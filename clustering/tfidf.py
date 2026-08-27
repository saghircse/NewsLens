from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def calculate_similarity(texts):
    """
    Calculate pairwise TF-IDF cosine similarity.

    Args:
        texts: list of strings

    Returns:
        similarity matrix
    """

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
    )

    matrix = vectorizer.fit_transform(texts)

    return cosine_similarity(matrix)