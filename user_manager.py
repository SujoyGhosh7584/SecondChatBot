import os
import pg8000.dbapi
import hashlib
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL")


def get_db_connection():
    """Safely parses any complex connection string using robust URL parsing engines."""
    if not DB_URL:
        raise ValueError(
            "Critical Error: DATABASE_URL environment variable is missing."
        )

    # Leverage robust built-in URL parser to handle special characters seamlessly
    parsed = urllib.parse.urlparse(DB_URL)

    user = parsed.username
    password = parsed.password
    host = parsed.hostname
    port = parsed.port if parsed.port else 5432
    database = parsed.path.lstrip("/")

    return pg8000.dbapi.connect(
        user=user,
        password=password,
        host=host,
        port=port,
        database=database,
        ssl_context=True,  # Required for Neon secure traffic pathways
    )


def init_user_db():
    """Ensures the accounts architecture exists safely inside your Neon Cloud project."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT,
                created_at TEXT
            );
        """)
        conn.commit()
    finally:
        conn.close()


# Structural autogeneration triggered instantly upon boot sequence
init_user_db()


class UserManager:
    """Manages cloud profile instances and verifies account credential match structures."""

    def _hash_password(self, password):
        """Hashes raw text passwords using standard SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, password):
        """Saves credentials up into Neon server logs. Returns (Success, Message)."""
        username = username.strip().lower()
        if not username or not password:
            return False, "Fields cannot be blank."

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            pwd_hash = self._hash_password(password)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Using standard parameter placeholder format for pg8000 compatibility
            cursor.execute(
                "INSERT INTO users VALUES (%s, %s, %s);", (username, pwd_hash, now)
            )
            conn.commit()
            return True, "Registration successful!"
        except pg8000.dbapi.IntegrityError:
            return False, "This username is already taken."
        finally:
            conn.close()

    def verify_user(self, username, password):
        """Validates input matches cloud database reference structures."""
        username = username.strip().lower()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT password_hash FROM users WHERE username = %s;", (username,)
            )
            row = cursor.fetchone()
            if row and row[0] == self._hash_password(password):
                return True
            return False
        finally:
            conn.close()
