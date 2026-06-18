import os
import pg8000.dbapi
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from user_manager import get_db_connection  # Reuse connection pipeline cleanly

load_dotenv()


def init_chat_db():
    """Ensures chat session and message tracking tables exist on Neon Cloud."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT,
                created_at TEXT
            );
        """)
        # Note: SERIAL is PostgreSQL's clean native version of SQLite's AUTOINCREMENT
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT
            );
        """)
        conn.commit()
    finally:
        conn.close()


# Initialize tables immediately upon module import
init_chat_db()


class ChatBotEngine:
    """Handles core conversational tasks, sidebar indexes, and model generations."""

    def __init__(self, system_prompt="You are a helpful AI assistant."):
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.model = "llama-3.3-7b-versatile"

        today_str = datetime.now().strftime("%B %d, %Y")
        self.base_system_prompt = (
            f"{system_prompt}\nCurrent Real-world Date: {today_str}."
        )

    def create_new_session(self, session_id, user_id, default_title="New Chat"):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Using basic upsert syntax alternative standard across SQL families
            cursor.execute("SELECT id FROM sessions WHERE id = %s;", (session_id,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO sessions VALUES (%s, %s, %s, %s);",
                    (session_id, user_id, default_title, now),
                )
                conn.commit()
        finally:
            conn.close()

    def update_session_title(self, session_id, new_title):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET title = %s WHERE id = %s;",
                (new_title[:30], session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_all_sessions(self, user_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title FROM sessions WHERE user_id = %s ORDER BY created_at DESC;",
                (user_id,),
            )
            return cursor.fetchall()
        finally:
            conn.close()

    def save_message(self, session_id, role, content):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (%s, %s, %s, %s);",
                (session_id, role, content, now),
            )
            conn.commit()
        finally:
            conn.close()

    def load_messages(self, session_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM messages WHERE session_id = %s ORDER BY id ASC;",
                (session_id,),
            )
            rows = cursor.fetchall()
            return [{"role": row[0], "content": row[1]} for row in rows]
        finally:
            conn.close()

    def get_streaming_response(self, chat_history):
        if not chat_history:
            return

        max_memory_window = 6
        recent_history = (
            chat_history[-max_memory_window:]
            if len(chat_history) > max_memory_window
            else chat_history
        )

        compiled_messages = [{"role": "system", "content": self.base_system_prompt}]
        for msg in recent_history:
            compiled_messages.append({"role": msg["role"], "content": msg["content"]})

        completion = self.client.chat.completions.create(
            model=self.model, messages=compiled_messages, stream=True
        )
        for chunk in completion:
            if chunk.choices and len(chunk.choices) > 0:
                content = chunk.choices[0].delta.content
                if content:
                    yield content

    def delete_session(self, session_id):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = %s;", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE id = %s;", (session_id,))
            conn.commit()
        finally:
            conn.close()
