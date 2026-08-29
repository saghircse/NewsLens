import spacy.cli


MODEL = "en_core_web_sm"


def main():
    try:
        import spacy

        spacy.load(MODEL)

        print(f"{MODEL} is already installed.")

    except OSError:

        print(f"{MODEL} not found.")
        print(f"Downloading {MODEL}...")

        spacy.cli.download(MODEL)

        print("Download complete.")


if __name__ == "__main__":
    main()