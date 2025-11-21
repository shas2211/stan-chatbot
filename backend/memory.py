# backend/memory.py
import time
from db import get_conn
from groq_client import generate_response

def get_memory(user_id):
    conn = get_conn()
    r = conn.execute("SELECT memory_text FROM user_memory WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return r["memory_text"] if r else ""

def save_memory(user_id, new_memory_text):
    now = int(time.time())
    conn = get_conn()
    conn.execute("""
        INSERT INTO user_memory (user_id, memory_text, last_updated)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET memory_text=excluded.memory_text, last_updated=excluded.last_updated
    """, (user_id, new_memory_text, now))
    conn.commit()
    conn.close()

def append_event_to_memory(user_id, event_text):
    """
    Add a new 'event' to memory, then compress/summarize into shorter memory.
    Uses Groq to summarize incremental memory.
    """
    current = get_memory(user_id) or ""
    combined = (current + "\n" + event_text).strip()
    # Prompt Groq to create a concise, factual summary of the memory suitable for reuse
    prompt = (
        "You are an assistant that extracts and summarizes personal facts and preferences "
        "for long-term memory storage. Convert the following user-provided text into "
        "a short, factual bulleted memory string (1-6 bullets). Avoid speculation. "
        "If nothing factual to store, reply with 'NO_MEMORY'.\n\n"
        f"INPUT:\n{event_text}\n\nCURRENT_MEMORY:\n{current}\n\nOUTPUT:"
    )
    summary = generate_response(prompt, temperature=0.0, max_tokens=300).strip()
    if summary.upper() == "NO_MEMORY":
        return False
    # Combine: prefer the new summary if it is concise. Store it.
    save_memory(user_id, summary)
    return True
