import gradio as gr


def greet(name):
    return f"Hello {name}! Welcome to NewsLens."


def create_app():
    return gr.Interface(
        fn=greet,
        inputs=gr.Textbox(label="Your name"),
        outputs=gr.Textbox(label="Message"),
        title="NewsLens",
        description="Understand the news, not just the headlines.",
    )