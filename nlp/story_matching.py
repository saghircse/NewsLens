from nlp.entity_similarity import calculate_entity_similarity


# Initial weights.
#
# We intentionally make semantic similarity dominant.
SEMANTIC_WEIGHT = 0.75
ENTITY_WEIGHT = 0.25


def combine_similarity_scores(
    semantic_similarity,
    entity_similarity,
):
    """
    Combine semantic and entity similarity.

    Both inputs should be between 0 and 1.
    """

    score = (
        SEMANTIC_WEIGHT * semantic_similarity
        +
        ENTITY_WEIGHT * entity_similarity
    )

    return max(
        0.0,
        min(1.0, score),
    )


def calculate_story_match(
    semantic_similarity,
    entities_a,
    entities_b,
):
    """
    Calculate a combined article/story matching score.
    """

    entity_result = calculate_entity_similarity(
        entities_a,
        entities_b,
    )

    entity_similarity = entity_result[
        "weighted_similarity"
    ]

    combined_score = combine_similarity_scores(
        semantic_similarity,
        entity_similarity,
    )

    return {
        "semantic_similarity": semantic_similarity,
        "entity_similarity": entity_similarity,
        "combined_score": combined_score,
        "shared_entities": entity_result[
            "shared_entities"
        ],
        "shared_entity_count": entity_result[
            "shared_entity_count"
        ],
        "entity_jaccard": entity_result[
            "jaccard"
        ],
        "entity_overlap_ratio": entity_result[
            "overlap_ratio"
        ],
    }