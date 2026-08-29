import numpy as np

from database.connection import get_connection


def parse_embedding(embedding):
    """
    Convert a PostgreSQL/pgvector embedding into
    a NumPy array.
    """

    if embedding is None:
        return None

    if isinstance(embedding, str):

        embedding = embedding.strip()

        if embedding.startswith("[") and embedding.endswith("]"):
            embedding = embedding[1:-1]

        if not embedding:
            return None

        values = [
            float(value.strip())
            for value in embedding.split(",")
        ]

        return np.array(
            values,
            dtype=np.float32,
        )

    return np.array(
        embedding,
        dtype=np.float32,
    )


def get_articles():
    """
    Get articles that have embeddings.
    """

    query = """
        select
            id,
            title,
            description,
            published_at,
            embedding
        from articles
        where embedding is not null
        order by published_at desc nulls last;
    """

    with get_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(query)

            return cursor.fetchall()


def get_stories():
    """
    Get stories that have embeddings.

    Stories do not have a published_at column.
    We use first_seen_at as the story's time reference.
    """

    query = """
        select
            id,
            title,
            summary,
            first_seen_at,
            embedding
        from stories
        where embedding is not null
        order by first_seen_at desc nulls last;
    """

    with get_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(query)

            return cursor.fetchall()


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


def calculate_time_similarity(
    article_time,
    story_time,
    max_hours=48,
):
    """
    Calculate similarity based on publication time.

    1.0 = same time
    0.0 = 48+ hours apart
    """

    if article_time is None or story_time is None:
        return 0.0

    difference = abs(
        article_time - story_time
    )

    hours = (
        difference.total_seconds()
        / 3600
    )

    if hours >= max_hours:
        return 0.0

    return 1.0 - (
        hours / max_hours
    )


def calculate_match_score(
    semantic_similarity,
    time_similarity,
):
    """
    Initial story matching score.

    Entity similarity will be added later.
    """

    return (
        0.85 * semantic_similarity
        + 0.15 * time_similarity
    )


def get_label(score):

    if score >= 0.80:
        return "🟢 HIGH"

    if score >= 0.60:
        return "🟡 POSSIBLE"

    return "⚪ LOW"


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

    if not articles:
        print("No articles available.")
        return

    if not stories:
        print(
            "No stories with embeddings available."
        )
        return

    print()
    print("=" * 70)
    print("NEWSLENS STORY MATCHING EVALUATOR")
    print("=" * 70)

    for article in articles:

        article_id = article[0]
        article_title = article[1]
        article_time = article[3]
        article_embedding = parse_embedding(
            article[4]
        )

        print()
        print("-" * 70)

        print(
            f"ARTICLE {article_id}"
        )

        print(article_title)

        print()

        results = []

        for story in stories:

            story_id = story[0]
            story_title = story[1]
            story_time = story[3]
            story_embedding = parse_embedding(
                story[4]
            )

            semantic = cosine_similarity(
                article_embedding,
                story_embedding,
            )

            time_score = calculate_time_similarity(
                article_time,
                story_time,
            )

            final_score = calculate_match_score(
                semantic,
                time_score,
            )

            results.append({
                "story_id": story_id,
                "story_title": story_title,
                "semantic": semantic,
                "time": time_score,
                "score": final_score,
            })

        # Highest score first
        results.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        # Show top 3 candidates
        for result in results[:3]:

            print(
                f"Story {result['story_id']}"
            )

            print(
                f"  {result['story_title']}"
            )

            print(
                f"  Semantic: "
                f"{result['semantic']:.3f}"
            )

            print(
                f"  Time:     "
                f"{result['time']:.3f}"
            )

            print(
                f"  Score:    "
                f"{result['score']:.3f} "
                f"{get_label(result['score'])}"
            )

            print()

    print()
    print("=" * 70)
    print("Evaluation complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()