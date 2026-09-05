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
            status,
            created_at
        FROM stories
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
            sa.similarity_score,
            s.name AS source
        FROM story_articles sa
        JOIN articles a
            ON a.id = sa.article_id
        LEFT JOIN sources s
            ON s.id = a.source_id
        WHERE sa.story_id = %s
        ORDER BY
            sa.similarity_score DESC NULLS LAST,
            a.published_at DESC NULLS LAST,
            a.id;
    """

    with conn.cursor() as cursor:
        cursor.execute(
            query,
            (story_id,),
        )
        return cursor.fetchall()


def main():

    print("=" * 70)
    print("NewsLens — STORY REPRESENTATION REVIEW")
    print("=" * 70)

    with get_connection() as conn:

        stories = get_stories(conn)

        print()
        print(f"Stories found: {len(stories)}")

        for (
            story_id,
            title,
            summary,
            why_it_matters,
            category,
            importance_score,
            first_seen_at,
            last_updated_at,
            status,
            created_at,
        ) in stories:

            print()
            print("-" * 70)
            print(f"STORY {story_id}")
            print("-" * 70)

            print(f"Title:             {title}")
            print(f"Summary:           {summary}")
            print(f"Why it matters:    {why_it_matters}")
            print(f"Category:          {category}")
            print(f"Importance score:  {importance_score}")
            print(f"First seen:        {first_seen_at}")
            print(f"Last updated:      {last_updated_at}")
            print(f"Status:            {status}")
            print(f"Created:           {created_at}")

            articles = get_story_articles(
                conn,
                story_id,
            )

            print()
            print(f"Articles: {len(articles)}")

            for (
                article_id,
                article_title,
                published_at,
                similarity_score,
                source,
            ) in articles:

                print(
                    f"  {article_id}: "
                    f"{similarity_score} | "
                    f"{source} | "
                    f"{published_at}"
                )

                print(
                    f"      {article_title}"
                )

    print()
    print("=" * 70)
    print("Review complete.")
    print("No database changes were made.")
    print("=" * 70)


if __name__ == "__main__":
    main()