import argparse

from scripts.match_articles_to_stories import (
    MATCH_THRESHOLD,
    POSSIBLE_THRESHOLD,
    find_best_story,
    get_articles,
    get_stories,
    prepare_story_data,
    save_mapping,
)


# ============================================================
# Database helpers
# ============================================================

def get_mapped_article_ids():
    """
    Return article IDs that are already assigned to a story.

    We intentionally query story_articles directly rather than
    relying on an articles.story_id column.
    """

    from database.connection import get_connection

    query = """
        SELECT DISTINCT article_id
        FROM story_articles
        ORDER BY article_id;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)

            return {
                row[0]
                for row in cursor.fetchall()
            }


# ============================================================
# Output helpers
# ============================================================

def print_match(article, result):
    """
    Print the matching result for one article.
    """

    print()
    print("-" * 70)

    print(
        f"Article {article['id']}: "
        f"{article['title']}"
    )

    if result is None:
        print("No stories available.")
        return

    print(
        f"Best story: {result['story_id']}"
    )

    print(
        f"  {result['story_title']}"
    )

    print(
        f"  Semantic similarity: "
        f"{result['semantic_score']:.4f}"
    )

    print(
        f"  Entity similarity:   "
        f"{result['entity_score']:.4f}"
    )

    print(
        f"  Title similarity:    "
        f"{result['title_score']:.4f}"
    )

    print(
        f"  Combined score:      "
        f"{result['combined_score']:.4f}"
    )

    if result.get("exact_title_match"):
        print(
            "  Exact title match:   YES"
        )
    else:
        print(
            "  Exact title match:   NO"
        )

    if result["shared_entities"]:
        print(
            "  Shared entities:     "
            f"{result['shared_entities']}"
        )
    else:
        print(
            "  Shared entities:     none"
        )

    score = result["combined_score"]

    if score >= MATCH_THRESHOLD:

        print(
            f"  Decision: MATCH "
            f"(>= {MATCH_THRESHOLD:.2f})"
        )

    elif score >= POSSIBLE_THRESHOLD:

        print(
            f"  Decision: POSSIBLE "
            f"(>= {POSSIBLE_THRESHOLD:.2f})"
        )

    else:

        print(
            f"  Decision: NO MATCH "
            f"(< {POSSIBLE_THRESHOLD:.2f})"
        )


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Match previously-unmatched NewsLens articles "
            "to existing stories."
        )
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Calculate matches without modifying "
            "the database."
        ),
    )

    args = parser.parse_args()

    print()
    print("=" * 70)
    print("NEWSLENS — UPDATE EXISTING STORIES")
    print("=" * 70)

    # --------------------------------------------------------
    # Load articles
    # --------------------------------------------------------

    print()
    print("Loading articles...")

    articles = get_articles()

    print(
        f"Found {len(articles)} articles "
        "with embeddings."
    )

    if not articles:
        print("No articles available.")
        return

    # --------------------------------------------------------
    # Find already assigned articles
    # --------------------------------------------------------

    print()
    print("Loading existing story/article mappings...")

    mapped_article_ids = get_mapped_article_ids()

    print(
        f"Found {len(mapped_article_ids)} "
        "articles already assigned to stories."
    )

    # --------------------------------------------------------
    # Filter unmatched articles
    # --------------------------------------------------------

    unmatched_articles = [
        article
        for article in articles
        if article["id"] not in mapped_article_ids
    ]

    print()
    print(
        f"Unmatched articles available for "
        f"existing-story matching: "
        f"{len(unmatched_articles)}"
    )

    if not unmatched_articles:
        print()
        print(
            "No unmatched articles found."
        )
        return

    # --------------------------------------------------------
    # Load stories
    # --------------------------------------------------------

    print()
    print("Loading existing stories...")

    stories = get_stories()

    print(
        f"Found {len(stories)} existing stories."
    )

    if not stories:
        print(
            "No existing stories with embeddings found."
        )
        return

    # --------------------------------------------------------
    # Prepare stories
    # --------------------------------------------------------

    print()
    print("Preparing story entities...")

    prepared_stories = prepare_story_data(
        stories
    )

    print("Story entities prepared.")

    # --------------------------------------------------------
    # Matching configuration
    #
    # These values come directly from
    # match_articles_to_stories.py.
    # --------------------------------------------------------

    print()
    print("Matching configuration:")

    from scripts.match_articles_to_stories import (
        SEMANTIC_WEIGHT,
        ENTITY_WEIGHT,
        TITLE_WEIGHT,
    )

    print(
        f"  Semantic weight:   "
        f"{SEMANTIC_WEIGHT:.2f}"
    )

    print(
        f"  Entity weight:     "
        f"{ENTITY_WEIGHT:.2f}"
    )

    print(
        f"  Title weight:      "
        f"{TITLE_WEIGHT:.2f}"
    )

    print(
        f"  Match threshold:   "
        f"{MATCH_THRESHOLD:.2f}"
    )

    print(
        f"  Possible threshold:"
        f" {POSSIBLE_THRESHOLD:.2f}"
    )

    # --------------------------------------------------------
    # Match articles
    # --------------------------------------------------------

    print()
    print(
        "Matching unmatched articles "
        "to existing stories..."
    )

    matched_count = 0
    possible_count = 0
    unmatched_count = 0
    failed_count = 0
    persisted_count = 0

    for index, article in enumerate(
        unmatched_articles,
        start=1,
    ):

        try:

            result, _, _ = find_best_story(
                article,
                prepared_stories,
            )

            print()
            print(
                f"[{index}/{len(unmatched_articles)}]"
            )

            print_match(
                article,
                result,
            )

            if result is None:

                unmatched_count += 1
                continue

            score = result["combined_score"]

            # ------------------------------------------------
            # Strong match
            # ------------------------------------------------

            if score >= MATCH_THRESHOLD:

                matched_count += 1

                if not args.dry_run:

                    save_mapping(
                        story_id=result["story_id"],
                        article_id=article["id"],
                        similarity_score=score,
                    )

                    persisted_count += 1

            # ------------------------------------------------
            # Possible match
            #
            # Do NOT automatically persist these.
            # They require review / future policy.
            # ------------------------------------------------

            elif score >= POSSIBLE_THRESHOLD:

                possible_count += 1

            # ------------------------------------------------
            # No match
            # ------------------------------------------------

            else:

                unmatched_count += 1

        except Exception as exc:

            failed_count += 1

            print()
            print(
                f"ERROR processing article "
                f"{article['id']}: {exc}"
            )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(
        f"Articles considered:  "
        f"{len(unmatched_articles)}"
    )

    print(
        f"Matched:              "
        f"{matched_count}"
    )

    print(
        f"Possible:              "
        f"{possible_count}"
    )

    print(
        f"Unmatched:             "
        f"{unmatched_count}"
    )

    print(
        f"Failed:                "
        f"{failed_count}"
    )

    print(
        f"Persisted:             "
        f"{persisted_count}"
    )

    print("=" * 70)

    if args.dry_run:

        print()
        print(
            "Dry run complete. "
            "No database changes made."
        )

    else:

        print()
        print(
            f"Existing stories updated: "
            f"{persisted_count}"
        )


if __name__ == "__main__":
    main()