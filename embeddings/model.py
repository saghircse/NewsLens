from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


_model = None


def get_model():
    global _model

    if _model is None:
        print("Loading embedding model...")
        _model = SentenceTransformer(MODEL_NAME)
        print("Embedding model loaded.")

    return _model


def generate_embeddings(texts):
    model = get_model()

    return model.encode(
        texts,
        normalize_embeddings=True,
    )