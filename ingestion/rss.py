import feedparser


def fetch_rss_feed(feed_url):
    """
    Fetch and parse an RSS feed.

    Returns:
        feedparser.FeedParserDict
    """
    feed = feedparser.parse(feed_url)

    if feed.bozo:
        print(f"Warning: RSS feed may have parsing issues: {feed_url}")

    return feed