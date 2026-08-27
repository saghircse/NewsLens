from database.repository import get_articles_for_clustering
from clustering.cluster import cluster_articles
from clustering.story_builder import build_stories


def main():

    print("Loading articles...")

    articles = get_articles_for_clustering(limit=100)

    print(f"Loaded {len(articles)} articles.")

    if not articles:
        print("No articles available.")
        return

    print("Calculating similarity...")

    clusters = cluster_articles(
        articles,
        threshold=0.25,
    )

    print(f"Created {len(clusters)} clusters.")

    multi_article_clusters = [
        cluster
        for cluster in clusters
        if len(cluster) >= 2
    ]

    print(
        f"Multi-source candidate stories: "
        f"{len(multi_article_clusters)}"
    )

    story_ids = build_stories(
        articles,
        multi_article_clusters,
    )

    print(
        f"Created {len(story_ids)} stories."
    )


if __name__ == "__main__":
    main()