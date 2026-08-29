import spacy

from nlp.cleaning import clean_text


MODEL_NAME = "en_core_web_sm"

_nlp = None


# Entity types that are particularly useful for NewsLens.
USEFUL_ENTITY_TYPES = {
    "PERSON",
    "ORG",
    "GPE",
    "LOC",
    "FAC",
    "EVENT",
    "NORP",
    "PRODUCT",
    "WORK_OF_ART",
}


def get_nlp():

    global _nlp

    if _nlp is None:
        print("Loading spaCy model...")
        _nlp = spacy.load(MODEL_NAME)
        print("spaCy model loaded.")

    return _nlp


def extract_entities(text):

    if not text:
        return []

    # Clean HTML, URLs, whitespace, etc.
    text = clean_text(text)

    if not text:
        return []

    nlp = get_nlp()

    doc = nlp(text)

    entities = []

    for entity in doc.ents:

        if entity.label_ not in USEFUL_ENTITY_TYPES:
            continue

        entity_text = entity.text.strip()

        if not entity_text:
            continue

        entities.append({
            "text": entity_text,
            "label": entity.label_,
        })

    return entities


def normalize_entity(text):

    text = clean_text(text)

    return (
        text
        .lower()
        .strip()
        .replace("'s", "")
    )


def extract_normalized_entities(text):

    entities = extract_entities(text)

    return {
        normalize_entity(entity["text"])
        for entity in entities
        if normalize_entity(entity["text"])
    }