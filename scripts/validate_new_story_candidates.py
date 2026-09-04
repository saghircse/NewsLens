import json
from collections import defaultdict
from pathlib import Path

from database.connection import get_connection


# ============================================================
# Configuration
# ============================================================

CANDIDATE_FILE = Path("candidate_new_stories.json")

MIN_ARTICLES_PER_STORY = 2
MIN_CLUSTER_SCORE = 0.60

# If two candidates share this percentage of their articles,
# consider them overlapping candidates.
MAX_CANDIDATE_OVERLAP = 0.50


# ============================================================
# Database helpers
# ============================================================

def get_article_ids():

    query = """
        SELECT id
        FROM articles
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

    return {
        row[0]
        for row in rows
    }


def get_matched_article_ids():

    query = """
        SELECT DISTINCT article_id
        FROM story_articles
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

    return {
        row[0]
        for row in rows
    }


# ============================================================
# Candidate file
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
# Validation
# ============================================================

def validate_candidate(
    candidate,
    all_article_ids,
    matched_article_ids,
):

    errors = []
    warnings = []

    article_ids = candidate.get(
        "article_ids",
        [],
    )

    title = candidate.get(
        "title",
        "",
    )

    article_count = candidate.get(
        "article_count",
        len(article_ids),
    )

    cluster_score = candidate.get(
        "cluster_score",
        0,
    )

    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    if not isinstance(article_ids, list):

        errors.append(
            "article_ids is not a list"
        )

        article_ids = []

    if not title:

        errors.append(
            "missing proposed title"
        )

    if len(article_ids) < MIN_ARTICLES_PER_STORY:

        errors.append(
            f"fewer than {MIN_ARTICLES_PER_STORY} articles"
        )

    if article_count != len(article_ids):

        warnings.append(
            "article_count does not match article_ids length"
        )

    # --------------------------------------------------------
    # Duplicate article IDs inside candidate
    # --------------------------------------------------------

    if len(article_ids) != len(set(article_ids)):

        errors.append(
            "duplicate article IDs inside candidate"
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

        cluster_score = 0

    if cluster_score < MIN_CLUSTER_SCORE:

        errors.append(
            f"cluster score {cluster_score:.3f} "
            f"is below minimum {MIN_CLUSTER_SCORE:.3f}"
        )

    # --------------------------------------------------------
    # Article existence
    # --------------------------------------------------------

    missing_articles = [
        article_id
        for article_id in article_ids
        if article_id not in all_article_ids
    ]

    if missing_articles:

        errors.append(
            f"article IDs do not exist: "
            f"{missing_articles}"
        )

    # --------------------------------------------------------
    # Existing story membership
    # --------------------------------------------------------

    already_matched = [
        article_id
        for article_id in article_ids
        if article_id in matched_article_ids
    ]

    if already_matched:

        errors.append(
            f"articles already assigned to stories: "
            f"{already_matched}"
        )

    return errors, warnings


# ============================================================
# Candidate overlap
# ============================================================

def calculate_overlap(
    candidate_a,
    candidate_b,
):

    articles_a = set(
        candidate_a.get(
            "article_ids",
            [],
        )
    )

    articles_b = set(
        candidate_b.get(
            "article_ids",
            [],
        )
    )

    if not articles_a or not articles_b:

        return 0.0

    intersection = articles_a.intersection(
        articles_b
    )

    smaller_candidate = min(
        len(articles_a),
        len(articles_b),
    )

    return len(intersection) / smaller_candidate


# ============================================================
# Reporting
# ============================================================

def print_candidate_result(
    number,
    candidate,
    errors,
    warnings,
):

    print(
        "\n------------------------------------------------------------"
    )

    print(
        f"CANDIDATE {number}"
    )

    print(
        "------------------------------------------------------------"
    )

    print(
        f"Title: {candidate.get('title', '<missing>')}"
    )

    print(
        f"Articles: {candidate.get('article_count', 0)}"
    )

    print(
        f"Cluster score: "
        f"{candidate.get('cluster_score', 0):.3f}"
    )

    print(
        f"Article IDs: "
        f"{candidate.get('article_ids', [])}"
    )

    if errors:

        print(
            "\nSTATUS: REJECT"
        )

        print(
            "\nErrors:"
        )

        for error in errors:

            print(
                f"  - {error}"
            )

    elif warnings:

        print(
            "\nSTATUS: VALID WITH WARNINGS"
        )

        print(
            "\nWarnings:"
        )

        for warning in warnings:

            print(
                f"  - {warning}"
            )

    else:

        print(
            "\nSTATUS: VALID"
        )


def print_overlap_warnings(
    candidates,
):

    print(
        "\n============================================================"
    )

    print(
        "CANDIDATE OVERLAP CHECK"
    )

    print(
        "============================================================"
    )

    found_overlap = False

    for i in range(len(candidates)):

        for j in range(i + 1, len(candidates)):

            overlap = calculate_overlap(
                candidates[i],
                candidates[j],
            )

            if overlap >= MAX_CANDIDATE_OVERLAP:

                found_overlap = True

                print(
                    f"\nWARNING: Candidate {i + 1} and "
                    f"Candidate {j + 1} overlap "
                    f"{overlap:.1%}."
                )

    if not found_overlap:

        print(
            "\nNo significant candidate overlap detected."
        )


# ============================================================
# Main
# ============================================================

def main():

    print(
        "Loading candidate_new_stories.json..."
    )

    candidates = load_candidates()

    print(
        f"Loaded {len(candidates)} candidates."
    )

    if not candidates:

        print(
            "\nNo candidates to validate."
        )

        return

    print(
        "\nLoading article IDs..."
    )

    all_article_ids = get_article_ids()

    print(
        f"Found {len(all_article_ids)} articles in database."
    )

    print(
        "\nLoading story/article mappings..."
    )

    matched_article_ids = get_matched_article_ids()

    print(
        f"Found {len(matched_article_ids)} articles "
        f"already assigned to stories."
    )

    print(
        "\n============================================================"
    )

    print(
        "NEW STORY CANDIDATE VALIDATION"
    )

    print(
        "============================================================"
    )

    valid_count = 0
    warning_count = 0
    rejected_count = 0

    for number, candidate in enumerate(
        candidates,
        start=1,
    ):

        errors, warnings = validate_candidate(
            candidate,
            all_article_ids,
            matched_article_ids,
        )

        print_candidate_result(
            number,
            candidate,
            errors,
            warnings,
        )

        if errors:

            rejected_count += 1

        elif warnings:

            warning_count += 1
            valid_count += 1

        else:

            valid_count += 1

    print_overlap_warnings(
        candidates
    )

    print(
        "\n============================================================"
    )

    print(
        "VALIDATION SUMMARY"
    )

    print(
        "============================================================"
    )

    print(
        f"Candidates found: {len(candidates)}"
    )

    print(
        f"Valid: {valid_count}"
    )

    print(
        f"Valid with warnings: {warning_count}"
    )

    print(
        f"Rejected: {rejected_count}"
    )

    print(
        "============================================================"
    )

    print(
        "\nValidation complete."
    )

    print(
        "No database changes were made."
    )


if __name__ == "__main__":
    main()