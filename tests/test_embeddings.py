from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def main():
    model = SentenceTransformer(MODEL_NAME)

    texts = [
        "India approves major semiconductor investment",
        "Government clears semiconductor manufacturing project",
        "Manchester United wins a football match",
    ]

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
    )

    similarity = cosine_similarity(embeddings)

    for i in range(len(texts)):
        print(f"\n{texts[i]}")

        for j in range(len(texts)):
            print(
                f"  vs {j + 1}: "
                f"{similarity[i][j]:.3f}"
            )


if __name__ == "__main__":
    main()