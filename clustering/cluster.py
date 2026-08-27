from clustering.tfidf import calculate_similarity


def cluster_articles(articles, threshold=0.25):
    """
    Group similar articles into clusters.

    Args:
        articles: list of article records
        threshold: similarity required to join a cluster

    Returns:
        list of clusters
    """

    if not articles:
        return []

    texts = []

    for article in articles:
        article_id, title, description, source_id, published_at = article

        text = f"{title} {description or ''}"

        texts.append(text)

    similarity = calculate_similarity(texts)

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

            if similarity[i][j] >= threshold:
                cluster.append(j)
                assigned.add(j)

        clusters.append(cluster)

    return clusters