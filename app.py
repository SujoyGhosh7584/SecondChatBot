import uuid
import streamlit as st
from ai_engine import ChatBotEngine

st.set_page_config(page_title="2nd Chat Bot", page_icon="🤖", layout="wide")

# 🛠️ 1. INITIALIZE BACKEND CONFIGURATION
if "bot_engine" not in st.session_state:
    st.session_state.bot_engine = ChatBotEngine(
        system_prompt="You are Jarvis, a brilliant and slightly sarcastic AI companion."
    )

# Establish tracking nodes for active window context swapping
if "active_session_id" not in st.session_state:
    initial_id = str(uuid.uuid4())
    st.session_state.active_session_id = initial_id
    st.session_state.bot_engine.create_new_session(initial_id, "Welcome Chat")

# 🎨 2. SIDEBAR PANEL (ChatGPT Style History Multi-Row Management)
with st.sidebar:
    st.title("💬 Chat History")

    # New Chat Launch Control
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())
        st.session_state.active_session_id = new_id
        st.session_state.bot_engine.create_new_session(new_id, "New Chat Window")
        st.rerun()

    st.write("---")

    # Render list links to historical chat nodes with interactive delete options
    past_sessions = st.session_state.bot_engine.get_all_sessions()

    for session_id, title in past_sessions:
        is_current = session_id == st.session_state.active_session_id
        button_label = f"📝 {title}" if not is_current else f"🔥 {title}"

        # Create two uneven columns to place the select button next to the trash bin
        col_link, col_del = st.columns([0.82, 0.18])

        with col_link:
            if st.button(
                button_label,
                key=f"link_{session_id}",
                use_container_width=True,
                disabled=is_current,
            ):
                st.session_state.active_session_id = session_id
                st.rerun()

        with col_del:
            if st.button("🗑️", key=f"del_{session_id}", use_container_width=True):
                # 1. Execute deletion down in the database storage layer
                st.session_state.bot_engine.delete_session(session_id)

                # 2. Redirect safety guardrail: If the active chat is deleted, swap to another
                if is_current:
                    remaining_sessions = st.session_state.bot_engine.get_all_sessions()
                    if remaining_sessions:
                        st.session_state.active_session_id = remaining_sessions[0][0]
                    else:
                        # Clean slate fallback if the user clears out absolutely everything
                        fresh_id = str(uuid.uuid4())
                        st.session_state.active_session_id = fresh_id
                        st.session_state.bot_engine.create_new_session(
                            fresh_id, "Welcome Chat"
                        )
                st.rerun()

# 💬 3. FETCH AND DISPLAY HISTORICAL DIALOG ROUNDS FOR CURRENT CHANNEL
current_session = st.session_state.active_session_id
active_messages = st.session_state.bot_engine.load_messages(current_session)

st.title("⚡ Sujoy's 2nd chatbot is here to help")
st.caption(f"Active Workspace Tracking ID Node: `{current_session}`")

for message in active_messages:
    avatar = "🧑‍💻" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# 🚀 4. INCOMING CHAT PROCESSING LOOP WITH MEMORY DUMP WRITING
if prompt := st.chat_input("Ask Sujoy something..."):
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)

    # Save user input permanently to our SQLite database
    st.session_state.bot_engine.save_message(current_session, "user", prompt)

    # Automatically rename "New Chat Window" based on the very first user message
    if len(active_messages) == 0:
        st.session_state.bot_engine.update_session_title(current_session, prompt)

    # Render streaming response from backend
    with st.chat_message("assistant", avatar="🤖"):
        try:
            updated_history = st.session_state.bot_engine.load_messages(current_session)

            stream_generator = st.session_state.bot_engine.get_streaming_response(
                updated_history
            )
            response = st.write_stream(stream_generator)

            # Save the final AI response to the database
            st.session_state.bot_engine.save_message(
                current_session, "assistant", response
            )
            st.rerun()

        except Exception as e:
            st.error(f"System Error: {e}")
