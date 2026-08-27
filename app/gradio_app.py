import gradio as gr

from database.repository import get_latest_articles


def load_articles():
    articles = get_latest_articles(limit=10)

    if not articles:
        return "No articles found."

    output = []

    for article in articles:
        article_id, title, url, published_at, source_name = article

        output.append(
            f"### {title}\n"
            f"**Source:** {source_name}\n\n"
            f"**Published:** {published_at}\n\n"
            f"[Read original article]({url})"
        )

    return "\n\n---\n\n".join(output)


def create_app():
    with gr.Blocks(title="NewsLens") as app:

        gr.Markdown(
            """
            # NewsLens

            ### Understand the news, not just the headlines.
            """
        )

        refresh_button = gr.Button("Load latest articles")

        articles_output = gr.Markdown()

        refresh_button.click(
            fn=load_articles,
            inputs=[],
            outputs=articles_output,
        )

    return app