import spacy


MODEL_NAME = "en_core_web_sm"

_nlp = None


def get_nlp():

    global _nlp

    if _nlp is None:
        print("Loading spaCy model...")
        _nlp = spacy.load(MODEL_NAME)
        print("spaCy model loaded.")

    return _nlp


def extract_entities(text):

    nlp = get_nlp()

    doc = nlp(text)

    entities = []

    for entity in doc.ents:

        entities.append({
            "text": entity.text,
            "label": entity.label_,
        })

    return entities

def normalize_entity(text):

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
    }