from database.repository import get_articles_for_clustering
from clustering.cluster import cluster_articles


def main():

    articles = get_articles_for_clustering(limit=50)

    print(f"Loaded {len(articles)} articles")

    clusters = cluster_articles(
        articles,
        threshold=0.25,
    )

    print(f"Created {len(clusters)} clusters")

    for number, cluster in enumerate(clusters, start=1):

        print(f"\n========== CLUSTER {number} ==========")

        for index in cluster:

            article = articles[index]

            article_id = article[0]
            title = article[1]

            print(f"{article_id}: {title}")


if __name__ == "__main__":
    main()