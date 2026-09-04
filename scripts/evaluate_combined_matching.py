from itertools import combinations

import numpy as np

from database.connection import get_connection
from nlp.entities import extract_entities
from nlp.story_matching import calculate_story_match


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

SEMANTIC_ONLY_THRESHOLD = 0.70
COMBINED_THRESHOLD = 0.70


# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

def get_articles():
    """
    Load articles together with their story assignments.

    The article -> story relationship is stored in the
    story_articles table.

    An article may belong to one story in the current
    NewsLens pipeline, but the database relationship itself
    allows the mapping explicitly.
    """

    query = """
        SELECT
            a.id,
            a.title,
            a.description,
            a.embedding,
            sa.story_id
        FROM articles AS a
        INNER JOIN story_articles AS sa
            ON a.id = sa.article_id
        WHERE a.embedding IS NOT NULL
        ORDER BY a.id
    """

    with get_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(query)

            rows = cursor.fetchall()

    articles = []

    for row in rows:

        articles.append({
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "embedding": row[3],
            "story_id": row[4],
        })

    return articles


# ---------------------------------------------------------
# Text
# ---------------------------------------------------------

def build_article_text(article):
    """
    Build the text used for entity extraction.

    Current articles table contains title and description,
    but does not contain a content column.
    """

    title = article.get("title") or ""
    description = article.get("description") or ""

    return f"{title}\n{description}".strip()


# ---------------------------------------------------------
# Embeddings
# ---------------------------------------------------------

def parse_embedding(value):
    """
    Convert a PostgreSQL pgvector value into a NumPy array.

    Example PostgreSQL value:

        '[0.123,0.456,-0.789]'
    """

    if value is None:
        return None

    if isinstance(value, str):

        value = value.strip()

        if value.startswith("[") and value.endswith("]"):
            value = value[1:-1]

        if not value:
            return None

        return np.array(
            [
                float(x)
                for x in value.split(",")
            ],
            dtype=float,
        )

    return np.array(
        value,
        dtype=float,
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


# ---------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------

def extract_article_entities(articles):

    print("\nExtracting entities...")

    for index, article in enumerate(
        articles,
        start=1,
    ):

        text = build_article_text(article)

        article["entities"] = extract_entities(text)

        print(
            f"Processed "
            f"{index}/{len(articles)}: "
            f"article {article['id']}"
        )

    print("Entity extraction complete.")


# ---------------------------------------------------------
# Pair evaluation
# ---------------------------------------------------------

def evaluate_pairs(articles):

    same_story_pairs = []
    different_story_pairs = []

    for article_a, article_b in combinations(
        articles,
        2,
    ):

        vector_a = parse_embedding(
            article_a["embedding"]
        )

        vector_b = parse_embedding(
            article_b["embedding"]
        )

        semantic_score = cosine_similarity(
            vector_a,
            vector_b,
        )

        match_result = calculate_story_match(
            semantic_score,
            article_a["entities"],
            article_b["entities"],
        )

        result = {
            "article_a_id": article_a["id"],
            "article_b_id": article_b["id"],

            "article_a_title": article_a["title"],
            "article_b_title": article_b["title"],

            "story_a": article_a["story_id"],
            "story_b": article_b["story_id"],

            **match_result,
        }

        if (
            article_a["story_id"]
            == article_b["story_id"]
        ):
            same_story_pairs.append(result)

        else:
            different_story_pairs.append(result)

    return (
        same_story_pairs,
        different_story_pairs,
    )


# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------

def average(values):

    if not values:
        return 0.0

    return sum(values) / len(values)


def print_statistics(
    same_story_pairs,
    different_story_pairs,
):

    print("\n")
    print("=" * 70)
    print("MATCHING STATISTICS")
    print("=" * 70)

    print(
        f"\nSame-story pairs: "
        f"{len(same_story_pairs)}"
    )

    print(
        f"Different-story pairs: "
        f"{len(different_story_pairs)}"
    )

    # -----------------------------------------------------
    # Semantic similarity
    # -----------------------------------------------------

    same_semantic = [
        pair["semantic_similarity"]
        for pair in same_story_pairs
    ]

    different_semantic = [
        pair["semantic_similarity"]
        for pair in different_story_pairs
    ]

    print("\n--- SEMANTIC SIMILARITY ---")

    print(
        f"Same-story average: "
        f"{average(same_semantic):.4f}"
    )

    print(
        f"Different-story average: "
        f"{average(different_semantic):.4f}"
    )

    # -----------------------------------------------------
    # Entity similarity
    # -----------------------------------------------------

    same_entity = [
        pair["entity_similarity"]
        for pair in same_story_pairs
    ]

    different_entity = [
        pair["entity_similarity"]
        for pair in different_story_pairs
    ]

    print("\n--- ENTITY SIMILARITY ---")

    print(
        f"Same-story average: "
        f"{average(same_entity):.4f}"
    )

    print(
        f"Different-story average: "
        f"{average(different_entity):.4f}"
    )

    # -----------------------------------------------------
    # Combined score
    # -----------------------------------------------------

    same_combined = [
        pair["combined_score"]
        for pair in same_story_pairs
    ]

    different_combined = [
        pair["combined_score"]
        for pair in different_story_pairs
    ]

    print("\n--- COMBINED SCORE ---")

    print(
        f"Same-story average: "
        f"{average(same_combined):.4f}"
    )

    print(
        f"Different-story average: "
        f"{average(different_combined):.4f}"
    )

    # -----------------------------------------------------
    # Threshold analysis
    # -----------------------------------------------------

    print("\n--- THRESHOLD ANALYSIS ---")

    evaluate_threshold(
        same_story_pairs,
        different_story_pairs,
        SEMANTIC_ONLY_THRESHOLD,
        "Semantic only",
        "semantic_similarity",
    )

    evaluate_threshold(
        same_story_pairs,
        different_story_pairs,
        COMBINED_THRESHOLD,
        "Semantic + entities",
        "combined_score",
    )


def evaluate_threshold(
    same_story_pairs,
    different_story_pairs,
    threshold,
    name,
    field,
):

    true_positives = sum(
        pair[field] >= threshold
        for pair in same_story_pairs
    )

    false_negatives = (
        len(same_story_pairs)
        - true_positives
    )

    false_positives = sum(
        pair[field] >= threshold
        for pair in different_story_pairs
    )

    true_negatives = (
        len(different_story_pairs)
        - false_positives
    )

    total = (
        true_positives
        + false_negatives
        + false_positives
        + true_negatives
    )

    accuracy = (
        (true_positives + true_negatives)
        / total
        if total
        else 0.0
    )

    precision = (
        true_positives
        / (true_positives + false_positives)
        if (true_positives + false_positives)
        else 0.0
    )

    recall = (
        true_positives
        / (true_positives + false_negatives)
        if (true_positives + false_negatives)
        else 0.0
    )

    print(f"\n{name}")

    print(
        f"Threshold: "
        f"{threshold:.2f}"
    )

    print(
        f"True positives: "
        f"{true_positives}"
    )

    print(
        f"False positives: "
        f"{false_positives}"
    )

    print(
        f"False negatives: "
        f"{false_negatives}"
    )

    print(
        f"True negatives: "
        f"{true_negatives}"
    )

    print(
        f"Accuracy: "
        f"{accuracy:.4f}"
    )

    print(
        f"Precision: "
        f"{precision:.4f}"
    )

    print(
        f"Recall: "
        f"{recall:.4f}"
    )


# ---------------------------------------------------------
# Interesting pairs
# ---------------------------------------------------------

def print_interesting_pairs(
    same_story_pairs,
    different_story_pairs,
):

    print("\n")
    print("=" * 70)
    print("INTERESTING SAME-STORY PAIRS")
    print("=" * 70)

    # Lowest combined scores among articles that are
    # already known to belong to the same story.
    lowest = sorted(
        same_story_pairs,
        key=lambda pair: pair["combined_score"],
    )[:10]

    for pair in lowest:

        print("\n----------------------------------------")

        print(
            f"Article {pair['article_a_id']}: "
            f"{pair['article_a_title']}"
        )

        print(
            f"Article {pair['article_b_id']}: "
            f"{pair['article_b_title']}"
        )

        print(
            f"Story ID: "
            f"{pair['story_a']}"
        )

        print(
            f"Semantic: "
            f"{pair['semantic_similarity']:.4f}"
        )

        print(
            f"Entity: "
            f"{pair['entity_similarity']:.4f}"
        )

        print(
            f"Combined: "
            f"{pair['combined_score']:.4f}"
        )

        print(
            f"Shared entities: "
            f"{pair['shared_entities']}"
        )

    print("\n")
    print("=" * 70)
    print("INTERESTING DIFFERENT-STORY PAIRS")
    print("=" * 70)

    # Highest combined scores among articles that belong
    # to different stories.
    highest = sorted(
        different_story_pairs,
        key=lambda pair: pair["combined_score"],
        reverse=True,
    )[:10]

    for pair in highest:

        print("\n----------------------------------------")

        print(
            f"Article {pair['article_a_id']}: "
            f"{pair['article_a_title']}"
        )

        print(
            f"Article {pair['article_b_id']}: "
            f"{pair['article_b_title']}"
        )

        print(
            f"Stories: "
            f"{pair['story_a']} "
            f"vs "
            f"{pair['story_b']}"
        )

        print(
            f"Semantic: "
            f"{pair['semantic_similarity']:.4f}"
        )

        print(
            f"Entity: "
            f"{pair['entity_similarity']:.4f}"
        )

        print(
            f"Combined: "
            f"{pair['combined_score']:.4f}"
        )

        print(
            f"Shared entities: "
            f"{pair['shared_entities']}"
        )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    print("Loading articles...")

    articles = get_articles()

    print(
        f"Loaded {len(articles)} article-story mappings."
    )

    if len(articles) < 2:

        print(
            "Not enough article-story mappings "
            "to evaluate."
        )

        return

    print(
        "\nExtracting entities from articles..."
    )

    extract_article_entities(
        articles
    )

    print(
        "\nEvaluating article pairs..."
    )

    (
        same_story_pairs,
        different_story_pairs,
    ) = evaluate_pairs(
        articles
    )

    print_statistics(
        same_story_pairs,
        different_story_pairs,
    )

    print_interesting_pairs(
        same_story_pairs,
        different_story_pairs,
    )

    print("\n")
    print("=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()