import numpy as np

from database.connection import get_connection
from database.repository import update_story_embedding


def get_story_articles():
    """
    Get all article embeddings associated with stories.
    """

    query = """
        select
            sa.story_id,
            a.embedding
        from story_articles sa
        join articles a
            on a.id = sa.article_id
        where a.embedding is not null
        order by sa.story_id;
    """

    with get_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(query)

            return cursor.fetchall()


def parse_embedding(embedding):
    """
    Convert a PostgreSQL/pgvector embedding into
    a Python list of floats.

    PostgreSQL may return the vector as a string like:

        '[0.123,0.456,-0.789,...]'

    or it may already be returned as a list/array.
    """

    if embedding is None:
        return None

    # PostgreSQL/pgvector may return a string
    if isinstance(embedding, str):

        embedding = embedding.strip()

        # Remove surrounding brackets
        if embedding.startswith("[") and embedding.endswith("]"):
            embedding = embedding[1:-1]

        if not embedding:
            return None

        values = [
            float(value.strip())
            for value in embedding.split(",")
        ]

        return values

    # Already a list/tuple/array
    return [
        float(value)
        for value in embedding
    ]


def calculate_story_embedding(embeddings):
    """
    Calculate a normalized average embedding
    from all article embeddings belonging to a story.
    """

    parsed_embeddings = []

    for embedding in embeddings:

        parsed = parse_embedding(embedding)

        if parsed is not None:
            parsed_embeddings.append(parsed)

    if not parsed_embeddings:
        return None

    vectors = np.array(
        parsed_embeddings,
        dtype=np.float32,
    )

    # Safety check
    if vectors.ndim != 2:
        raise ValueError(
            f"Unexpected embedding shape: {vectors.shape}"
        )

    # All embeddings should have the same dimensions
    dimensions = vectors.shape[1]

    if dimensions != 384:
        raise ValueError(
            f"Expected 384-dimensional embeddings, "
            f"but found {dimensions} dimensions."
        )

    # Average all article embeddings
    average = vectors.mean(axis=0)

    # Normalize the resulting story embedding
    norm = np.linalg.norm(average)

    if norm > 0:
        average = average / norm

    return average


def main():

    print("Loading story/article embeddings...")

    rows = get_story_articles()

    if not rows:

        print("No story/article embeddings found.")

        return

    # Group article embeddings by story
    stories = {}

    for story_id, embedding in rows:

        stories.setdefault(
            story_id,
            []
        ).append(
            embedding
        )

    print(
        f"Found {len(stories)} stories."
    )

    print()

    successful = 0
    failed = 0

    for story_id, embeddings in stories.items():

        try:

            story_embedding = (
                calculate_story_embedding(
                    embeddings
                )
            )

            if story_embedding is None:

                print(
                    f"Skipping story {story_id}: "
                    f"no valid embeddings."
                )

                failed += 1

                continue

            update_story_embedding(
                story_id,
                story_embedding,
            )

            print(
                f"Updated story {story_id} "
                f"({len(embeddings)} articles)"
            )

            successful += 1

        except Exception as error:

            print(
                f"ERROR processing story "
                f"{story_id}: {error}"
            )

            failed += 1

    print()
    print("========== SUMMARY ==========")
    print(
        f"Stories found: {len(stories)}"
    )
    print(
        f"Successfully updated: {successful}"
    )
    print(
        f"Failed: {failed}"
    )
    print("=============================")


if __name__ == "__main__":
    main()