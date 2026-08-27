from clustering.tfidf import calculate_similarity


def main():

    articles = [
        "India approves major semiconductor investment",
        "Government clears semiconductor plant in India",
        "India announces new chip manufacturing project",
        "Manchester United wins football match",
    ]

    similarity = calculate_similarity(articles)

    for i in range(len(articles)):
        print(f"\nArticle {i + 1}")

        for j in range(len(articles)):
            print(
                f"  vs Article {j + 1}: "
                f"{similarity[i][j]:.3f}"
            )


if __name__ == "__main__":
    main()