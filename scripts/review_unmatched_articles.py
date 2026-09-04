import psycopg
import os
from database.connection import get_connection

def get_unmatched_articles(conn):
    query = """
        SELECT
            a.id,
            a.title,
            a.published_at,
            s.name AS source
        FROM articles a
        LEFT JOIN story_articles sa
            ON sa.article_id = a.id
        LEFT JOIN sources s
            ON s.id = a.source_id
        WHERE sa.article_id IS NULL
        ORDER BY a.id;
    """

    with conn.cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall()


def main():

    print("=" * 60)
    print("NewsLens — UNMATCHED ARTICLE REVIEW")
    print("=" * 60)

    with get_connection() as conn:

        articles = get_unmatched_articles(conn)

    print()
    print(f"Unmatched articles: {len(articles)}")
    print()

    for article_id, title, published_at, source in articles:

        print("-" * 60)
        print(f"Article ID: {article_id}")
        print(f"Title:      {title}")
        print(f"Published:  {published_at}")
        print(f"Source:     {source}")
        print()

    print("=" * 60)
    print("Review complete.")
    print("No database changes were made.")
    print("=" * 60)


if __name__ == "__main__":
    main()