import argparse
import subprocess
import sys


STAGES = [
    (
        "Existing Story Matching",
        "scripts.update_existing_stories",
    ),
    (
        "New Story Discovery",
        "scripts.create_new_stories",
    ),
]


def run_stage(name, module, dry_run):

    print()
    print("=" * 70)
    print(f"STAGE: {name}")
    print("=" * 70)

    command = [
        sys.executable,
        "-m",
        module,
    ]

    if dry_run:
        command.append("--dry-run")

    print()
    print(
        "Running:",
        " ".join(command),
    )

    result = subprocess.run(
        command,
        check=False,
    )

    print()

    if result.returncode != 0:

        print(
            f"Stage failed: {name} "
            f"(exit code {result.returncode})"
        )

        return False

    print(
        f"Stage completed successfully: {name}"
    )

    return True


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Run the NewsLens story-processing "
            "pipeline."
        )
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Run all story-processing stages "
            "without database changes."
        ),
    )

    args = parser.parse_args()

    print()
    print("=" * 70)
    print("NEWSLENS — STORY PIPELINE")
    print("=" * 70)

    print()
    if args.dry_run:
        print("Mode: DRY RUN")
    else:
        print("Mode: LIVE")

    for name, module in STAGES:

        success = run_stage(
            name,
            module,
            args.dry_run,
        )

        if not success:

            print()
            print("=" * 70)
            print("PIPELINE STOPPED")
            print("=" * 70)

            sys.exit(1)

    print()
    print("=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)

    if args.dry_run:

        print()
        print(
            "Dry run complete. "
            "No database changes were made."
        )


if __name__ == "__main__":
    main()