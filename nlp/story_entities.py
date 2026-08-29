from collections import Counter, defaultdict


def aggregate_story_entities(article_entities):

    """
    Aggregate entities from multiple articles belonging
    to the same story.

    article_entities should be:

    [
        [
            {"text": "...", "label": "...", "normalized": "..."},
            ...
        ],
        [
            {"text": "...", "label": "...", "normalized": "..."},
            ...
        ]
    ]
    """

    counts = Counter()
    labels = defaultdict(Counter)
    display_names = defaultdict(Counter)

    for entities in article_entities:

        # Count an entity at most once per article.
        seen_in_article = set()

        for entity in entities:

            normalized = entity.get("normalized")

            if not normalized:
                continue

            if normalized in seen_in_article:
                continue

            seen_in_article.add(normalized)

            counts[normalized] += 1

            label = entity.get("label")

            if label:
                labels[normalized][label] += 1

            text = entity.get("text")

            if text:
                display_names[normalized][text] += 1

    result = []

    for normalized, article_count in counts.most_common():

        most_common_label = None

        if labels[normalized]:
            most_common_label = (
                labels[normalized]
                .most_common(1)[0][0]
            )

        display_name = normalized

        if display_names[normalized]:

            display_name = (
                display_names[normalized]
                .most_common(1)[0][0]
            )

        result.append({
            "normalized": normalized,
            "text": display_name,
            "label": most_common_label,
            "article_count": article_count,
        })

    return result