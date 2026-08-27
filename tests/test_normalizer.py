from ingestion.rss import fetch_rss_feed
from ingestion.normalizer import normalize_rss_entry


FEED_URL = "https://www.theguardian.com/world/rss"


def main():
    feed = fetch_rss_feed(FEED_URL)

    for entry in feed.entries[:3]:
        article = normalize_rss_entry(entry)

        print("\n--- ARTICLE ---")
        print("Title:", article["title"])
        print("URL:", article["url"])
        print("Author:", article["author"])
        print("Published:", article["published_at"])
        print("Description:", article["description"][:200])


if __name__ == "__main__":
    main()