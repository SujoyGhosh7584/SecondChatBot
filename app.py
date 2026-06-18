import uuid
import streamlit as st
from user_manager import UserManager
from ai_engine import ChatBotEngine

st.set_page_config(page_title="2nd Chat Bot", page_icon="🤖", layout="wide")

# 🛠️ 1. INITIALIZE BACKEND CONFIGURATIONS INDEPENDENTLY
if "user_manager" not in st.session_state:
    st.session_state.user_manager = UserManager()

if "bot_engine" not in st.session_state:
    st.session_state.bot_engine = ChatBotEngine(
        system_prompt="You are Jarvis, a brilliant and slightly sarcastic AI companion."
    )

if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

# 🔐 WALL OF AUTHENTICATION: RENDER LOGIN SCREEN IF NO USER LOGGED IN
if st.session_state.authenticated_user is None:
    st.title("🔒 Chatbot Access Gateway")

    tab_login, tab_signup = st.tabs(
        ["🔑 Existing Account Login", "📝 Create Free Account"]
    )

    with tab_login:
        with st.form("login_form"):
            user_input = st.text_input("Username").strip().lower()
            pass_input = st.text_input("Password", type="password")
            btn_login = st.form_submit_button(
                "Sign In To Dashboard", use_container_width=True
            )

            if btn_login:
                if st.session_state.user_manager.verify_user(user_input, pass_input):
                    st.session_state.authenticated_user = user_input

                    user_sessions = st.session_state.bot_engine.get_all_sessions(
                        user_input
                    )
                    if user_sessions:
                        st.session_state.active_session_id = user_sessions[0][0]
                    else:
                        initial_id = str(uuid.uuid4())
                        st.session_state.active_session_id = initial_id
                        st.session_state.bot_engine.create_new_session(
                            initial_id, user_input, "Welcome Chat"
                        )
                    st.rerun()
                else:
                    st.error("Invalid username or password credentials.")

    with tab_signup:
        with st.form("signup_form"):
            new_user = st.text_input("Choose Unique Username").strip().lower()
            new_pass = st.text_input("Set Secure Password", type="password")
            btn_signup = st.form_submit_button(
                "Register New Account", use_container_width=True
            )

            if btn_signup:
                success, msg = st.session_state.user_manager.register_user(
                    new_user, new_pass
                )
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    st.stop()

# 🧑‍💻 IF PASSED HERE, USER IS AUTHENTICATED
current_user = st.session_state.authenticated_user

# 🎨 2. SIDEBAR PANEL (User Isolated Chat Multi-Row Management)
with st.sidebar:
    st.title("💬 Chat History")
    st.caption(f"Logged in as: **{current_user}**")

    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())
        st.session_state.active_session_id = new_id
        st.session_state.bot_engine.create_new_session(
            new_id, current_user, "New Chat Window"
        )
        st.rerun()

    st.write("---")

    past_sessions = st.session_state.bot_engine.get_all_sessions(current_user)

    for session_id, title in past_sessions:
        is_current = session_id == st.session_state.active_session_id
        button_label = f"📝 {title}" if not is_current else f"🔥 {title}"

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
                st.session_state.bot_engine.delete_session(session_id)

                if is_current:
                    remaining_sessions = st.session_state.bot_engine.get_all_sessions(
                        current_user
                    )
                    if remaining_sessions:
                        st.session_state.active_session_id = remaining_sessions[0][0]
                    else:
                        fresh_id = str(uuid.uuid4())
                        st.session_state.active_session_id = fresh_id
                        st.session_state.bot_engine.create_new_session(
                            fresh_id, current_user, "Welcome Chat"
                        )
                st.rerun()

    st.write("---")
    if st.button("🚪 Log Out Account", use_container_width=True):
        st.session_state.authenticated_user = None
        if "active_session_id" in st.session_state:
            del st.session_state.active_session_id
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

    st.session_state.bot_engine.save_message(current_session, "user", prompt)

    if len(active_messages) == 0:
        clean_title = prompt[:25] + "..." if len(prompt) > 25 else prompt
        st.session_state.bot_engine.update_session_title(current_session, clean_title)

    with st.chat_message("assistant", avatar="🤖"):
        try:
            updated_history = st.session_state.bot_engine.load_messages(current_session)
            stream_generator = st.session_state.bot_engine.get_streaming_response(
                updated_history
            )
            response = st.write_stream(stream_generator)
            st.session_state.bot_engine.save_message(
                current_session, "assistant", response
            )
            st.rerun()  # Forces immediate visual confirmation of the saved assistant message

        except Exception as e:
            st.error(f"System Error: {e}")
