from sklearn.metrics.pairwise import cosine_similarity


def calculate_embedding_similarity(embeddings):
    return cosine_similarity(embeddings)