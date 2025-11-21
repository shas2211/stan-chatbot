# backend/db.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "stan_chat.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # store per-user memory (long term)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_memory (
        user_id TEXT PRIMARY KEY,
        memory_text TEXT,
        last_updated INTEGER
    )
    """)

    # conversation history (append-only, for session-level context)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        role TEXT,             -- 'user' or 'bot'
        text TEXT,
        created_at INTEGER
    )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
