# This is just a hello world gradio app - not part of this project.
import gradio as gr

def greet(name):
    return f"Hello {name}! Welcome to NewsLens."

app = gr.Interface(
    fn=greet, 
    inputs=gr.Textbox(label="Your Name"), 
    outputs=gr.Textbox(label="Greeting Message"), 
    title="NewsLens",
    description="Understand the news, not just the headlines."
    )

app.launch()