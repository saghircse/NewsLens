import numpy as np

from database.connection import get_connection
from nlp.entities import extract_normalized_entities


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

HIGH_THRESHOLD = 0.75
POSSIBLE_THRESHOLD = 0.55

SEMANTIC_WEIGHT = 0.65
ENTITY_WEIGHT = 0.25
TIME_WEIGHT = 0.10


# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

def get_articles():

    query = """
        SELECT
            id,
            title,
            description,
            published_at,
            embedding
        FROM articles
        WHERE embedding IS NOT NULL
        ORDER BY id;
    """

    with get_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(query)

            return cursor.fetchall()


def get_stories():

    query = """
        SELECT
            id,
            title,
            summary,
            why_it_matters,
            first_seen_at,
            last_updated_at,
            embedding
        FROM stories
        WHERE embedding IS NOT NULL
        ORDER BY id;
    """

    with get_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(query)

            return cursor.fetchall()


# ---------------------------------------------------------
# Vector utilities
# ---------------------------------------------------------

def parse_embedding(value):

    if value is None:
        return None

    if isinstance(value, str):

        value = value.strip()

        if value.startswith("[") and value.endswith("]"):

            value = value[1:-1]

        return np.array(
            [
                float(x)
                for x in value.split(",")
                if x.strip()
            ],
            dtype=float,
        )

    return np.array(value, dtype=float)


def cosine_similarity(vector_a, vector_b):

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
# Entity utilities
# ---------------------------------------------------------

def article_text(article):

    (
        article_id,
        title,
        description,
        published_at,
        embedding,
    ) = article

    parts = []

    if title:
        parts.append(title)

    if description:
        parts.append(description)

    return " ".join(parts)


def story_text(story):

    (
        story_id,
        title,
        summary,
        why_it_matters,
        first_seen_at,
        last_updated_at,
        embedding,
    ) = story

    parts = []

    if title:
        parts.append(title)

    if summary:
        parts.append(summary)

    if why_it_matters:
        parts.append(why_it_matters)

    return " ".join(parts)


def entity_overlap(article_entities, story_entities):

    if not article_entities or not story_entities:
        return 0.0

    intersection = (
        article_entities
        & story_entities
    )

    union = (
        article_entities
        | story_entities
    )

    if not union:
        return 0.0

    return len(intersection) / len(union)


# ---------------------------------------------------------
# Time similarity
# ---------------------------------------------------------

def time_similarity(article_time, story):

    if article_time is None:
        return 0.0

    (
        story_id,
        title,
        summary,
        why_it_matters,
        first_seen_at,
        last_updated_at,
        embedding,
    ) = story

    if first_seen_at is None:
        return 0.0

    difference = abs(
        (
            article_time - first_seen_at
        ).total_seconds()
    )

    hours = difference / 3600.0

    # Same hour
    if hours <= 1:
        return 1.0

    # Gradually decrease similarity.
    #
    # After 24 hours this reaches 0.
    score = max(
        0.0,
        1.0 - (hours / 24.0)
    )

    return score


# ---------------------------------------------------------
# Match score
# ---------------------------------------------------------

def calculate_match_score(
    semantic,
    entity,
    time,
):

    return (
        SEMANTIC_WEIGHT * semantic
        + ENTITY_WEIGHT * entity
        + TIME_WEIGHT * time
    )


def classify_score(score):

    if score >= HIGH_THRESHOLD:
        return "HIGH"

    if score >= POSSIBLE_THRESHOLD:
        return "POSSIBLE"

    return "LOW"


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    print("Loading articles...")

    articles = get_articles()

    print(
        f"Loaded {len(articles)} articles."
    )

    print()

    print("Loading stories...")

    stories = get_stories()

    print(
        f"Loaded {len(stories)} stories."
    )

    print()

    if not stories:

        print("No stories found.")

        return

    print(
        "Extracting article entities..."
    )

    article_entities = {}

    for article in articles:

        article_id = article[0]

        text = article_text(article)

        article_entities[article_id] = (
            extract_normalized_entities(text)
        )

    print("Entity extraction complete.")

    print()

    print("=" * 80)
    print("ENTITY-AWARE STORY MATCHING")
    print("=" * 80)

    for article in articles:

        (
            article_id,
            title,
            description,
            published_at,
            embedding_value,
        ) = article

        article_vector = parse_embedding(
            embedding_value
        )

        print()
        print("=" * 80)
        print(
            f"ARTICLE {article_id}"
        )
        print("-" * 80)
        print(title)

        print()

        entities = article_entities[
            article_id
        ]

        print(
            f"Entities ({len(entities)}):"
        )

        if entities:

            print(
                ", ".join(
                    sorted(entities)
                )
            )

        else:

            print("None")

        print()

        results = []

        for story in stories:

            (
                story_id,
                story_title,
                summary,
                why_it_matters,
                first_seen_at,
                last_updated_at,
                story_embedding_value,
            ) = story

            story_vector = parse_embedding(
                story_embedding_value
            )

            semantic = cosine_similarity(
                article_vector,
                story_vector,
            )

            story_entities = (
                extract_normalized_entities(
                    story_text(story)
                )
            )

            entity_score = entity_overlap(
                entities,
                story_entities,
            )

            time_score = time_similarity(
                published_at,
                story,
            )

            final_score = calculate_match_score(
                semantic,
                entity_score,
                time_score,
            )

            classification = classify_score(
                final_score
            )

            results.append(
                (
                    final_score,
                    story_id,
                    story_title,
                    semantic,
                    entity_score,
                    time_score,
                    classification,
                )
            )

        results.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        for (
            final_score,
            story_id,
            story_title,
            semantic,
            entity_score,
            time_score,
            classification,
        ) in results:

            print()
            print(
                f"Story {story_id}"
            )

            print(
                f"  {story_title}"
            )

            print(
                f"  Semantic: {semantic:.3f}"
            )

            print(
                f"  Entity:   {entity_score:.3f}"
            )

            print(
                f"  Time:     {time_score:.3f}"
            )

            print(
                f"  Score:    {final_score:.3f} "
                f"{classification}"
            )

    print()
    print("=" * 80)
    print("Evaluation complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()