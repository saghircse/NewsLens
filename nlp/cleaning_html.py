import re
from html import unescape
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):

    def __init__(self):

        super().__init__()

        self.parts = []

    def handle_data(self, data):

        if data:
            self.parts.append(data)

    def get_text(self):

        return " ".join(self.parts)


def clean_text(text):

    if not text:
        return ""

    # Decode HTML entities such as &amp;
    text = unescape(text)

    # Extract actual text from HTML.
    parser = HTMLTextExtractor()

    try:

        parser.feed(text)
        parser.close()

        text = parser.get_text()

    except Exception:

        # Fallback if malformed HTML causes parser problems.
        text = re.sub(
            r"<[^>]*>",
            " ",
            text,
        )

    # Remove URLs.
    text = re.sub(
        r"https?://\S+|www\.\S+",
        " ",
        text,
    )

    # Remove excessive whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()