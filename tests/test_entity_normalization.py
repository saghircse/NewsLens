from nlp.entity_normalization import (
    normalize_entity_text,
    canonicalize_entity,
)


def test_normalization():

    tests = [
        ("Donald Trump", "donald trump"),
        ("donald trump", "donald trump"),
        ("Trump's", "trump"),
        ("Trump’s", "trump"),
        ("  Donald   Trump  ", "donald trump"),
        ("U.S.", "united states"),
        ("U.S", "united states"),
        ("US", "united states"),
        ("U.K.", "united kingdom"),
        ("UK", "united kingdom"),
    ]

    for original, expected in tests:

        result = canonicalize_entity(original)

        print(
            f"{original!r} -> {result!r}"
        )

        assert result == expected


def test_conservative_normalization():

    # We intentionally do NOT map demonyms
    # to countries yet.

    tests = [
        ("American", "american"),
        ("Americans", "americans"),
        ("Canadian", "canadian"),
        ("Canadians", "canadians"),
        ("British", "british"),
    ]

    for original, expected in tests:

        result = canonicalize_entity(original)

        print(
            f"{original!r} -> {result!r}"
        )

        assert result == expected


def main():

    print("\n========== ENTITY NORMALIZATION TEST ==========\n")

    test_normalization()

    print("\nBasic normalization: PASS")

    test_conservative_normalization()

    print("Conservative normalization: PASS")

    print("\n===============================================\n")


if __name__ == "__main__":
    main()