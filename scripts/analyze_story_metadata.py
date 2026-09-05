from collections import Counter
from datetime import datetime

from database.connection import get_connection


def get_stories(conn):
    query = """
        SELECT
            id,
            title,
            summary,
            why_it_matters,
            category,
            importance_score,
            first_seen_at,
            last_updated_at,
            status
        FROM stories
        WHERE status = 'active'
        ORDER BY id;
    """

    with conn.cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall()


def get_story_articles(conn, story_id):
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
            a.published_at DESC NULLS LAST,
            a.id;
    """

    with conn.cursor() as cursor:
        cursor.execute(query, (story_id,))
        return cursor.fetchall()


def get_article_entities(conn, article_ids):
    """
    This function intentionally does not assume an entity table/schema.

    Stage 8.3 only uses fields that are already confirmed to exist
    in the articles table.
    """
    return {article_id: [] for article_id in article_ids}


def calculate_average_similarity(articles):
    scores = [
        row[4]
        for row in articles
        if row[4] is not None
    ]

    if not scores:
        return None

    return sum(scores) / len(scores)


def calculate_similarity_range(articles):
    scores = [
        row[4]
        for row in articles
        if row[4] is not None
    ]

    if not scores:
        return None, None

    return min(scores), max(scores)


def get_temporal_range(articles):
    dates = [
        row[3]
        for row in articles
        if row[3] is not None
    ]

    if not dates:
        return None, None

    return min(dates), max(dates)


def get_title_similarity_signal(story_title, articles):
    """
    Simple lexical signal.

    This is deliberately diagnostic rather than a final scoring mechanism.
    It checks how much of the story title's meaningful words appear in
    article titles.
    """

    if not story_title:
        return 0.0

    stop_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "after",
        "amid",
        "as",
        "is",
        "are",
        "from",
        "by",
        "at",
        "over",
        "under",
    }

    story_words = {
        word.strip(".,:;!?()[]{}\"'“”‘’–—-").lower()
        for word in story_title.split()
    }

    story_words = {
        word
        for word in story_words
        if word and word not in stop_words and len(word) > 2
    }

    if not story_words:
        return 0.0

    article_text = " ".join(
        row[1] or ""
        for row in articles
    ).lower()

    matched = sum(
        1
        for word in story_words
        if word in article_text
    )

    return matched / len(story_words)


def classify_story_size(article_count):
    if article_count == 1:
        return "single-article"
    if article_count <= 3:
        return "small"
    if article_count <= 7:
        return "medium"

    return "large"


def print_story_analysis(
    story,
    articles,
):
    (
        story_id,
        story_title,
        summary,
        why_it_matters,
        category,
        importance_score,
        first_seen_at,
        last_updated_at,
        status,
    ) = story

    article_count = len(articles)

    average_similarity = calculate_average_similarity(
        articles
    )

    min_similarity, max_similarity = calculate_similarity_range(
        articles
    )

    earliest, latest = get_temporal_range(
        articles
    )

    title_signal = get_title_similarity_signal(
        story_title,
        articles,
    )

    print()
    print("=" * 70)
    print(f"STORY {story_id}")
    print("=" * 70)

    print(f"Title:              {story_title}")
    print(f"Article count:      {article_count}")
    print(f"Story size:         {classify_story_size(article_count)}")
    print(f"Importance score:   {importance_score}")
    print(f"Status:             {status}")

    print()
    print("CURRENT METADATA")
    print(f"  Summary:          {summary}")
    print(f"  Why it matters:   {why_it_matters}")
    print(f"  Category:         {category}")

    print()
    print("TIMELINE")
    print(f"  Earliest article: {earliest}")
    print(f"  Latest article:   {latest}")

    print()
    print("SIMILARITY")
    print(
        f"  Average:          "
        f"{average_similarity:.4f}"
        if average_similarity is not None
        else "  Average:          N/A"
    )

    print(
        f"  Minimum:          "
        f"{min_similarity:.4f}"
        if min_similarity is not None
        else "  Minimum:          N/A"
    )

    print(
        f"  Maximum:          "
        f"{max_similarity:.4f}"
        if max_similarity is not None
        else "  Maximum:          N/A"
    )

    print(
        f"  Title coverage:   {title_signal:.4f}"
    )

    print()
    print("ARTICLES")

    for rank, article in enumerate(
        articles,
        start=1,
    ):
        (
            article_id,
            article_title,
            description,
            published_at,
            similarity_score,
        ) = article

        score_text = (
            f"{similarity_score:.4f}"
            if similarity_score is not None
            else "N/A"
        )

        print()
        print(
            f"  #{rank} "
            f"Article {article_id} "
            f"(similarity={score_text})"
        )

        print(
            f"      Published: {published_at}"
        )

        print(
            f"      Title:     {article_title}"
        )

        if description:
            description_text = " ".join(
                description.split()
            )

            if len(description_text) > 300:
                description_text = (
                    description_text[:297] + "..."
                )

            print(
                f"      Description: {description_text}"
            )

    if articles:
        representative = articles[0]

        print()
        print("REPRESENTATIVE ARTICLE")
        print(
            f"  Article ID:       {representative[0]}"
        )
        print(
            f"  Similarity:       "
            f"{representative[4]:.4f}"
            if representative[4] is not None
            else "  Similarity:       N/A"
        )
        print(
            f"  Title:            {representative[1]}"
        )

    print()


def main():

    print("=" * 70)
    print("NewsLens — STORY METADATA ANALYSIS")
    print("=" * 70)

    with get_connection() as conn:

        stories = get_stories(conn)

        print()
        print(f"Active stories: {len(stories)}")

        for story in stories:

            story_id = story[0]

            articles = get_story_articles(
                conn,
                story_id,
            )

            print_story_analysis(
                story,
                articles,
            )

    print("=" * 70)
    print("Analysis complete.")
    print("No database changes were made.")
    print("=" * 70)


if __name__ == "__main__":
    main()