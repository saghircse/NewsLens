import argparse
import ast
import numpy as np
from psycopg.rows import dict_row

from database.connection import get_connection
from nlp.entities import extract_normalized_entities


# ============================================================
# Configuration
# ============================================================

SEMANTIC_WEIGHT = 0.75
ENTITY_WEIGHT = 0.25

# Conservative threshold for automatically assigning an article
# to an existing story.
MATCH_THRESHOLD = 0.70

# Minimum threshold at which we display a possible match during
# dry-run diagnostics.
POSSIBLE_THRESHOLD = 0.55


# ============================================================
# Embedding helpers
# ============================================================

def parse_embedding(value):
    """
    Convert an embedding stored in PostgreSQL into a Python list.

    pgvector values may be returned by psycopg as strings such as:

        '[0.12,0.34,-0.56,...]'

    We therefore explicitly parse the string instead of passing
    it directly to numpy.array().
    """

    if value is None:
        return None

    if isinstance(value, np.ndarray):
        return value.astype(float)

    if isinstance(value, (list, tuple)):
        return np.array(value, dtype=float)

    if isinstance(value, str):
        value = value.strip()

        try:
            parsed = ast.literal_eval(value)
            return np.array(parsed, dtype=float)
        except (ValueError, SyntaxError):
            # Fallback for pgvector-style strings without spaces.
            value = value.strip("[]")

            if not value:
                return None

            return np.array(
                [float(x) for x in value.split(",")],
                dtype=float,
            )

    raise TypeError(
        f"Unsupported embedding type: {type(value)}"
    )


def cosine_similarity(vector_a, vector_b):
    """
    Calculate cosine similarity between two vectors.
    """

    if vector_a is None or vector_b is None:
        return 0.0

    norm_a = np.linalg.norm(vector_a)
    norm_b = np.linalg.norm(vector_b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(
        np.dot(vector_a, vector_b)
        / (norm_a * norm_b)
    )


# ============================================================
# Entity similarity
# ============================================================

def entity_similarity(article_entities, story_entities):
    """
    Calculate Jaccard similarity between article and story entities.

    Jaccard similarity:

        intersection / union
    """

    if not article_entities or not story_entities:
        return 0.0

    intersection = article_entities.intersection(story_entities)
    union = article_entities.union(story_entities)

    if not union:
        return 0.0

    return len(intersection) / len(union)


# ============================================================
# Combined score
# ============================================================

def calculate_combined_score(
    semantic_score,
    entity_score,
):
    """
    Combined NewsLens story matching score.

    Stage 7.9 formula:

        75% semantic similarity
        25% entity similarity
    """

    return (
        SEMANTIC_WEIGHT * semantic_score
        + ENTITY_WEIGHT * entity_score
    )


# ============================================================
# Database loading
# ============================================================

def get_articles():
    """
    Load articles that have embeddings.
    """

    query = """
        SELECT
            id,
            title,
            description,
            embedding
        FROM articles
        WHERE embedding IS NOT NULL
        ORDER BY id;
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query)
            return cursor.fetchall()


def get_stories():
    """
    Load stories that have embeddings.
    """

    query = """
        SELECT
            id,
            title,
            summary,
            why_it_matters,
            embedding
        FROM stories
        WHERE embedding IS NOT NULL
        ORDER BY id;
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query)
            return cursor.fetchall()


# ============================================================
# Text preparation
# ============================================================

def build_article_text(article):
    """
    Build text used for entity extraction.

    We intentionally use title + description.

    Article content is not currently part of the articles schema.
    """

    parts = []

    if article.get("title"):
        parts.append(article["title"])

    if article.get("description"):
        parts.append(article["description"])

    return " ".join(parts).strip()


def build_story_text(story):
    """
    Build text used for entity extraction.

    Story currently contains:

        title
        summary
        why_it_matters
    """

    parts = []

    if story.get("title"):
        parts.append(story["title"])

    if story.get("summary"):
        parts.append(story["summary"])

    if story.get("why_it_matters"):
        parts.append(story["why_it_matters"])

    return " ".join(parts).strip()


# ============================================================
# Matching
# ============================================================

def prepare_story_data(stories):
    """
    Pre-process stories so entity extraction is performed only once.
    """

    prepared = []

    for story in stories:

        embedding = parse_embedding(
            story["embedding"]
        )

        text = build_story_text(story)

        entities = extract_normalized_entities(text)

        prepared.append({
            "id": story["id"],
            "title": story["title"],
            "embedding": embedding,
            "entities": entities,
        })

    return prepared


def find_best_story(article, stories):
    """
    Compare one article against all stories and return the
    highest-scoring story.
    """

    article_embedding = parse_embedding(
        article["embedding"]
    )

    article_text = build_article_text(article)

    article_entities = extract_normalized_entities(
        article_text
    )

    candidates = []

    for story in stories:

        semantic_score = cosine_similarity(
            article_embedding,
            story["embedding"],
        )

        entity_score = entity_similarity(
            article_entities,
            story["entities"],
        )

        combined_score = calculate_combined_score(
            semantic_score,
            entity_score,
        )

        shared_entities = sorted(
            article_entities.intersection(
                story["entities"]
            )
        )

        candidates.append({
            "story_id": story["id"],
            "story_title": story["title"],
            "semantic_score": semantic_score,
            "entity_score": entity_score,
            "combined_score": combined_score,
            "shared_entities": shared_entities,
        })

    candidates.sort(
        key=lambda x: x["combined_score"],
        reverse=True,
    )

    if not candidates:
        return None, article_entities, []

    return candidates[0], article_entities, candidates


# ============================================================
# Database persistence
# ============================================================

def clear_story_articles():
    """
    Remove all existing story/article mappings.

    This is intended for development and controlled rebuilding.
    """

    query = """
        DELETE FROM story_articles;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)

        connection.commit()


def save_mapping(
    story_id,
    article_id,
    similarity_score,
):
    """
    Insert or update a story/article relationship.
    """

    query = """
        INSERT INTO story_articles (
            story_id,
            article_id,
            similarity_score
        )
        VALUES (%s, %s, %s)

        ON CONFLICT (story_id, article_id)
        DO UPDATE SET
            similarity_score = EXCLUDED.similarity_score;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                query,
                (
                    story_id,
                    article_id,
                    similarity_score,
                ),
            )

        connection.commit()


# ============================================================
# Output helpers
# ============================================================

def print_match(article, result):

    print()
    print("-" * 70)

    print(
        f"Article {article['id']}: "
        f"{article['title']}"
    )

    if result is None:
        print("No stories available.")
        return

    print(
        f"Best story: {result['story_id']}"
    )

    print(
        f"  {result['story_title']}"
    )

    print(
        f"  Semantic similarity: "
        f"{result['semantic_score']:.4f}"
    )

    print(
        f"  Entity similarity:   "
        f"{result['entity_score']:.4f}"
    )

    print(
        f"  Combined score:      "
        f"{result['combined_score']:.4f}"
    )

    if result["shared_entities"]:
        print(
            "  Shared entities:     "
            f"{result['shared_entities']}"
        )
    else:
        print(
            "  Shared entities:     none"
        )

    if result["combined_score"] >= MATCH_THRESHOLD:

        print(
            f"  Decision: MATCH "
            f"(>= {MATCH_THRESHOLD:.2f})"
        )

    elif result["combined_score"] >= POSSIBLE_THRESHOLD:

        print(
            f"  Decision: POSSIBLE "
            f"(>= {POSSIBLE_THRESHOLD:.2f})"
        )

    else:

        print(
            f"  Decision: NO MATCH "
            f"(< {POSSIBLE_THRESHOLD:.2f})"
        )


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Match NewsLens articles to existing stories."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calculate matches without modifying the database.",
    )

    parser.add_argument(
        "--rebuild",
        action="store_true",
        help=(
            "Delete all existing story_articles mappings "
            "before rebuilding them."
        ),
    )

    args = parser.parse_args()

    print()
    print("=" * 70)
    print("NEWSLENS STORY-ARTICLE MATCHING")
    print("=" * 70)

    # --------------------------------------------------------
    # Load articles
    # --------------------------------------------------------

    print()
    print("Loading articles...")

    articles = get_articles()

    print(
        f"Loaded {len(articles)} articles."
    )

    if not articles:
        print("No articles with embeddings found.")
        return

    # --------------------------------------------------------
    # Load stories
    # --------------------------------------------------------

    print()
    print("Loading stories...")

    stories = get_stories()

    print(
        f"Loaded {len(stories)} stories."
    )

    if not stories:
        print("No stories with embeddings found.")
        return

    # --------------------------------------------------------
    # Prepare stories
    # --------------------------------------------------------

    print()
    print("Preparing story entities...")

    prepared_stories = prepare_story_data(
        stories
    )

    print("Story entities prepared.")

    # --------------------------------------------------------
    # Rebuild option
    # --------------------------------------------------------

    if args.rebuild:

        if args.dry_run:

            print()
            print(
                "WARNING: --rebuild ignored because "
                "--dry-run was specified."
            )

        else:

            print()
            print(
                "Clearing existing story_articles mappings..."
            )

            clear_story_articles()

            print(
                "Existing mappings cleared."
            )

    # --------------------------------------------------------
    # Matching
    # --------------------------------------------------------

    print()
    print("Matching articles to stories...")

    print(
        f"Semantic weight: {SEMANTIC_WEIGHT:.2f}"
    )

    print(
        f"Entity weight:   {ENTITY_WEIGHT:.2f}"
    )

    print(
        f"Match threshold: {MATCH_THRESHOLD:.2f}"
    )

    matched_count = 0
    possible_count = 0
    unmatched_count = 0
    failed_count = 0

    persisted_count = 0

    for index, article in enumerate(articles, start=1):

        try:

            result, article_entities, candidates = (
                find_best_story(
                    article,
                    prepared_stories,
                )
            )

            print()
            print(
                f"[{index}/{len(articles)}]"
            )

            print_match(
                article,
                result,
            )

            if result is None:
                unmatched_count += 1
                continue

            score = result["combined_score"]

            if score >= MATCH_THRESHOLD:

                matched_count += 1

                if not args.dry_run:

                    save_mapping(
                        story_id=result["story_id"],
                        article_id=article["id"],
                        similarity_score=score,
                    )

                    persisted_count += 1

            elif score >= POSSIBLE_THRESHOLD:

                possible_count += 1

            else:

                unmatched_count += 1

        except Exception as exc:

            failed_count += 1

            print()
            print(
                f"ERROR processing article "
                f"{article['id']}: {exc}"
            )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(
        f"Articles processed:   {len(articles)}"
    )

    print(
        f"Matched:              {matched_count}"
    )

    print(
        f"Possible:              {possible_count}"
    )

    print(
        f"Unmatched:            {unmatched_count}"
    )

    print(
        f"Failed:               {failed_count}"
    )

    if args.dry_run:

        print()
        print(
            "DRY RUN: database was NOT modified."
        )

    else:

        print(
            f"Mappings persisted:   {persisted_count}"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()