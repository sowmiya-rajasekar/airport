"""
app.py
------
Flask backend for PlacementPrep AI chatbot.
Uses Google Gemini API (google-genai SDK) with a strict system prompt
defined in chatbot_config.py, so the bot only answers placement-prep related queries.
"""

import os
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types
from dotenv import load_dotenv

from chatbot_config import (
    CHATBOT_NAME,
    CHATBOT_TAGLINE,
    SYSTEM_PROMPT,
    GEMINI_MODEL,
    GENERATION_CONFIG,
)

# Load .env file (put your GEMINI_API_KEY here)
load_dotenv()

app = Flask(__name__)

# Get API key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY not found! Create a .env file with: GEMINI_API_KEY=your_key_here"
    )

# Initialize Gemini client (new google-genai SDK, works with AQ.-format keys too)
client = genai.Client(api_key=API_KEY)

# In-memory chat history store (simple, per-server session — resets on restart)
# For production, move this to a session/db, but for a demo/project this is fine.
chat_sessions = {}


def get_or_create_chat(session_id: str):
    """Return an existing Gemini chat session, or create a new one with the system prompt."""
    if session_id not in chat_sessions:
        chat_sessions[session_id] = client.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=GENERATION_CONFIG["temperature"],
                max_output_tokens=GENERATION_CONFIG["max_output_tokens"],
            ),
        )
    return chat_sessions[session_id]


@app.route("/")
def index():
    """Serve the chat UI, passing bot name/tagline so index.html can display it."""
    return render_template(
        "index.html", chatbot_name=CHATBOT_NAME, chatbot_tagline=CHATBOT_TAGLINE
    )


@app.route("/chat", methods=["POST"])
def chat():
    """Receive a user message, send it to Gemini with the system prompt, return the reply."""
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    session_id = data.get("session_id", "default")

    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    try:
        chat_session = get_or_create_chat(session_id)
        response = chat_session.send_message(user_message)
        bot_reply = response.text
        return jsonify({"reply": bot_reply})
    except Exception as e:
        # Keep the error message generic for the user, log the real one server-side
        print(f"[ERROR] Gemini API call failed: {e}")
        return jsonify(
            {"error": "Oops! Something went wrong while generating the response. Please try again."}
        ), 500


@app.route("/reset", methods=["POST"])
def reset():
    """Clear chat history for a session (used by the 'New Chat' button in UI)."""
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id", "default")
    chat_sessions.pop(session_id, None)
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
