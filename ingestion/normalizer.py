from datetime import datetime, timezone


def normalize_rss_entry(entry):
    """
    Convert an RSS entry into the standard NewsLens article format.
    """

    published_at = None

    if entry.get("published_parsed"):
        published_at = datetime(
            *entry.published_parsed[:6],
            tzinfo=timezone.utc,
        )

    return {
        "title": entry.get("title", "").strip(),
        "url": entry.get("link", "").strip(),
        "description": entry.get("summary", "").strip(),
        "author": entry.get("author"),
        "published_at": published_at,
    }