import json
from pathlib import Path

from database.connection import get_connection


# ============================================================
# Configuration
# ============================================================

CANDIDATE_FILE = Path("candidate_new_stories.json")

MIN_ARTICLES_PER_STORY = 2
MIN_CLUSTER_SCORE = 0.60


# ============================================================
# Candidate loading
# ============================================================

def load_candidates():

    if not CANDIDATE_FILE.exists():
        raise FileNotFoundError(
            f"Candidate file not found: {CANDIDATE_FILE}"
        )

    with open(
        CANDIDATE_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    candidates = data.get("candidates", [])

    if not isinstance(candidates, list):
        raise ValueError(
            "The 'candidates' field must be a list."
        )

    return candidates


# ============================================================
# Database helpers
# ============================================================

def get_existing_article_ids(connection):

    query = """
        SELECT DISTINCT article_id
        FROM story_articles
    """

    with connection.cursor() as cursor:

        cursor.execute(query)

        return {
            row[0]
            for row in cursor.fetchall()
        }


def get_existing_story_titles(connection):

    query = """
        SELECT title
        FROM stories
    """

    with connection.cursor() as cursor:

        cursor.execute(query)

        return {
            row[0].strip().lower()
            for row in cursor.fetchall()
            if row[0]
        }


def insert_story(
    connection,
    candidate,
):

    query = """
        INSERT INTO stories (
            title,
            importance_score,
            status
        )
        VALUES (
            %s,
            %s,
            'active'
        )
        RETURNING id
    """

    title = candidate["title"]
    score = float(candidate["cluster_score"])

    with connection.cursor() as cursor:

        cursor.execute(
            query,
            (
                title,
                score,
            ),
        )

        return cursor.fetchone()[0]


def insert_story_articles(
    connection,
    story_id,
    article_ids,
    similarity_score,
):

    query = """
        INSERT INTO story_articles (
            story_id,
            article_id,
            similarity_score
        )
        VALUES (
            %s,
            %s,
            %s
        )
    """

    rows = [
        (
            story_id,
            article_id,
            similarity_score,
        )
        for article_id in article_ids
    ]

    with connection.cursor() as cursor:

        cursor.executemany(
            query,
            rows,
        )


# ============================================================
# Validation
# ============================================================

def validate_candidate(
    candidate,
    existing_article_ids,
    existing_story_titles,
):

    errors = []

    title = candidate.get("title", "")
    article_ids = candidate.get("article_ids", [])
    cluster_score = candidate.get("cluster_score", 0)

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    if not isinstance(title, str) or not title.strip():

        errors.append(
            "missing title"
        )

    # --------------------------------------------------------
    # Article IDs
    # --------------------------------------------------------

    if not isinstance(article_ids, list):

        errors.append(
            "article_ids is not a list"
        )

        article_ids = []

    if len(article_ids) < MIN_ARTICLES_PER_STORY:

        errors.append(
            f"fewer than {MIN_ARTICLES_PER_STORY} articles"
        )

    if len(article_ids) != len(set(article_ids)):

        errors.append(
            "duplicate article IDs"
        )

    # --------------------------------------------------------
    # Cluster score
    # --------------------------------------------------------

    try:

        cluster_score = float(cluster_score)

    except (TypeError, ValueError):

        errors.append(
            "invalid cluster score"
        )

        cluster_score = 0.0

    if cluster_score < MIN_CLUSTER_SCORE:

        errors.append(
            f"cluster score {cluster_score:.3f} "
            f"is below minimum {MIN_CLUSTER_SCORE:.3f}"
        )

    # --------------------------------------------------------
    # Already-mapped articles
    # --------------------------------------------------------

    already_mapped = [
        article_id
        for article_id in article_ids
        if article_id in existing_article_ids
    ]

    if already_mapped:

        errors.append(
            "articles already mapped to stories: "
            f"{already_mapped}"
        )

    # --------------------------------------------------------
    # Duplicate story title
    # --------------------------------------------------------

    normalized_title = title.strip().lower()

    if normalized_title in existing_story_titles:

        errors.append(
            "story title already exists"
        )

    return errors


# ============================================================
# Main
# ============================================================

def main():

    print(
        "============================================================"
    )
    print(
        "NewsLens — CREATE VALIDATED STORIES"
    )
    print(
        "============================================================"
    )

    print("\nLoading candidates...")

    candidates = load_candidates()

    print(
        f"Loaded {len(candidates)} candidates."
    )

    if not candidates:

        print("\nNo candidates to create.")

        return

    connection = None

    try:

        connection = get_connection()

        print(
            "\nConnected to database."
        )

        print(
            "Checking existing story/article mappings..."
        )

        existing_article_ids = get_existing_article_ids(
            connection
        )

        print(
            f"Found {len(existing_article_ids)} "
            "already-mapped articles."
        )

        print(
            "\nChecking existing story titles..."
        )

        existing_story_titles = get_existing_story_titles(
            connection
        )

        print(
            f"Found {len(existing_story_titles)} "
            "existing stories."
        )

        created_stories = []
        rejected_candidates = []

        # ----------------------------------------------------
        # Process candidates
        # ----------------------------------------------------

        for index, candidate in enumerate(
            candidates,
            start=1,
        ):

            print(
                "\n------------------------------------------------------------"
            )
            print(
                f"CANDIDATE {index}"
            )
            print(
                "------------------------------------------------------------"
            )

            title = candidate.get(
                "title",
                "<missing>",
            )

            article_ids = candidate.get(
                "article_ids",
                [],
            )

            score = candidate.get(
                "cluster_score",
                0,
            )

            print(
                f"Title: {title}"
            )

            print(
                f"Articles: {len(article_ids)}"
            )

            print(
                f"Cluster score: {float(score):.3f}"
            )

            # ------------------------------------------------
            # Validate again immediately before INSERT.
            # ------------------------------------------------

            errors = validate_candidate(
                candidate,
                existing_article_ids,
                existing_story_titles,
            )

            if errors:

                print(
                    "\nSTATUS: REJECTED"
                )

                for error in errors:

                    print(
                        f"  - {error}"
                    )

                rejected_candidates.append(index)

                continue

            # ------------------------------------------------
            # Create story
            # ------------------------------------------------

            story_id = insert_story(
                connection,
                candidate,
            )

            print(
                f"\nCreated story {story_id}."
            )

            # ------------------------------------------------
            # Create mappings
            # ------------------------------------------------

            similarity_score = float(
                candidate["cluster_score"]
            )

            insert_story_articles(
                connection,
                story_id,
                article_ids,
                similarity_score,
            )

            print(
                f"Added {len(article_ids)} articles "
                f"to story {story_id}."
            )

            created_stories.append(
                {
                    "story_id": story_id,
                    "title": title,
                    "article_ids": article_ids,
                }
            )

            # Prevent another candidate from using the
            # same articles during this execution.
            existing_article_ids.update(
                article_ids
            )

            existing_story_titles.add(
                title.strip().lower()
            )

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        connection.commit()

        print(
            "\nDatabase transaction committed."
        )

    except Exception:

        if connection is not None:

            connection.rollback()

        print(
            "\nERROR: Database operation failed."
        )

        print(
            "Transaction rolled back. "
            "No partial database changes were committed."
        )

        raise

    finally:

        if connection is not None:

            connection.close()

    # ========================================================
    # Summary
    # ========================================================

    print(
        "\n============================================================"
    )

    print(
        "CREATION SUMMARY"
    )

    print(
        "============================================================"
    )

    print(
        f"Candidates found: {len(candidates)}"
    )

    print(
        f"Stories created: {len(created_stories)}"
    )

    print(
        f"Candidates rejected: {len(rejected_candidates)}"
    )

    total_articles = sum(
        len(story["article_ids"])
        for story in created_stories
    )

    print(
        f"Article mappings created: {total_articles}"
    )

    print(
        "============================================================"
    )

    if created_stories:

        print("\nCreated stories:")

        for story in created_stories:

            print(
                f"  Story {story['story_id']}: "
                f"{story['title']}"
            )

            print(
                f"    Articles: "
                f"{story['article_ids']}"
            )

    print(
        "\nStage 7.13 complete."
    )


if __name__ == "__main__":
    main()