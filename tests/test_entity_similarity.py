from nlp.entity_similarity import (
    entity_set,
    shared_entities,
    entity_jaccard_similarity,
    weighted_entity_similarity,
    entity_overlap_ratio,
    calculate_entity_similarity,
)


def main():

    article_a = [
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

    article_b = [
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
            "text": "Ontario",
            "label": "GPE",
            "normalized": "ontario",
        },
    ]

    print("\n========== ENTITY SIMILARITY TEST ==========\n")

    print("Article A entities:")
    print(entity_set(article_a))

    print("\nArticle B entities:")
    print(entity_set(article_b))

    shared = shared_entities(
        article_a,
        article_b,
    )

    print("\nShared entities:")
    print(shared)

    jaccard = entity_jaccard_similarity(
        article_a,
        article_b,
    )

    print(
        f"\nJaccard similarity: "
        f"{jaccard:.4f}"
    )

    weighted = weighted_entity_similarity(
        article_a,
        article_b,
    )

    print(
        f"Weighted similarity: "
        f"{weighted:.4f}"
    )

    overlap = entity_overlap_ratio(
        article_a,
        article_b,
    )

    print(
        f"Overlap ratio: "
        f"{overlap:.4f}"
    )

    result = calculate_entity_similarity(
        article_a,
        article_b,
    )

    print("\nComplete result:")
    print(result)

    assert shared == [
        "canada",
        "donald trump",
    ]

    assert jaccard > 0

    assert weighted > 0

    assert overlap > 0

    print(
        "\nEntity similarity tests: PASS"
    )

    print(
        "\n============================================\n"
    )


if __name__ == "__main__":
    main()