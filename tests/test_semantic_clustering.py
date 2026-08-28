from database.repository import get_articles_for_clustering
from clustering.semantic import cluster_articles_semantically


def main():

    articles = get_articles_for_clustering(
        limit=50
    )

    print(
        f"Loaded {len(articles)} articles."
    )

    if not articles:
        print("No articles found.")
        return

    clusters = cluster_articles_semantically(
        articles,
        threshold=0.65,
    )

    print(
        f"\nCreated {len(clusters)} clusters."
    )

    for number, cluster in enumerate(
        clusters,
        start=1,
    ):

        print(
            f"\n========== CLUSTER {number} =========="
        )

        for index in cluster:

            article = articles[index]

            article_id = article[0]
            title = article[1]

            print(
                f"{article_id}: {title}"
            )


if __name__ == "__main__":
    main()