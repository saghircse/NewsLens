from database.connection import get_connection


def main():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("select 1;")
            result = cursor.fetchone()

    print("Database connection successful!")
    print("Result:", result)


if __name__ == "__main__":
    main()