from database.repository import get_latest_articles


def main():
    articles = get_latest_articles()

    for article in articles:
        print(article)


if __name__ == "__main__":
    main()