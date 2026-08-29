from nlp.entities import extract_entities


def main():

    text = """
    Donald Trump's government announced a new policy
    involving the United States and Canada.

    Canadian companies and American investors are watching
    the announcement closely.
    """

    print("\n========== ENTITY EXTRACTION TEST ==========\n")

    entities = extract_entities(text)

    for entity in entities:

        print(
            f"Text:       {entity['text']}"
        )

        print(
            f"Label:      {entity['label']}"
        )

        print(
            f"Normalized: {entity['normalized']}"
        )

        print()


if __name__ == "__main__":
    main()