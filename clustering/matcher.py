from clustering.entity_similarity import (
    calculate_entity_similarity,
)

from clustering.time_similarity import (
    calculate_time_similarity,
)

from clustering.match_score import (
    calculate_match_score,
)


def match_article_to_story(
    article,
    story_articles,
    article_entities,
    story_entities,
    article_embedding,
    story_embedding,
):

    semantic_similarity = float(
        article_embedding @ story_embedding
    )

    entity_similarity = (
        calculate_entity_similarity(
            article_entities,
            story_entities,
        )
    )

    time_similarity = (
        calculate_time_similarity(
            article[4],
            story_articles[0][4],
        )
    )

    score = calculate_match_score(
        semantic_similarity,
        entity_similarity,
        time_similarity,
    )

    return {
        "semantic": semantic_similarity,
        "entity": entity_similarity,
        "time": time_similarity,
        "score": score,
    }