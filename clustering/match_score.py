def calculate_match_score(
    semantic_similarity,
    entity_similarity,
    time_similarity,
):

    score = (
        0.60 * semantic_similarity
        + 0.25 * entity_similarity
        + 0.15 * time_similarity
    )

    return score