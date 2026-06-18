import sqlite3
import hashlib
from datetime import datetime

DB_PATH = "chatbot_memory.db"


def init_user_db():
    """Ensures the users table exists in the database."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT,
                created_at TEXT
            )
        """)
        conn.commit()


# Initialize table immediately upon module import
init_user_db()


class UserManager:
    """Handles everything related to user security, sign-ups, and login validation."""

    def __init__(self):
        self.db_path = DB_PATH

    def _hash_password(self, password):
        """Hashes raw text passwords using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, password):
        """Registers a user node. Returns (Success Boolean, Feedback Message)."""
        username = username.strip().lower()
        if not username or not password:
            return False, "Fields cannot be blank."

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                pwd_hash = self._hash_password(password)
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT INTO users VALUES (?, ?, ?)", (username, pwd_hash, now)
                )
                conn.commit()
                return True, "Registration successful!"
        except sqlite3.IntegrityError:
            return False, "This username is already taken."

    def verify_user(self, username, password):
        """Validates input matches hashed database references."""
        username = username.strip().lower()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT password_hash FROM users WHERE username = ?", (username,)
            )
            row = cursor.fetchone()
            if row and row[0] == self._hash_password(password):
                return True
            return False
