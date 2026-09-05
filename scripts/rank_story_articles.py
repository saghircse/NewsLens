from database.connection import get_connection


def get_stories(conn):
    query = """
        SELECT
            id,
            title,
            importance_score,
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


def main():

    print("=" * 70)
    print("NewsLens — STORY ARTICLE RANKING")
    print("=" * 70)

    with get_connection() as conn:

        stories = get_stories(conn)

        print()
        print(f"Active stories: {len(stories)}")

        for (
            story_id,
            story_title,
            importance_score,
            status,
        ) in stories:

            print()
            print("-" * 70)
            print(f"STORY {story_id}")
            print("-" * 70)

            print(f"Title: {story_title}")
            print(f"Importance score: {importance_score}")

            articles = get_story_articles(
                conn,
                story_id,
            )

            if not articles:
                print()
                print("No articles mapped.")
                continue

            print()
            print(f"Articles: {len(articles)}")

            for rank, (
                article_id,
                article_title,
                published_at,
                similarity_score,
            ) in enumerate(articles, start=1):

                similarity_text = (
                    f"{similarity_score:.4f}"
                    if similarity_score is not None
                    else "N/A"
                )

                print(
                    f"\n  #{rank}"
                    f"\n  Article ID:    {article_id}"
                    f"\n  Similarity:    {similarity_text}"
                    f"\n  Published:     {published_at}"
                    f"\n  Title:         {article_title}"
                )

            top_article = articles[0]

            print()
            print("  REPRESENTATIVE ARTICLE")
            print(
                f"    Article ID: {top_article[0]}"
            )
            print(
                f"    Similarity: "
                f"{top_article[3]:.4f}"
                if top_article[3] is not None
                else "    Similarity: N/A"
            )
            print(
                f"    Title: {top_article[1]}"
            )

    print()
    print("=" * 70)
    print("Ranking complete.")
    print("No database changes were made.")
    print("=" * 70)


if __name__ == "__main__":
    main()