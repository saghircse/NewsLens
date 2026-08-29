from nlp.story_entities import aggregate_story_entities


def main():

    article_1 = [
        {
            "text": "Donald Trump",
            "label": "PERSON",
            "normalized": "donald trump",
        },
        {
            "text": "Canada",
            "label": "GPE",
            "normalized": "canada",
        },
        {
            "text": "Lake Ontario",
            "label": "LOC",
            "normalized": "lake ontario",
        },
    ]

    article_2 = [
        {
            "text": "Trump",
            "label": "PERSON",
            "normalized": "trump",
        },
        {
            "text": "Canada",
            "label": "GPE",
            "normalized": "canada",
        },
        {
            "text": "Ontario",
            "label": "GPE",
            "normalized": "ontario",
        },
    ]

    article_3 = [
        {
            "text": "Donald Trump",
            "label": "PERSON",
            "normalized": "donald trump",
        },
        {
            "text": "Canada",
            "label": "GPE",
            "normalized": "canada",
        },
    ]

    result = aggregate_story_entities(
        [
            article_1,
            article_2,
            article_3,
        ]
    )

    print("\n========== STORY ENTITY AGGREGATION ==========\n")

    for entity in result:

        print(
            f"{entity['text']:<20} "
            f"{entity['label']:<10} "
            f"articles={entity['article_count']}"
        )

    print(
        "\n==============================================\n"
    )


if __name__ == "__main__":
    main()