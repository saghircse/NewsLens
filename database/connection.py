import psycopg

from config.settings import DATABASE_URL


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Please add it to your .env file."
        )

    return psycopg.connect(DATABASE_URL)