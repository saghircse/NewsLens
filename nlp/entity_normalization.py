import re
import unicodedata


def normalize_entity_text(text):
    """
    Basic normalization for an entity string.

    This function intentionally does NOT try to determine
    whether two different names refer to the same real-world entity.
    """

    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)

    text = text.lower().strip()

    # Normalize curly apostrophes.
    text = text.replace("’", "'")

    # Remove possessive endings.
    text = re.sub(r"'s$", "", text)

    # Remove a trailing plural possessive.
    text = re.sub(r"s'$", "s", text)

    # Collapse repeated whitespace.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def canonicalize_entity(text, label=None):
    """
    Return a conservative canonical representation.

    We deliberately avoid broad mappings such as:
        American -> United States
        Canadian -> Canada

    because those can create false matches.
    """

    normalized = normalize_entity_text(text)

    if not normalized:
        return ""

    # Common safe abbreviations.
    # These are only applied where the meaning is sufficiently clear.
    safe_mappings = {
        "u.s.": "united states",
        "u.s": "united states",
        "us": "united states",

        "u.k.": "united kingdom",
        "u.k": "united kingdom",
        "uk": "united kingdom",

        "uae": "united arab emirates",
    }

    return safe_mappings.get(normalized, normalized)