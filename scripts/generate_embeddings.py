from database.repository import (
    get_articles_for_clustering,
    update_article_embedding,
)

from embeddings.model import generate_embeddings


def main():

    articles = get_articles_for_clustering(
        limit=100
    )

    print(
        f"Found {len(articles)} articles."
    )

    if not articles:
        return

    texts = []

    for article in articles:

        title = article[1]
        description = article[2] or ""

        texts.append(
            f"{title}. {description}"
        )

    print("Generating embeddings...")

    embeddings = generate_embeddings(texts)

    print("Saving embeddings...")

    for article, embedding in zip(
        articles,
        embeddings,
    ):

        article_id = article[0]

        update_article_embedding(
            article_id,
            embedding,
        )

        print(
            f"Saved embedding for article "
            f"{article_id}"
        )

    print("Done.")


if __name__ == "__main__":
    main()