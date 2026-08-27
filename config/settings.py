import os

from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
LLM_API_KEY = os.getenv("LLM_API_KEY")