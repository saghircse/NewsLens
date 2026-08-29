import spacy

from nlp.cleaning import clean_text
from nlp.entity_normalization import canonicalize_entity


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

        normalized = canonicalize_entity(
            entity_text,
            entity.label_,
        )

        if not normalized:
            continue

        entities.append({
            "text": entity_text,
            "label": entity.label_,
            "normalized": normalized,
        })

    return entities


def normalize_entity(text):

    return canonicalize_entity(text)


def extract_normalized_entities(text):

    entities = extract_entities(text)

    return {
        entity["normalized"]
        for entity in entities
        if entity["normalized"]
    }