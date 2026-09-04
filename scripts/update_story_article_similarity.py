import ast
import math

from database.connection import get_connection


# ============================================================
# Vector helpers
# ============================================================

def parse_embedding(value):

    """
    Convert a PostgreSQL pgvector value into a Python list.

    Depending on the driver/database representation, the value
    may already be a list/tuple or may be returned as a string.
    """

    if value is None:
        return None

    if isinstance(value, (list, tuple)):
        return [float(x) for x in value]

    if isinstance(value, str):

        value = value.strip()

        # PostgreSQL pgvector commonly returns:
        # [0.123,0.456,...]
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):

            # Fallback for pgvector strings without Python
            # spacing/formatting.
            value = value.strip("[]")

            if not value:
                return []

            return [
                float(x.strip())
                for x in value.split(",")
            ]

        if isinstance(parsed, (list, tuple)):

            return [
                float(x)
                for x in parsed
            ]

    raise ValueError(
        f"Unsupported embedding type: {type(value)}"
    )


def cosine_similarity(
    vector_a,
    vector_b,
):

    if vector_a is None or vector_b is None:
        return None

    if len(vector_a) != len(vector_b):

        raise ValueError(
            "Embedding dimensions do not match: "
            f"{len(vector_a)} vs {len(vector_b)}"
        )

    dot_product = sum(
        a * b
        for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = math.sqrt(
        sum(
            a * a
            for a in vector_a
        )
    )

    magnitude_b = math.sqrt(
        sum(
            b * b
            for b in vector_b
        )
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return None

    return dot_product / (
        magnitude_a * magnitude_b
    )


# ============================================================
# Database
# ============================================================

def get_story_article_embeddings(connection):

    query = """
        SELECT
            sa.story_id,
            sa.article_id,
            a.embedding,
            s.embedding
        FROM story_articles sa
        JOIN articles a
            ON a.id = sa.article_id
        JOIN stories s
            ON s.id = sa.story_id
        ORDER BY
            sa.story_id,
            sa.article_id
    """

    with connection.cursor() as cursor:

        cursor.execute(query)

        return cursor.fetchall()


def update_similarity(
    connection,
    story_id,
    article_id,
    similarity,
):

    query = """
        UPDATE story_articles
        SET similarity_score = %s
        WHERE story_id = %s
          AND article_id = %s
    """

    with connection.cursor() as cursor:

        cursor.execute(
            query,
            (
                similarity,
                story_id,
                article_id,
            ),
        )


# ============================================================
# Main
# ============================================================

def main():

    print(
        "============================================================"
    )

    print(
        "NewsLens — UPDATE STORY/ARTICLE SIMILARITY"
    )

    print(
        "============================================================"
    )

    print(
        "\nLoading story/article embeddings..."
    )

    with get_connection() as connection:

        rows = get_story_article_embeddings(
            connection
        )

        print(
            f"Found {len(rows)} story/article mappings."
        )

        if not rows:

            print(
                "\nNo story/article mappings found."
            )

            return

        updated = 0
        skipped = 0
        failed = 0

        print(
            "\nCalculating per-article similarity..."
        )

        for (
            story_id,
            article_id,
            article_embedding,
            story_embedding,
        ) in rows:

            try:

                article_vector = parse_embedding(
                    article_embedding
                )

                story_vector = parse_embedding(
                    story_embedding
                )

                if article_vector is None:

                    print(
                        f"SKIPPED: Story {story_id}, "
                        f"Article {article_id} — "
                        "article embedding is missing."
                    )

                    skipped += 1

                    continue

                if story_vector is None:

                    print(
                        f"SKIPPED: Story {story_id}, "
                        f"Article {article_id} — "
                        "story embedding is missing."
                    )

                    skipped += 1

                    continue

                similarity = cosine_similarity(
                    article_vector,
                    story_vector,
                )

                if similarity is None:

                    print(
                        f"SKIPPED: Story {story_id}, "
                        f"Article {article_id} — "
                        "unable to calculate similarity."
                    )

                    skipped += 1

                    continue

                update_similarity(
                    connection,
                    story_id,
                    article_id,
                    similarity,
                )

                print(
                    f"Updated story {story_id}, "
                    f"article {article_id}: "
                    f"{similarity:.4f}"
                )

                updated += 1

            except Exception as error:

                print(
                    f"FAILED: Story {story_id}, "
                    f"Article {article_id}: "
                    f"{error}"
                )

                failed += 1

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        connection.commit()

    print(
        "\n============================================================"
    )

    print(
        "SUMMARY"
    )

    print(
        "============================================================"
    )

    print(
        f"Mappings found: {len(rows)}"
    )

    print(
        f"Successfully updated: {updated}"
    )

    print(
        f"Skipped: {skipped}"
    )

    print(
        f"Failed: {failed}"
    )

    print(
        "============================================================"
    )

    print(
        "\nStage 7.14 complete."
    )


if __name__ == "__main__":
    main()