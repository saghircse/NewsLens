from ingestion.rss import fetch_rss_feed


FEED_URL = "https://www.theguardian.com/world/rss"


def main():
    feed = fetch_rss_feed(FEED_URL)

    print("Feed title:")
    print(feed.feed.get("title"))

    print("\nNumber of articles:")
    print(len(feed.entries))

    print("\nFirst five articles:")

    for entry in feed.entries[:5]:
        print("-", entry.get("title"))


if __name__ == "__main__":
    main()