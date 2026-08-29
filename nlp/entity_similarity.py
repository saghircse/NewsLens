from collections import defaultdict


# Entity weights.
#
# These are intentionally conservative.
# Semantic similarity remains the primary matching signal.
ENTITY_LABEL_WEIGHTS = {
    "PERSON": 1.00,
    "ORG": 1.00,
    "GPE": 0.90,
    "LOC": 0.90,
    "FAC": 0.80,
    "EVENT": 0.90,
    "NORP": 0.60,
    "PRODUCT": 0.60,
    "WORK_OF_ART": 0.50,
}


def entity_set(entities):
    """
    Convert extracted entity dictionaries into a set
    of normalized entity strings.

    Example:

    [
        {
            "text": "Donald Trump",
            "label": "PERSON",
            "normalized": "donald trump",
        }
    ]

    becomes:

    {
        "donald trump"
    }
    """

    result = set()

    if not entities:
        return result

    for entity in entities:

        normalized = entity.get("normalized")

        if normalized:
            result.add(normalized)

    return result


def entity_label_map(entities):
    """
    Create:

        normalized_entity -> label

    If an entity appears multiple times with different labels,
    the first useful label encountered is retained.
    """

    result = {}

    if not entities:
        return result

    for entity in entities:

        normalized = entity.get("normalized")
        label = entity.get("label")

        if not normalized:
            continue

        if normalized not in result:
            result[normalized] = label

    return result


def shared_entities(entities_a, entities_b):
    """
    Return normalized entities appearing in both articles.
    """

    set_a = entity_set(entities_a)
    set_b = entity_set(entities_b)

    return sorted(set_a.intersection(set_b))


def entity_jaccard_similarity(entities_a, entities_b):
    """
    Standard Jaccard similarity:

        intersection / union

    Returns a value between 0 and 1.
    """

    set_a = entity_set(entities_a)
    set_b = entity_set(entities_b)

    if not set_a and not set_b:
        return 0.0

    union = set_a.union(set_b)

    if not union:
        return 0.0

    intersection = set_a.intersection(set_b)

    return len(intersection) / len(union)


def weighted_entity_similarity(entities_a, entities_b):
    """
    Calculate entity similarity while giving more importance
    to useful entity types.

    Returns a value between 0 and 1.
    """

    set_a = entity_set(entities_a)
    set_b = entity_set(entities_b)

    if not set_a or not set_b:
        return 0.0

    labels_a = entity_label_map(entities_a)
    labels_b = entity_label_map(entities_b)

    union = set_a.union(set_b)
    intersection = set_a.intersection(set_b)

    if not union:
        return 0.0

    intersection_weight = 0.0
    union_weight = 0.0

    for entity in union:

        label_a = labels_a.get(entity)
        label_b = labels_b.get(entity)

        weight_a = ENTITY_LABEL_WEIGHTS.get(
            label_a,
            0.50,
        )

        weight_b = ENTITY_LABEL_WEIGHTS.get(
            label_b,
            0.50,
        )

        weight = max(weight_a, weight_b)

        union_weight += weight

        if entity in intersection:
            intersection_weight += weight

    if union_weight == 0:
        return 0.0

    return intersection_weight / union_weight


def entity_overlap_ratio(entities_a, entities_b):
    """
    Calculate how much of the smaller entity set overlaps
    with the larger set.

    This is useful when one article mentions many entities
    and another article mentions only the key entities.

    Example:

        A = {trump, canada, ontario, mexico}
        B = {trump, canada}

        overlap = 2 / 2 = 1.0
    """

    set_a = entity_set(entities_a)
    set_b = entity_set(entities_b)

    if not set_a or not set_b:
        return 0.0

    intersection = set_a.intersection(set_b)

    smaller_size = min(
        len(set_a),
        len(set_b),
    )

    if smaller_size == 0:
        return 0.0

    return len(intersection) / smaller_size


def calculate_entity_similarity(entities_a, entities_b):
    """
    Return all useful entity similarity metrics.
    """

    shared = shared_entities(
        entities_a,
        entities_b,
    )

    jaccard = entity_jaccard_similarity(
        entities_a,
        entities_b,
    )

    weighted = weighted_entity_similarity(
        entities_a,
        entities_b,
    )

    overlap = entity_overlap_ratio(
        entities_a,
        entities_b,
    )

    return {
        "shared_entities": shared,
        "shared_entity_count": len(shared),
        "jaccard": jaccard,
        "weighted_similarity": weighted,
        "overlap_ratio": overlap,
    }