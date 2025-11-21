# backend/app.py
import time
from flask import Flask, request, render_template, redirect, url_for
from dotenv import load_dotenv
from db import init_db, get_conn
from groq_client import generate_response
from memory import get_memory, append_event_to_memory

load_dotenv()
init_db()

app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")

USER_ID = "user1"   # simple single-user demo; extendable to auth-based users

# helper: fetch last N messages (user+bot) for context (descending order)
def fetch_recent_chat(user_id, limit=10):
    conn = get_conn()
    rows = conn.execute("""
        SELECT role, text, created_at FROM chats
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    # reverse to chronological
    return list(reversed(rows))

def save_chat(user_id, role, text):
    conn = get_conn()
    conn.execute("INSERT INTO chats (user_id, role, text, created_at) VALUES (?, ?, ?, ?)",
                 (user_id, role, text, int(time.time())))
    conn.commit()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def chat():
    user_id = USER_ID
    if request.method == "POST":
        user_text = request.form.get("msg", "").strip()
        if user_text:
            # store user message
            save_chat(user_id, "user", user_text)

            # 1) Detect tone/emotion quickly using LLM
            tone_prompt = (
                "You are a compact emotion-classifier. Read the user message and return a single-word "
                "emotion label and a short instruction for tone adaptation (1 sentence). "
                "Possible emotions: neutral, happy, sad, angry, anxious, excited. "
                "Format exactly: EMOTION || adaptation\n\nMessage:\n" + user_text
            )
            tone_out = generate_response(tone_prompt, temperature=0.0, max_tokens=30).strip()
            # guard parsing
            if "||" in tone_out:
                emotion, adaptation = [s.strip() for s in tone_out.split("||", 1)]
            else:
                emotion = "neutral"
                adaptation = "Respond naturally and warmly."

            # 2) Build the main system prompt (memory + recent history + adapt tone)
            memory_text = get_memory(user_id) or "No long-term memory."
            recent = fetch_recent_chat(user_id, limit=12)
            hist_str = "\n".join([f"{r['role'].upper()}: {r['text']}" for r in recent])

            sys_prompt = f"""
You are NOVA — an empathetic, human-like conversational companion for users.
Rules:
- NEVER claim to be more than a conversational agent that cares (do not invent real-world sensory experiences).
- Be empathetic and adapt to the user's emotional state using the adaptation instruction.
- Use the memory section to personalize replies and to recall past facts.
- If the user asks for unverifiable facts about themselves, either ask clarifying q or be playfully vague.

ADAPTATION: {adaptation}  (detected emotion: {emotion})
LONG_TERM_MEMORY:
{memory_text}

RECENT_CHAT:
{hist_str}

Now produce a natural, human reply to the user's latest message:
User: {user_text}

Also, if the user provided factual personal details that should be remembered (name, location, birthdays, likes/dislikes, major projects), extract briefly at the end under the heading MEM_TO_STORE: with concise lines like 'name: X' or 'likes: Y' or 'NO_MEMORY' if nothing to store.
"""
            assistant_out = generate_response(sys_prompt, temperature=0.85, max_tokens=500).strip()

            # The assistant_out is expected to be reply + a MEM_TO_STORE section.
            # Split: look for "\nMEM_TO_STORE:" marker
            if "\nMEM_TO_STORE:" in assistant_out:
                reply_text, mem_block = assistant_out.split("\nMEM_TO_STORE:", 1)
                mem_block = mem_block.strip()
            else:
                reply_text = assistant_out
                mem_block = "NO_MEMORY"

            # Save bot reply
            save_chat(user_id, "bot", reply_text.strip())

            # If mem_block has facts, call append_event_to_memory to compress and store
            if mem_block and mem_block.upper() != "NO_MEMORY":
                append_event_to_memory(user_id, mem_block)

        return redirect(url_for("chat"))

    # GET: render page with history
    rows = fetch_recent_chat(USER_ID, limit=50)
    # transform rows into list-of-dicts for Jinja
    chat_rows = [{"role": r["role"], "text": r["text"], "created_at": r["created_at"]} for r in rows]
    return render_template("chat.html", chat=chat_rows, memory=get_memory(USER_ID))

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
