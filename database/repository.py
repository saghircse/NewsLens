from database.connection import get_connection


def get_latest_articles(limit=10):
    query = """
        select
            articles.id,
            articles.title,
            articles.url,
            articles.published_at,
            sources.name as source_name
        from articles
        left join sources
            on articles.source_id = sources.id
        order by articles.published_at desc
        limit %s;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (limit,))
            return cursor.fetchall()

def article_exists(url):
    query = """
        select exists(
            select 1
            from articles
            where url = %s
        );
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (url,))
            return cursor.fetchone()[0]        

def get_active_sources():
    query = """
        select
            id,
            name,
            feed_url
        from sources
        where active = true
          and feed_url is not null
        order by name;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()   


def insert_article(
    source_id,
    title,
    url,
    description=None,
    author=None,
    published_at=None,
):
    query = """
        insert into articles (
            source_id,
            title,
            url,
            description,
            author,
            published_at
        )
        values (%s, %s, %s, %s, %s, %s)
        on conflict (url) do nothing
        returning id;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    source_id,
                    title,
                    url,
                    description,
                    author,
                    published_at,
                ),
            )

            result = cursor.fetchone()

        connection.commit()

    return result[0] if result else None           


def get_articles_for_clustering(limit=100):
    query = """
        select
            id,
            title,
            description,
            source_id,
            published_at
        from articles
        order by published_at desc nulls last
        limit %s;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (limit,))
            return cursor.fetchall()


def create_story(
    title,
    category=None,
    first_seen_at=None,
    last_updated_at=None,
):
    query = """
        insert into stories (
            title,
            category,
            first_seen_at,
            last_updated_at
        )
        values (%s, %s, %s, %s)
        returning id;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                query,
                (
                    title,
                    category,
                    first_seen_at,
                    last_updated_at,
                ),
            )

            story_id = cursor.fetchone()[0]

        connection.commit()

    return story_id        

def link_article_to_story(
    story_id,
    article_id,
    similarity_score=None,
):
    query = """
        insert into story_articles (
            story_id,
            article_id,
            similarity_score
        )
        values (%s, %s, %s)
        on conflict (story_id, article_id)
        do nothing;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                query,
                (
                    story_id,
                    article_id,
                    similarity_score,
                ),
            )

        connection.commit()

def update_article_embedding(article_id, embedding):
    query = """
        update articles
        set embedding = %s
        where id = %s;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (embedding.tolist(), article_id),
            )

        connection.commit()

def get_articles_with_embeddings(limit=100):
    query = """
        select
            id,
            title,
            description,
            source_id,
            published_at,
            embedding
        from articles
        where embedding is not null
        order by published_at desc nulls last
        limit %s;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (limit,))
            return cursor.fetchall()        

def update_story_embedding(
    story_id,
    embedding,
):

    query = """
        update stories
        set embedding = %s
        where id = %s;
    """

    with get_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                query,
                (
                    embedding.tolist(),
                    story_id,
                ),
            )

        connection.commit()