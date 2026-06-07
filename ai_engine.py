import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient

load_dotenv()


class ChatBotEngine:

    def __init__(self, system_prompt="You are a helpful AI assistant."):
        """Initializes clients, paths, and sets up the persistent local database."""
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        # self.model = "llama-3.1-8b-instant"
        # self.model = "groq/compound"
        self.model = "openai/gpt-oss-safeguard-20b"

        tavily_key = os.environ.get("TAVILY_API_KEY")
        self.search_client = TavilyClient(api_key=tavily_key) if tavily_key else None

        today_str = datetime.now().strftime("%B %d, %Y")
        self.base_system_prompt = (
            f"{system_prompt}\n"
            f"Current Real-world Date: {today_str}.\n"
            "You have access to live web search data when relevant."
        )

        # Initialize SQLite database file
        self.db_path = "chatbot_memory.db"
        self._init_db()

    def _init_db(self):
        """Creates database storage tables if they don't exist yet."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Table to store unique session windows
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT
                )
            """)
            # Table to store independent chat messages linked to a session ID
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT
                )
            """)
            conn.commit()

    def create_new_session(self, session_id, default_title="New Chat"):
        """Saves a brand new conversation channel node."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT OR IGNORE INTO sessions VALUES (?, ?, ?)",
                (session_id, default_title, now),
            )
            conn.commit()

    def update_session_title(self, session_id, new_title):
        """Updates the visible title string in the sidebar menu."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET title = ? WHERE id = ?",
                (new_title[:30], session_id),
            )
            conn.commit()

    def get_all_sessions(self):
        """Fetches all past conversation sessions ordered by newest first."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM sessions ORDER BY created_at DESC")
            return cursor.fetchall()

    def save_message(self, session_id, role, content):
        """Appends a new conversation dialog element to the memory stack."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, content, now),
            )
            conn.commit()

    def load_messages(self, session_id):
        """Retrieves the complete message array history for a chosen window."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            )
            rows = cursor.fetchall()
            return [{"role": row[0], "content": row[1]} for row in rows]

    def _execute_web_search(self, query):
        """Silently searches the live internet for recent facts."""
        if not self.search_client:
            return "Web search is currently unavailable."
        try:
            response = self.search_client.search(
                query=query, max_results=3, topic="general"
            )
            context_list = [
                f"- {item['title']}: {item['content']}"
                for item in response.get("results", [])
            ]
            return "\n".join(context_list)
        except Exception:
            return "Failed to fetch live context data."

    def get_streaming_response(self, chat_history):
        """Evaluates data payload and pipes live streaming text chunks back."""
        max_memory_window = 6
        recent_history = (
            chat_history[-max_memory_window:]
            if len(chat_history) > max_memory_window
            else chat_history
        )

        last_user_message = chat_history[-1]["content"] if chat_history else ""
        trigger_words = [
            "weather",
            "score",
            "won",
            "news",
            "current",
            "latest",
            "today",
            "date",
        ]
        needs_search = any(word in last_user_message.lower() for word in trigger_words)

        live_context = ""
        if needs_search:
            live_context = self._execute_web_search(last_user_message)

        system_content = self.base_system_prompt
        if live_context:
            system_content += f"\n\n[LIVE SEARCH RESULTS]\n{live_context}\n\nUse this data to answer accurately."

        compiled_messages = [{"role": "system", "content": system_content}]
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
        """Permanently drops a conversation channel and all its underlying text items."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 1. Clear out message rows linked to this workspace node
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            # 2. Delete the primary chat card index reference item
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
