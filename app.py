import uuid
import streamlit as st
from user_manager import UserManager
from ai_engine import ChatBotEngine
from ui_components import inject_custom_theme, render_login_header

# ⚠️ FIX: Changed to "centered" layout to naturally group the login form and remove empty space bugs
st.set_page_config(page_title="S U J O Y", page_icon="🤖", layout="centered")

# Trigger clean design layers
inject_custom_theme()

# INITIALIZE BACKEND CONFIGURATIONS INDEPENDENTLY
if "user_manager" not in st.session_state:
    st.session_state.user_manager = UserManager()

if "bot_engine" not in st.session_state:
    st.session_state.bot_engine = ChatBotEngine(
        system_prompt="You are Jarvis, a brilliant and slightly sarcastic AI companion."
    )

if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

# 🔐 WALL OF AUTHENTICATION: RENDER GATEWAY OVERLAY IF NO USER ACTIVE
if st.session_state.authenticated_user is None:

    # ⚠️ FIX: Uses Streamlit's native container border to build the form box layout cleanly
    with st.container(border=True):
        render_login_header()

        tab_login, tab_signup = st.tabs(["🔑 Account Login", "📝 Create Free Account"])

        with tab_login:
            st.write("")
            with st.form("login_form", clear_on_submit=False):
                user_input = (
                    st.text_input("Username", placeholder="e.g. sujoy_99")
                    .strip()
                    .lower()
                )
                pass_input = st.text_input(
                    "Password", type="password", placeholder="••••••••"
                )
                btn_login = st.form_submit_button(
                    "Sign In To Dashboard", use_container_width=True, type="primary"
                )

                if btn_login:
                    if st.session_state.user_manager.verify_user(
                        user_input, pass_input
                    ):
                        st.session_state.authenticated_user = user_input
                        user_sessions = st.session_state.bot_engine.get_all_sessions(
                            user_input
                        )
                        if user_sessions:
                            st.session_state.active_session_id = user_sessions
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
            st.write("")
            with st.form("signup_form", clear_on_submit=True):
                new_user = (
                    st.text_input(
                        "Choose Unique Username", placeholder="Letters and numbers only"
                    )
                    .strip()
                    .lower()
                )
                new_pass = st.text_input(
                    "Set Secure Password",
                    type="password",
                    placeholder="Min 6 characters",
                )
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

# 🧑‍💻 AUTHENTICATED CONTROL MATRIX LAYOUT
current_user = st.session_state.authenticated_user

# 🎨 SIDEBAR PANEL (Dynamic Models Selector, History List & Advanced Metrics)
with st.sidebar:
    st.title("⚙️ Control Dashboard")
    st.caption(f"User Active: **{current_user}**")

    chosen_model = st.selectbox(
        "🧠 Active Brain Model",
        options=list(st.session_state.bot_engine.available_models.keys()),
    )

    st.write("---")
    st.subheader("💬 Chat History")

    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())
        st.session_state.active_session_id = new_id
        st.session_state.bot_engine.create_new_session(
            new_id, current_user, "New Chat Window"
        )
        st.rerun()

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
                        st.session_state.active_session_id = remaining_sessions
                    else:
                        fresh_id = str(uuid.uuid4())
                        st.session_state.active_session_id = fresh_id
                        st.session_state.bot_engine.create_new_session(
                            fresh_id, current_user, "Welcome Chat"
                        )
                st.rerun()

    st.write("---")

    current_session = st.session_state.active_session_id
    usage = st.session_state.bot_engine.get_token_usage(current_session)

    with st.expander("📊 Session Token Analytics", expanded=False):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Prompt", f"{usage['prompt']}")
        with col_m2:
            st.metric("Output", f"{usage['completion']}")
        st.metric("Total Shared Usage", f"{usage['total']} Tokens")
        st.caption("Calculated using standard base byte tokenization ratios.")

    if st.button("🚪 Log Out Account", use_container_width=True):
        st.session_state.authenticated_user = None
        if "active_session_id" in st.session_state:
            del st.session_state.active_session_id
        st.rerun()

# 💬 FETCH AND DISPLAY CURRENT DIALOG CHANNEL
active_messages = st.session_state.bot_engine.load_messages(current_session)

# ⚠️ FIX: Swapped column layout selectors with a clean native subheader placement.
# This separates titles and download files cleanly without pushing the button up into the invisible header zone.
st.subheader("⚡ Sujoy's Chatbot Pro")

if active_messages:
    raw_markdown = f"# Chat History Log\n*Session ID: {current_session}*\n\n"
    for m in active_messages:
        raw_markdown += f"### **{m['role'].upper()}**:\n{m['content']}\n\n---\n"

    st.download_button(
        label="📥 Export Chat Log (.md)",
        data=raw_markdown,
        file_name=f"chat_log_{current_session[:8]}.md",
        mime="text/markdown",
        use_container_width=False,  # Inline natural sizing keeps the text fully visible
    )

st.caption(
    f"Active Workspace Tracking ID Node: `{current_session}` | Model: **{chosen_model}**"
)
st.write("---")

for message in active_messages:
    avatar = "🧑‍💻" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# INCOMING CHAT PROCESSING LOOP WITH MEMORY DUMP WRITING
if prompt := st.chat_input("Ask something..."):
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
                updated_history, chosen_model
            )
            response = st.write_stream(stream_generator)

            st.session_state.bot_engine.save_message(
                current_session, "assistant", response
            )
            st.session_state.bot_engine.update_token_usage(
                current_session, prompt, response
            )
            st.rerun()

        except Exception as e:
            st.error(f"System Error: {e}")
