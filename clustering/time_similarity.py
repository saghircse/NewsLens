from datetime import datetime


def calculate_time_similarity(
    published_a,
    published_b,
    max_hours=48,
):

    if published_a is None or published_b is None:
        return 0.0

    difference = abs(
        published_a - published_b
    )

    hours = (
        difference.total_seconds()
        / 3600
    )

    if hours >= max_hours:
        return 0.0

    return 1.0 - (
        hours / max_hours
    )