from embeddings.model import generate_embeddings
from embeddings.similarity import calculate_embedding_similarity


def cluster_articles_semantically(
    articles,
    threshold=0.65,
):
    """
    Cluster articles using semantic embeddings.

    Args:
        articles:
            Article database records.

        threshold:
            Minimum cosine similarity for grouping.

    Returns:
        List of clusters containing article indexes.
    """

    if not articles:
        return []

    texts = []

    for article in articles:
        title = article[1]
        description = article[2] or ""

        text = f"{title}. {description}"

        texts.append(text)

    print("Generating embeddings...")

    embeddings = generate_embeddings(texts)

    print("Calculating semantic similarity...")

    similarity = calculate_embedding_similarity(
        embeddings
    )

    clusters = []
    assigned = set()

    for i in range(len(articles)):

        if i in assigned:
            continue

        cluster = [i]
        assigned.add(i)

        for j in range(i + 1, len(articles)):

            if j in assigned:
                continue

            score = similarity[i][j]

            if score >= threshold:
                cluster.append(j)
                assigned.add(j)

        clusters.append(cluster)

    return clusters