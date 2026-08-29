def calculate_entity_similarity(
    entities_a,
    entities_b,
):
    if not entities_a or not entities_b:
        return 0.0

    intersection = (
        entities_a & entities_b
    )

    union = (
        entities_a | entities_b
    )

    return len(intersection) / len(union) # This is Jaccard similarity.

