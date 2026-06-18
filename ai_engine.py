import os
import pg8000.dbapi
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from user_manager import get_db_connection

load_dotenv()


def init_chat_db():
    """Ensures chat session, message tracking, and usage tracking tables exist on Neon Cloud."""
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT
            );
        """)
        # New table to accurately store token tracking histories permanently per user session
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                session_id TEXT PRIMARY KEY,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER
            );
        """)
        conn.commit()
    finally:
        conn.close()


init_chat_db()


class ChatBotEngine:
    """Handles scalable conversations, dashboard model mapping, and token computations."""

    def __init__(self, system_prompt="You are a helpful AI assistant."):
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        # Supported models dictionary map
        self.available_models = {
            "⚡Llama 3.1 (Fast)": "llama-3.1-8b-instant",
            "🚀Groq Compound (High Quality)": "groq/compound",
            "🧠OpenAI (Deep Logic)": "openai/gpt-oss-safeguard-20b",
        }
        today_str = datetime.now().strftime("%B %d, %Y")
        self.base_system_prompt = (
            f"{system_prompt}\nCurrent Real-world Date: {today_str}."
        )

    def create_new_session(self, session_id, user_id, default_title="New Chat"):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("SELECT id FROM sessions WHERE id = %s;", (session_id,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO sessions VALUES (%s, %s, %s, %s);",
                    (session_id, user_id, default_title, now),
                )
                cursor.execute(
                    "INSERT INTO token_usage VALUES (%s, 0, 0, 0);", (session_id,)
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

    def get_token_usage(self, session_id):
        """Fetches total aggregated cloud platform tracking integers."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT prompt_tokens, completion_tokens, total_tokens FROM token_usage WHERE session_id = %s;",
                (session_id,),
            )
            row = cursor.fetchone()
            if row:
                return {"prompt": row[0], "completion": row[1], "total": row[2]}
            return {"prompt": 0, "completion": 0, "total": 0}
        finally:
            conn.close()

    def update_token_usage(self, session_id, prompt_text, completion_text):
        """Computes approximate token tracking variables using lightweight statistical models."""
        # Simple fallback token estimation approximation metric (1 word ~ 1.3 tokens)
        p_tokens = int(len(prompt_text.split()) * 1.3) + 50  # 50 base for system setup
        c_tokens = int(len(completion_text.split()) * 1.3)
        t_tokens = p_tokens + c_tokens

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE token_usage 
                SET prompt_tokens = prompt_tokens + %s, 
                    completion_tokens = completion_tokens + %s, 
                    total_tokens = total_tokens + %s 
                WHERE session_id = %s;
            """,
                (p_tokens, c_tokens, t_tokens, session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_streaming_response(self, chat_history, selected_model_key):
        """Pipes real-time text arrays down using chosen user model configurations."""
        if not chat_history:
            return

        target_model = self.available_models.get(
            selected_model_key, "llama-3.1-8b-instant"
        )
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
            model=target_model, messages=compiled_messages, stream=True
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
            cursor.execute(
                "DELETE FROM token_usage WHERE session_id = %s;", (session_id,)
            )
            conn.commit()
        finally:
            conn.close()
