import spacy


MODEL_NAME = "en_core_web_sm"


def main():

    print("Loading spaCy model...")

    nlp = spacy.load(MODEL_NAME)

    text = """
    India approves a major semiconductor investment
    involving Tata Electronics and the government.
    """

    doc = nlp(text)

    print("\nEntities:")

    for entity in doc.ents:
        print(
            f"{entity.text} "
            f"→ {entity.label_}"
        )



if __name__ == "__main__":
    main()