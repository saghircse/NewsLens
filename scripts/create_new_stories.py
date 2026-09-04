import argparse
import json
from collections import defaultdict
from itertools import combinations

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from database.connection import get_connection
from nlp.entities import extract_normalized_entities


# ============================================================
# Configuration
# ============================================================

MIN_ARTICLES_PER_STORY = 2

# Used to build the initial candidate graph.
PAIR_SIMILARITY_THRESHOLD = 0.55

# Minimum relationship score required for an article to be
# considered part of the core event.
CORE_SIMILARITY_THRESHOLD = 0.62

# An article must have a sufficiently strong relationship with
# this fraction of the other articles in its candidate cluster.
MIN_CORE_NEIGHBOR_RATIO = 0.50

# Additional evidence from shared entities.
ENTITY_BONUS = 0.10

MAX_CANDIDATES = 20


# ============================================================
# Database
# ============================================================

def get_unmatched_articles():
    """
    Get articles that are not currently mapped to a story.

    The article-to-story relationship is stored in story_articles.
    articles does NOT contain story_id.
    """

    query = """
        SELECT
            a.id,
            a.title,
            a.description,
            a.published_at,
            a.embedding
        FROM articles a
        LEFT JOIN story_articles sa
            ON a.id = sa.article_id
        WHERE sa.article_id IS NULL
        ORDER BY a.published_at NULLS LAST, a.id
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

    articles = []

    for row in rows:
        articles.append({
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "published_at": row[3],
            "embedding": row[4],
        })

    return articles


# ============================================================
# Embeddings
# ============================================================

def parse_embedding(value):
    """
    Convert a PostgreSQL pgvector value into a numpy array.

    Handles values such as:

        '[0.1,0.2,0.3]'

    """

    if value is None:
        return None

    if isinstance(value, np.ndarray):
        return value.astype(float)

    if isinstance(value, (list, tuple)):
        return np.array(value, dtype=float)

    if isinstance(value, str):
        value = value.strip()

        if value.startswith("[") and value.endswith("]"):
            value = value[1:-1]

        if not value:
            return None

        return np.array(
            [float(x) for x in value.split(",")],
            dtype=float,
        )

    raise ValueError(
        f"Unsupported embedding type: {type(value)}"
    )


def calculate_similarity_matrix(articles):
    """
    Calculate cosine similarity between article embeddings.
    """

    valid_articles = []
    vectors = []

    for article in articles:

        embedding = parse_embedding(
            article.get("embedding")
        )

        if embedding is None:
            continue

        valid_articles.append(article)
        vectors.append(embedding)

    if not vectors:
        return valid_articles, np.empty((0, 0))

    vectors = np.array(vectors, dtype=float)

    similarity_matrix = cosine_similarity(vectors)

    return valid_articles, similarity_matrix


# ============================================================
# Entity extraction
# ============================================================

def get_article_text(article):
    title = article.get("title") or ""
    description = article.get("description") or ""

    return f"{title}. {description}".strip()


def extract_article_entities(articles):
    """
    Extract normalized entities from article title/description.
    """

    for article in articles:

        text = get_article_text(article)

        try:
            article["entities"] = extract_normalized_entities(
                text
            )
        except Exception as exc:

            print(
                f"Warning: entity extraction failed "
                f"for article {article['id']}: {exc}"
            )

            article["entities"] = set()


def entity_overlap(article_a, article_b):
    """
    Jaccard similarity between the normalized entity sets.
    """

    entities_a = article_a.get("entities", set())
    entities_b = article_b.get("entities", set())

    if not entities_a or not entities_b:
        return 0.0

    intersection = entities_a.intersection(entities_b)
    union = entities_a.union(entities_b)

    if not union:
        return 0.0

    return len(intersection) / len(union)


# ============================================================
# Relationship scoring
# ============================================================

def relationship_score(
    article_a,
    article_b,
    semantic_score,
):
    """
    Combine semantic similarity with entity overlap.

    This is still a deterministic MVP score.
    """

    overlap = entity_overlap(
        article_a,
        article_b,
    )

    score = semantic_score

    if overlap > 0:
        score += ENTITY_BONUS * overlap

    return min(score, 1.0)


# ============================================================
# Candidate graph
# ============================================================

def build_candidate_graph(
    articles,
    similarity_matrix,
):
    """
    Build an article relationship graph.

    An edge means that two articles are sufficiently related
    to be considered part of the same candidate event.
    """

    graph = defaultdict(set)

    for i, j in combinations(
        range(len(articles)),
        2,
    ):

        semantic_score = float(
            similarity_matrix[i][j]
        )

        score = relationship_score(
            articles[i],
            articles[j],
            semantic_score,
        )

        if score >= PAIR_SIMILARITY_THRESHOLD:

            article_a_id = articles[i]["id"]
            article_b_id = articles[j]["id"]

            graph[article_a_id].add(
                article_b_id
            )

            graph[article_b_id].add(
                article_a_id
            )

    return graph


# ============================================================
# Connected components
# ============================================================

def find_connected_components(
    articles,
    graph,
):
    """
    Find connected components in the candidate graph.

    These are only provisional clusters.
    They are NOT final stories.
    """

    article_ids = {
        article["id"]
        for article in articles
    }

    visited = set()
    components = []

    for article_id in article_ids:

        if article_id in visited:
            continue

        stack = [article_id]
        component = []

        while stack:

            current = stack.pop()

            if current in visited:
                continue

            visited.add(current)
            component.append(current)

            for neighbor in graph.get(
                current,
                set(),
            ):

                if neighbor not in visited:
                    stack.append(neighbor)

        if len(component) >= MIN_ARTICLES_PER_STORY:
            components.append(component)

    return components


# ============================================================
# Core-event filtering
# ============================================================

def calculate_article_core_score(
    article,
    cluster_articles,
    similarity_matrix,
    article_index,
):
    """
    Calculate how strongly an article relates to the other
    articles in the provisional cluster.

    We use the average relationship score rather than merely
    checking whether one connection exists.
    """

    scores = []

    article_id = article["id"]
    index_a = article_index[article_id]

    for other in cluster_articles:

        if other["id"] == article_id:
            continue

        index_b = article_index[other["id"]]

        semantic_score = float(
            similarity_matrix[index_a][index_b]
        )

        score = relationship_score(
            article,
            other,
            semantic_score,
        )

        scores.append(score)

    if not scores:
        return 0.0

    return float(np.mean(scores))


def filter_cluster_to_core_event(
    cluster_articles,
    similarity_matrix,
    article_index,
):
    """
    Keep only articles that have strong enough relationships
    with the core of the candidate event.

    This prevents transitive relationships such as:

        A -> B -> C -> D

    from automatically making A/B/C/D one story.
    """

    if len(cluster_articles) <= 2:
        return cluster_articles

    article_scores = []

    for article in cluster_articles:

        score = calculate_article_core_score(
            article,
            cluster_articles,
            similarity_matrix,
            article_index,
        )

        article_scores.append(
            (article, score)
        )

    # Find the strongest article as the provisional core.
    article_scores.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    core_article = article_scores[0][0]

    core_index = article_index[
        core_article["id"]
    ]

    core_members = []

    for article in cluster_articles:

        if article["id"] == core_article["id"]:
            core_members.append(article)
            continue

        article_index_value = article_index[
            article["id"]
        ]

        semantic_score = float(
            similarity_matrix[
                core_index
            ][
                article_index_value
            ]
        )

        score = relationship_score(
            core_article,
            article,
            semantic_score,
        )

        if score >= CORE_SIMILARITY_THRESHOLD:
            core_members.append(article)

    return core_members


# ============================================================
# Cluster score
# ============================================================

def calculate_cluster_score(
    cluster_articles,
    similarity_matrix,
    article_index,
):
    """
    Calculate average pairwise relationship score for the
    final candidate cluster.
    """

    if len(cluster_articles) < 2:
        return 0.0

    scores = []

    for article_a, article_b in combinations(
        cluster_articles,
        2,
    ):

        index_a = article_index[
            article_a["id"]
        ]

        index_b = article_index[
            article_b["id"]
        ]

        semantic_score = float(
            similarity_matrix[index_a][index_b]
        )

        score = relationship_score(
            article_a,
            article_b,
            semantic_score,
        )

        scores.append(score)

    if not scores:
        return 0.0

    return float(np.mean(scores))


# ============================================================
# Title
# ============================================================

def select_proposed_title(
    cluster_articles,
):
    """
    Use an existing source headline as the proposed story title.

    We intentionally do not use an LLM for title generation yet.
    """

    if not cluster_articles:
        return "Untitled story"

    # Prefer the longest headline because it generally contains
    # more event-specific information.
    sorted_articles = sorted(
        cluster_articles,
        key=lambda article: len(
            article.get("title") or ""
        ),
        reverse=True,
    )

    return sorted_articles[0]["title"]


# ============================================================
# Candidate generation
# ============================================================

def generate_candidates(articles):

    if not articles:
        return []

    print(
        "\nParsing article embeddings and extracting entities..."
    )

    extract_article_entities(
        articles
    )

    print(
        f"Articles available for discovery: {len(articles)}"
    )

    print(
        "\nCalculating unmatched article similarity..."
    )

    articles, similarity_matrix = (
        calculate_similarity_matrix(
            articles
        )
    )

    if not articles:
        return []

    article_index = {
        article["id"]: index
        for index, article in enumerate(
            articles
        )
    }

    graph = build_candidate_graph(
        articles,
        similarity_matrix,
    )

    components = find_connected_components(
        articles,
        graph,
    )

    print(
        f"Generated {len(components)} candidate clusters."
    )

    articles_by_id = {
        article["id"]: article
        for article in articles
    }

    candidates = []

    for component in components:

        cluster_articles = [
            articles_by_id[article_id]
            for article_id in component
        ]

        cluster_articles.sort(
            key=lambda article: article["id"]
        )

        # IMPORTANT:
        # Connected components are only provisional.
        # Now isolate the actual core event.
        core_articles = filter_cluster_to_core_event(
            cluster_articles,
            similarity_matrix,
            article_index,
        )

        if len(core_articles) < MIN_ARTICLES_PER_STORY:
            continue

        score = calculate_cluster_score(
            core_articles,
            similarity_matrix,
            article_index,
        )

        if score < PAIR_SIMILARITY_THRESHOLD:
            continue

        candidates.append({
            "title": select_proposed_title(
                core_articles
            ),
            "article_ids": [
                article["id"]
                for article in core_articles
            ],
            "article_titles": [
                article["title"]
                for article in core_articles
            ],
            "article_count": len(
                core_articles
            ),
            "cluster_score": round(
                score,
                3,
            ),
        })

    candidates.sort(
        key=lambda candidate: (
            candidate["cluster_score"],
            candidate["article_count"],
        ),
        reverse=True,
    )

    return candidates[:MAX_CANDIDATES]


# ============================================================
# Output
# ============================================================

def print_candidates(candidates):

    print(
        "\n============================================================"
    )

    print(
        "NEW STORY DISCOVERY — DRY RUN"
    )

    print(
        "============================================================"
    )

    if not candidates:

        print(
            "\nNo sufficiently strong new story candidates found."
        )

        print(
            "\n============================================================"
        )

        print(
            "Potential new stories: 0"
        )

        print(
            "============================================================"
        )

        return

    for number, candidate in enumerate(
        candidates,
        start=1,
    ):

        print(
            f"\nNEW STORY {number}"
        )

        print(
            f"Articles: {candidate['article_count']}"
        )

        print(
            f"Cluster score: "
            f"{candidate['cluster_score']:.3f}"
        )

        print(
            f"Proposed title: "
            f"{candidate['title']}"
        )

        print()

        for article_id, title in zip(
            candidate["article_ids"],
            candidate["article_titles"],
        ):

            print(
                f"  {article_id}: {title}"
            )

    print(
        "\n============================================================"
    )

    print(
        f"Potential new stories: {len(candidates)}"
    )

    print(
        "============================================================"
    )


def save_candidates(candidates):

    output = {
        "candidate_count": len(candidates),
        "candidates": candidates,
    }

    with open(
        "candidate_new_stories.json",
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(
        "Saved candidates to candidate_new_stories.json"
    )


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Discover potential new NewsLens stories "
            "from unmatched articles."
        )
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Show discovered stories without "
            "changing the database."
        ),
    )

    args = parser.parse_args()

    print(
        "Loading unmatched articles..."
    )

    articles = get_unmatched_articles()

    print(
        f"Found {len(articles)} unmatched articles."
    )

    candidates = generate_candidates(
        articles
    )

    print_candidates(
        candidates
    )

    save_candidates(
        candidates
    )

    if args.dry_run:

        print(
            "\nDry run complete. No database changes made."
        )

        return

    print(
        "\nActual story creation is not implemented yet."
    )

    print(
        "Run with --dry-run while validating discovery."
    )


if __name__ == "__main__":
    main()