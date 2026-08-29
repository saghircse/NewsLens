from nlp.story_matching import (
    combine_similarity_scores,
    calculate_story_match,
)


def main():

    print("\n========== STORY MATCHING TEST ==========\n")

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
    ]

    semantic_similarity = 0.80

    result = calculate_story_match(
        semantic_similarity,
        article_a,
        article_b,
    )

    print(
        f"Semantic similarity: "
        f"{result['semantic_similarity']:.4f}"
    )

    print(
        f"Entity similarity: "
        f"{result['entity_similarity']:.4f}"
    )

    print(
        f"Combined score: "
        f"{result['combined_score']:.4f}"
    )

    print(
        f"Shared entities: "
        f"{result['shared_entities']}"
    )

    assert result["combined_score"] > 0.80

    print(
        "\nStory matching test: PASS"
    )

    print(
        "\n========================================\n"
    )


if __name__ == "__main__":
    main()