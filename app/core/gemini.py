# app/core/gemini.py
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

# The new SDK automatically picks up the GEMINI_API_KEY from your .env file
client = genai.Client()

def get_client():
    return client