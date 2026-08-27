from database.repository import (
    get_active_sources,
    insert_article,
)
from ingestion.rss import fetch_rss_feed
from ingestion.normalizer import normalize_rss_entry


def ingest_rss_sources():
    sources = get_active_sources()

    total_found = 0
    total_inserted = 0

    for source_id, source_name, feed_url in sources:

        print(f"\nProcessing: {source_name}")
        print(f"Feed: {feed_url}")

        feed = fetch_rss_feed(feed_url)

        print(f"Found {len(feed.entries)} entries")

        for entry in feed.entries:

            total_found += 1

            article = normalize_rss_entry(entry)

            if not article["title"] or not article["url"]:
                continue

            article_id = insert_article(
                source_id=source_id,
                title=article["title"],
                url=article["url"],
                description=article["description"],
                author=article["author"],
                published_at=article["published_at"],
            )

            if article_id:
                total_inserted += 1
                print(f"  Added: {article['title']}")

    print("\n==============================")
    print("INGESTION COMPLETE")
    print("==============================")
    print(f"Entries found: {total_found}")
    print(f"Articles inserted: {total_inserted}")