import argparse
import re
from collections import Counter
from html import unescape

from database.connection import get_connection


# ============================================================
# Configuration
# ============================================================

MAX_SUMMARY_LENGTH = 450
MAX_WHY_IT_MATTERS_LENGTH = 500


# ============================================================
# Database
# ============================================================

def get_active_stories(connection):
    query = """
        SELECT
            id,
            title,
            summary,
            why_it_matters,
            category,
            importance_score,
            first_seen_at,
            last_updated_at
        FROM stories
        WHERE status = 'active'
        ORDER BY id
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "title": row[1],
            "summary": row[2],
            "why_it_matters": row[3],
            "category": row[4],
            "importance_score": row[5],
            "first_seen_at": row[6],
            "last_updated_at": row[7],
        }
        for row in rows
    ]


def get_story_articles(connection, story_id):
    query = """
        SELECT
            a.id,
            a.title,
            a.description,
            a.published_at,
            sa.similarity_score
        FROM story_articles sa
        JOIN articles a
            ON a.id = sa.article_id
        WHERE sa.story_id = %s
        ORDER BY
            sa.similarity_score DESC NULLS LAST,
            a.published_at ASC NULLS LAST,
            a.id
    """

    with connection.cursor() as cursor:
        cursor.execute(query, (story_id,))
        rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "published_at": row[3],
            "similarity_score": row[4],
        }
        for row in rows
    ]


# ============================================================
# Text cleaning
# ============================================================

def clean_html(text):
    """
    Convert HTML into plain text.
    """

    if not text:
        return ""

    text = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    text = text.replace(
        "&nbsp;",
        " ",
    )

    text = text.replace(
        "&amp;",
        "&",
    )

    text = text.replace(
        "&quot;",
        '"',
    )

    text = text.replace(
        "&#39;",
        "'",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def clean_text(text):
    """
    Normalize article text.
    """

    return clean_html(text)


# ============================================================
# Guardian boilerplate
# ============================================================

BOILERPLATE_PATTERNS = [
    r"\bGet our breaking news email\b.*",
    r"\bGet our .*? email\b.*",
    r"\bfree app\b.*",
    r"\bdaily news podcast\b.*",
    r"\bThis was originally published in .*",
    r"\bTell us: .*",
    r"\bVisual guide: .*",
    r"\bRead more: .*",
    r"\bFollow live: .*",
    r"\bRelated: .*",
    r"\bMore on this story\b.*",
    r"\bSign up for .*? newsletter\b.*",
    r"\bSubscribe to .*? newsletter\b.*",
]


def remove_boilerplate(text):
    """
    Remove common publisher/navigation content that can appear
    inside article descriptions.
    """

    if not text:
        return ""

    cleaned = text

    for pattern in BOILERPLATE_PATTERNS:
        cleaned = re.sub(
            pattern,
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    )

    return cleaned.strip()


# ============================================================
# Sentence extraction
# ============================================================

def split_sentences(text):
    """
    Lightweight sentence splitter.

    We intentionally avoid a dependency on an NLP pipeline here.
    """

    text = clean_text(text)

    if not text:
        return []

    parts = re.split(
        r"(?<=[.!?])\s+(?=[A-Z0-9])",
        text,
    )

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


def is_probably_boilerplate(sentence):
    """
    Detect individual sentences that should not be used as
    story metadata.
    """

    normalized = sentence.lower()

    patterns = [
        "get our breaking news email",
        "get our email",
        "free app",
        "daily news podcast",
        "this was originally published",
        "visual guide:",
        "tell us:",
        "read more:",
        "follow live:",
        "related:",
        "sign up for",
        "subscribe to",
    ]

    return any(
        pattern in normalized
        for pattern in patterns
    )


def extract_content_sentences(text):
    """
    Return useful editorial sentences while removing obvious
    navigation/promotional material.
    """

    text = remove_boilerplate(
        clean_text(text)
    )

    if not text:
        return []

    sentences = split_sentences(text)

    return [
        sentence
        for sentence in sentences
        if not is_probably_boilerplate(sentence)
    ]


def extract_description_blocks(html):
    """
    Extract meaningful textual blocks from an article description.

    Guardian descriptions commonly contain:
      <p>standfirst</p>
      <ul>related links...</ul>

    We want the actual editorial paragraph(s), not navigation
    or related-link content.
    """

    if not html:
        return []

    html = unescape(html)

    # Remove scripts/styles completely.
    html = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    html = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Extract paragraph contents before stripping tags.
    paragraphs = re.findall(
        r"<p\b[^>]*>(.*?)</p>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    blocks = []

    for paragraph in paragraphs:
        text = re.sub(
            r"<[^>]+>",
            " ",
            paragraph,
        )

        text = unescape(text)

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        if not text:
            continue

        if is_probably_boilerplate(text):
            continue

        blocks.append(text)

    return blocks

# ============================================================
# Summary
# ============================================================

def generate_summary(story, articles):
    """
    Generate a concise summary from the representative article.

    Prefer the article's first meaningful editorial paragraph,
    which is normally the standfirst. Do not concatenate
    navigation, related links, or newsletter content.
    """

    if not articles:
        return None

    representative = articles[0]

    description = representative.get("description") or ""

    blocks = extract_description_blocks(
        description
    )

    if blocks:
        summary = blocks[0].strip()

        # Ensure normal sentence punctuation where the source
        # standfirst omitted it.
        if summary and summary[-1] not in ".!?":
            summary += "."

        return summary[:MAX_SUMMARY_LENGTH]

    # Fallback when the description contains no <p> blocks.
    title = clean_text(
        representative.get("title")
        or story.get("title")
        or ""
    )

    return title[:MAX_SUMMARY_LENGTH] or None

# ============================================================
# Keyword helpers
# ============================================================

def story_text(story, articles):
    """
    Build a text representation of the story from titles and
    meaningful editorial description blocks.
    """

    parts = [
        story.get("title") or "",
    ]

    for article in articles:

        parts.append(
            article.get("title") or ""
        )

        description = article.get("description") or ""

        blocks = extract_description_blocks(
            description
        )

        parts.extend(blocks)

    return " ".join(parts).lower()

# ============================================================
# Category detection
# ============================================================

CATEGORY_KEYWORDS = {
    "Politics": {
        "government",
        "president",
        "prime minister",
        "minister",
        "election",
        "political",
        "politics",
        "parliament",
        "senator",
        "democrat",
        "republican",
        "trump",
        "sanctions",
        "immigration",
        "refugee",
        "policy",
        "coalition",
        "tariff",
        "tariffs",
    },

    "World": {
        "iran",
        "nepal",
        "tibet",
        "israel",
        "gaza",
        "russia",
        "ukraine",
        "china",
        "india",
        "pakistan",
        "africa",
        "europe",
        "thailand",
        "haiti",
        "bosnia",
        "egypt",
        "canada",
        "foreign",
        "international",
        "cairo",
    },

    "Environment": {
        "climate",
        "climate crisis",
        "flood",
        "floods",
        "storm",
        "storms",
        "heatwave",
        "heatwaves",
        "glacier",
        "glaciers",
        "wildlife",
        "environment",
        "environmental",
        "disaster",
    },

    "Health": {
        "health",
        "hospital",
        "malaria",
        "mpox",
        "outbreak",
        "disease",
        "medical",
        "medicine",
        "patients",
        "virus",
        "healthcare",
    },

    "Crime": {
        "police",
        "arrest",
        "arrested",
        "crime",
        "criminal",
        "murder",
        "killed",
        "kidnapped",
        "assault",
        "heist",
        "stolen",
        "smuggling",
        "guilty",
        "offender",
        "offenders",
    },

    "Culture": {
        "artist",
        "musician",
        "actor",
        "actress",
        "film",
        "music",
        "culture",
        "museum",
        "art",
        "charity",
        "food",
    },
}


def detect_category(story, articles):
    """
    Determine a broad category from the complete story text.

    Category selection is deterministic and based on keyword
    evidence across the complete cluster.
    """

    text = story_text(
        story,
        articles,
    )

    scores = Counter()

    for category, keywords in CATEGORY_KEYWORDS.items():

        for keyword in keywords:

            if keyword in text:
                scores[category] += 1

    if not scores:
        return "General"

    # Prefer the category with the strongest evidence.
    return scores.most_common(1)[0][0]


# ============================================================
# Why it matters
# ============================================================

WHY_IT_MATTERS_RULES = [
    (
        {
            "flood",
            "floods",
            "flash flood",
            "flash floods",
            "disaster",
            "missing",
            "killed",
            "death toll",
        },
        (
            "The event has caused significant loss of life and "
            "left people missing, making the ongoing rescue, "
            "recovery and humanitarian response important."
        ),
    ),

    (
        {
            "sanctions",
            "iran",
            "economic ties",
            "retaliate",
        },
        (
            "The developments could affect Iran's international "
            "economic relationships and increase pressure on "
            "countries and entities that maintain ties with Tehran."
        ),
    ),

    (
        {
            "trump",
            "canada",
            "trade war",
            "tariff",
            "tariffs",
        },
        (
            "The development is part of wider tensions between "
            "the United States and Canada, with potential political "
            "and economic consequences for both countries."
        ),
    ),

    (
        {
            "immigration",
            "refugee",
            "asylum",
            "migration",
        },
        (
            "The issue affects immigration policy and the treatment "
            "of migrants or refugees, making it relevant to wider "
            "political and social debate."
        ),
    ),

    (
        {
            "police",
            "arrest",
            "arrested",
            "crime",
            "criminal",
            "assault",
            "killed",
            "kidnapped",
            "heist",
            "smuggling",
        },
        (
            "The development concerns public safety and the response "
            "of law-enforcement authorities, with consequences for "
            "those directly affected."
        ),
    ),

    (
        {
            "hospital",
            "malaria",
            "mpox",
            "outbreak",
            "disease",
            "virus",
        },
        (
            "The development has public-health implications and may "
            "require continued monitoring as authorities assess the "
            "risk and response."
        ),
    ),

    (
        {
            "climate",
            "climate crisis",
            "glacier",
            "glaciers",
            "heatwave",
            "heatwaves",
            "storm",
            "storms",
        },
        (
            "The development highlights environmental risks and "
            "potential consequences for communities, infrastructure "
            "or ecosystems."
        ),
    ),

    (
        {
            "artist",
            "musician",
            "actor",
            "actress",
            "museum",
            "art",
            "culture",
        },
        (
            "The development is significant in the cultural sphere "
            "and provides an update on a notable figure, institution "
            "or cultural event."
        ),
    ),
]


def generate_why_it_matters(story, articles):
    """
    Generate a topic-oriented explanation using deterministic
    keyword evidence.

    The text deliberately avoids claiming facts that cannot be
    established from the article cluster.
    """

    text = story_text(
        story,
        articles,
    )

    best_match = None
    best_score = 0

    for keywords, explanation in WHY_IT_MATTERS_RULES:

        score = 0

        for keyword in keywords:

            if keyword in text:
                score += 1

        if score > best_score:
            best_score = score
            best_match = explanation

    if best_match:
        return best_match[:MAX_WHY_IT_MATTERS_LENGTH]

    # Conservative fallback.
    title = clean_text(
        story.get("title") or ""
    )

    if title:
        return (
            "The story tracks a significant reported development "
            "and may become more important as further information "
            "or official responses emerge."
        )

    return None


# ============================================================
# Metadata generation
# ============================================================

def generate_story_metadata(story, articles):
    return {
        "summary": generate_summary(
            story,
            articles,
        ),

        "why_it_matters": generate_why_it_matters(
            story,
            articles,
        ),

        "category": detect_category(
            story,
            articles,
        ),
    }


# ============================================================
# Output
# ============================================================

def print_metadata(story, articles, metadata):

    print()
    print("-" * 70)

    print(
        f"STORY {story['id']}"
    )

    print(
        f"Title:              {story['title']}"
    )

    print(
        f"Articles:           {len(articles)}"
    )

    print(
        f"Importance score:   "
        f"{float(story['importance_score'] or 0):.3f}"
    )

    print()

    print(
        "GENERATED METADATA"
    )

    print(
        f"  Summary:          {metadata['summary']}"
    )

    print(
        f"  Why it matters:   {metadata['why_it_matters']}"
    )

    print(
        f"  Category:         {metadata['category']}"
    )

    print()

    if articles:

        representative = articles[0]

        print(
            "REPRESENTATIVE ARTICLE"
        )

        print(
            f"  Article ID:       {representative['id']}"
        )

        print(
            f"  Similarity:       "
            f"{float(representative['similarity_score'] or 0):.4f}"
        )

        print(
            f"  Title:            "
            f"{representative['title']}"
        )


# ============================================================
# Persistence
# ============================================================

def update_story_metadata(
    connection,
    story_id,
    metadata,
):
    query = """
        UPDATE stories
        SET
            summary = %s,
            why_it_matters = %s,
            category = %s,
            last_updated_at = NOW()
        WHERE id = %s
    """

    with connection.cursor() as cursor:
        cursor.execute(
            query,
            (
                metadata["summary"],
                metadata["why_it_matters"],
                metadata["category"],
                story_id,
            ),
        )


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Generate metadata for NewsLens stories."
        )
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Show generated metadata without "
            "changing the database."
        ),
    )

    args = parser.parse_args()

    print(
        "=" * 70
    )

    print(
        "NewsLens — GENERATE STORY METADATA"
    )

    print(
        "=" * 70
    )

    print(
        f"\nMode: "
        f"{'DRY RUN' if args.dry_run else 'UPDATE DATABASE'}"
    )

    with get_connection() as connection:

        print(
            "\nLoading active stories..."
        )

        stories = get_active_stories(
            connection
        )

        print(
            f"Found {len(stories)} active stories."
        )

        if not stories:
            print(
                "\nNo active stories found."
            )
            return

        generated = 0
        skipped = 0
        failed = 0

        for story in stories:

            print()
            print(
                f"Processing story {story['id']}..."
            )

            articles = get_story_articles(
                connection,
                story["id"],
            )

            if not articles:

                print(
                    f"SKIPPED: Story {story['id']} "
                    f"has no articles."
                )

                skipped += 1
                continue

            try:

                metadata = generate_story_metadata(
                    story,
                    articles,
                )

                print_metadata(
                    story,
                    articles,
                    metadata,
                )

                if not args.dry_run:

                    update_story_metadata(
                        connection,
                        story["id"],
                        metadata,
                    )

                    print(
                        f"\nUPDATED story {story['id']}"
                    )

                generated += 1

            except Exception as error:

                print(
                    f"ERROR processing story "
                    f"{story['id']}: {error}"
                )

                failed += 1

        print()
        print(
            "=" * 70
        )

        print(
            "SUMMARY"
        )

        print(
            f"Stories found:       {len(stories)}"
        )

        print(
            f"Metadata generated:  {generated}"
        )

        print(
            f"Skipped:             {skipped}"
        )

        print(
            f"Failed:              {failed}"
        )

        print(
            "=" * 70
        )

        if args.dry_run:

            print(
                "\nDry run complete. "
                "No database changes were made."
            )

        else:

            print(
                "\nStory metadata update complete."
            )


if __name__ == "__main__":
    main()