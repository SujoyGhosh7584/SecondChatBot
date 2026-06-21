import os
import json
import pg8000.dbapi
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from user_manager import get_db_connection
import agent_tools as tools

# Native driver conversion extension for pgvector compatibility
from pgvector.pg8000 import register_vector

load_dotenv()


def init_chat_db():
    """Ensures chat session, usage tracking, and vector RAG tables exist on Neon Cloud."""
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                session_id TEXT PRIMARY KEY,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER
            );
        """)

        # Sets up the vector module natively inside your database engine instance
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_documents (
                id SERIAL PRIMARY KEY,
                user_id TEXT,
                file_name TEXT,
                content TEXT,
                embedding vector(384) 
            );
        """)
        conn.commit()
    finally:
        conn.close()


# Initialize tables during runtime spin-up
init_chat_db()


class ChatBotEngine:
    """Handles scalable conversations, dashboard model mapping, and context retrieval."""

    def __init__(self, system_prompt="You are a helpful AI assistant."):
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.available_models = {
            "⚡Llama 3.1 (Fast)": "llama-3.1-8b-instant",
            "🚀Groq Compound (High Quality)": "groq/compound",
            "🧠OpenAI (Deep Logic)": "openai/gpt-oss-safeguard-20b",
        }
        today_str = datetime.now().strftime("%B %d, %Y")
        self.base_system_prompt = (
            f"{system_prompt}\nCurrent Real-world Date: {today_str}."
        )

    # --- SESSION MANAGEMENT METHODS ---
    def create_new_session(self, session_id, user_id, default_title="New Chat"):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM sessions WHERE id = %s;", (session_id,))
            if not cursor.fetchone():
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
            return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]
        finally:
            conn.close()

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

    def get_token_usage(self, session_id):
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
        p_tokens = int(len(prompt_text.split()) * 1.3) + 50
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

    # --- RAG KNOWLEDGE BASE METHODS ---
    def save_document(self, username, file_name, chunks, embeddings):
        """Saves text fragments and 384D embedding vectors safely into the Neon Database."""
        # Open the raw standard connection
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Check and enable pgvector extension natively via standard SQL execution
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()

            # Ensure the vector knowledge storage table exists securely
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_knowledge (
                    id SERIAL PRIMARY KEY,
                    username TEXT,
                    file_name TEXT,
                    content TEXT,
                    embedding vector(384)
                );
            """)
            conn.commit()

            # Insert each chunk alongside its formatted text vector seamlessly
            for chunk, embedding in zip(chunks, embeddings):
                # Explicitly format the float list to square bracket string notation [x, y, z]
                # to satisfy pgvector's native parser constraints
                vector_string = "[" + ",".join(map(str, embedding)) + "]"

                cursor.execute(
                    """
                    INSERT INTO document_knowledge (username, file_name, content, embedding)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (username, file_name, chunk, vector_string),
                )

            conn.commit()

        finally:
            conn.close()

    def get_relevant_context(self, username, query_text, limit=3):
        """Queries pgvector to find the most relevant document chunks for a user query."""
        import document_processor as dp

        # 1. Convert the user's raw query string into a 384D float list
        query_embedding = dp.get_embeddings(query_text)
        # Format explicitly as a square bracket string literal for pgvector compatibility
        vector_string = "[" + ",".join(map(str, query_embedding)) + "]"

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # 2. Use cosine distance operator (<=>) to fetch closest matches
            cursor.execute(
                """
                SELECT content 
                FROM document_knowledge 
                WHERE username = %s 
                ORDER BY embedding <=> %s 
                LIMIT %s;
                """,
                (username, vector_string, limit),
            )
            rows = cursor.fetchall()
            # Combine the matched chunks into a single context string
            context_chunks = [row[0] for row in rows]
            return "\n\n".join(context_chunks)
        except Exception as e:
            print(f"Error retrieving RAG context: {e}")
            return ""
        finally:
            conn.close()

    def get_relevant_context(self, user_id, query_embedding, limit=3):
        """Queries database items through geometric nearest-neighbor matching."""
        conn = get_db_connection()
        register_vector(conn)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT content FROM user_documents 
                WHERE user_id = %s 
                ORDER BY embedding <-> %s 
                LIMIT %s;
                """,
                (user_id, query_embedding, limit),
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows] if rows else []
        finally:
            conn.close()

    def get_streaming_response(
        self, chat_history, selected_model_key, context_texts=None
    ):
        """Standard conversational text retrieval routing (used for plain RAG inquiries)."""
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

        system_prompt = self.base_system_prompt
        if context_texts:
            joined_context = "\n\n---\n\n".join(context_texts)
            system_prompt += (
                f"\n\n[SYSTEM INSTRUCTION]: You have access to the user's personal documents. "
                f"Use the following context to answer their question. If the answer is not in the context, just answer normally.\n\n"
                f"CONTEXT:\n{joined_context}"
            )

        compiled_messages = [{"role": "system", "content": system_prompt}]
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

    def execute_agent_chat(self, chat_history, selected_model_key):
        """
        Handles automated tool execution loops seamlessly using a single
        continuous stream to prevent data dropping or duplicate API calls.
        """
        import agent_tools as tools

        target_model = self.available_models.get(
            selected_model_key, "llama-3.1-8b-instant"
        )

        configured_tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search_scraper",
                    "description": "CRITICAL: You MUST use this tool whenever the user asks about ANY facts, events, stats, weather, prices, dates, or info that require looking up real-time or current information beyond your static knowledge base.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query keywords.",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "agent_send_email",
                    "description": "Sends an email. Use ONLY if explicitly asked to 'email' or 'send mail'. Do NOT use if the user is simply asking a question in chat.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to_email": {
                                "type": "string",
                                "description": "Recipient email address.",
                            },
                            "subject": {
                                "type": "string",
                                "description": "Clear subject line for the email.",
                            },
                            "body_content": {
                                "type": "string",
                                "description": "The email body text formatted using standard HTML tags (<h3>, <p>, <ul>, <li>). Never include raw Markdown code inside this argument.",
                            },
                        },
                        "required": ["to_email", "subject", "body_content"],
                    },
                },
            },
        ]

        agent_system_instruction = (
            f"{self.base_system_prompt}\n\n"
            "You are Jarvis, a live AI assistant.\n\n"
            "CRITICAL PROTOCOLS:\n"
            "1. For real-time questions (weather, gold rates, news, current statistics), ALWAYS execute 'web_search_scraper' first to pull active data.\n"
            "2. Respond directly to the user in the chat interface using clean, standard Markdown. NEVER leak or show raw HTML elements (like <html>, <h3>, <ul>, <li>, or <br>) to the user in the direct chat box interface.\n"
            "3. ONLY call 'agent_send_email' if the user explicitly asked you to send an email or mail something. If they did not ask for an email, do NOT call the email tool.\n"
            "4. WORKFLOW FOR DUAL REQUESTS (e.g., 'Search X and email it to me'):\n"
            "   - Step A: Run 'web_search_scraper' to fetch the true metrics.\n"
            "   - Step B: Trigger the 'agent_send_email' tool, packaging the fetched metrics into a clean HTML format inside the 'body_content' parameter.\n"
            "   - Step C: Respond in the chat window using human-readable plain text/markdown confirming that the data was pulled and the email has been sent successfully."
        )

        messages = [{"role": "system", "content": agent_system_instruction}]
        for m in chat_history[-6:]:
            messages.append({"role": m["role"], "content": m["content"]})

        try:
            response_stream = self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                tools=configured_tools,
                tool_choice="auto",
                stream=True,
            )

            tool_calls_to_process = {}

            for chunk in response_stream:
                delta = chunk.choices[0].delta

                if delta.content:
                    yield delta.content

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_to_process:
                            tool_calls_to_process[idx] = {
                                "id": tc.id,
                                "name": tc.function.name if tc.function else "",
                                "arguments": (
                                    tc.function.arguments if tc.function else ""
                                ),
                            }
                        else:
                            if tc.function and tc.function.name:
                                tool_calls_to_process[idx]["name"] += tc.function.name
                            if tc.function and tc.function.arguments:
                                tool_calls_to_process[idx][
                                    "arguments"
                                ] += tc.function.arguments

            if tool_calls_to_process:
                assistant_msg = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"],
                            },
                        }
                        for tc in tool_calls_to_process.values()
                    ],
                }
                messages.append(assistant_msg)

                # Run the actual Python tool functions
                for tc in tool_calls_to_process.values():
                    func_name = tc["name"]
                    raw_args = tc["arguments"]

                    # 🛡️ ROBUST JSON REPAIR LAYER
                    try:
                        args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        try:
                            cleaned_args = raw_args.strip().lstrip("`").rstrip("`")
                            if cleaned_args.startswith("{") and cleaned_args.endswith(
                                "}"
                            ):
                                args = json.loads(cleaned_args)
                            else:
                                raise Exception()
                        except:
                            args = {
                                "query": raw_args,
                                "body_content": raw_args,
                                "to_email": "",
                            }

                    # Execute the respective tool matching the function schema name
                    if func_name == "web_search_scraper":
                        search_query = (
                            args.get("query") if isinstance(args, dict) else raw_args
                        )
                        if isinstance(search_query, str) and search_query.startswith(
                            "{"
                        ):
                            try:
                                search_query = json.loads(search_query).get(
                                    "query", search_query
                                )
                            except:
                                pass
                        result = tools.web_search_scraper(search_query)

                    elif func_name == "agent_send_email":
                        result = tools.agent_send_email(
                            args.get("to_email", ""),
                            args.get("subject", "Automated Live Report Update"),
                            args.get(
                                "body_content", str(args.get("body_content", args))
                            ),
                        )
                    else:
                        result = f"Error: Function name '{func_name}' is not recognized by the runtime."

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": func_name,
                            "content": str(result),
                        }
                    )

                # Final recall loop to provide user feedback after tools complete execution
                final_stream = self.client.chat.completions.create(
                    model=target_model, messages=messages, stream=True
                )
                for chunk in final_stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"Agent Execution Error: {str(e)}"
