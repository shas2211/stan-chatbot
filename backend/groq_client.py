# backend/groq_client.py
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("GROQ_API_KEY env var not set. Add it in Render dashboard or as an OS env var.")

client = Groq(api_key=API_KEY)

def generate_response(prompt, model="llama-3.3-70b-versatile", temperature=0.8, max_tokens=800):
    """
    Returns assistant content (string).
    """
    res = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens
    )

    # Correct new Groq SDK access
    return res.choices[0].message.content
