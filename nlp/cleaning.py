import re
from html import unescape


def clean_text(text):

    if not text:
        return ""

    # Decode HTML entities such as &amp;
    text = unescape(text)

    # Remove HTML tags
    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    # Remove URLs
    text = re.sub(
        r"https?://\S+|www\.\S+",
        " ",
        text,
    )

    # Remove excessive whitespace
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()