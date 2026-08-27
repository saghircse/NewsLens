from database.repository import (
    create_story,
    link_article_to_story,
)


def build_stories(articles, clusters):

    created_stories = []

    for cluster in clusters:

        # Ignore single-article clusters for now.
        if len(cluster) < 2:
            continue

        cluster_articles = [
            articles[index]
            for index in cluster
        ]

        # Use the first article's title as a temporary story title.
        first_article = cluster_articles[0]

        story_title = first_article[1]

        published_dates = [
            article[4]
            for article in cluster_articles
            if article[4] is not None
        ]

        first_seen = min(published_dates) if published_dates else None
        last_updated = max(published_dates) if published_dates else None

        story_id = create_story(
            title=story_title,
            first_seen_at=first_seen,
            last_updated_at=last_updated,
        )

        for article in cluster_articles:

            article_id = article[0]

            link_article_to_story(
                story_id=story_id,
                article_id=article_id,
            )

        created_stories.append(story_id)

    return created_stories