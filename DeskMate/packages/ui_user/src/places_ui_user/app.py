import uuid

import streamlit as st
from places_core.settings import settings
from places_core.streamlit_auth import logout, require_login

st.set_page_config(
    page_title="DeskMate",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_login()

# Resolve the signed-in Entra user to a local DB record (created on first visit).
if settings.ms_places_enabled and "user_id" not in st.session_state:
    try:
        from places_ui_user.api_client import get_me
        me = get_me()
        st.session_state["user_id"] = me["id"]
        st.session_state["user_display_name"] = me["display_name"]
    except Exception:
        st.session_state.setdefault("user_display_name", st.session_state.get("auth_name", "User"))

# --- Sidebar ---
with st.sidebar:
    auth_name = st.session_state.get("auth_name", "User")
    auth_email = st.session_state.get("auth_email", "")

    if settings.ms_places_enabled:
        st.markdown(f"**{auth_name}**")
        if auth_email:
            st.caption(auth_email)
        if st.button("Sign out", use_container_width=True):
            logout()
    else:
        st.markdown("### Who are you?")
        st.caption("Demo mode — Entra SSO disabled.")

        try:
            from places_ui_user.api_client import list_users

            users = list_users()
            user_options = {f"{u['display_name']} ({u['email']})": u for u in users}
        except Exception:
            user_options = {}

        if user_options:
            selected_label = st.selectbox("Select your profile", list(user_options.keys()))
            active_user = user_options[selected_label]
            st.session_state["user_id"] = active_user["id"]
            st.session_state["user_display_name"] = active_user["display_name"]
        else:
            st.session_state.setdefault("user_id", 1)
            st.session_state.setdefault("user_display_name", "Demo User")
            st.warning("Backend not reachable — using demo user.")

    if not settings.ms_places_enabled:
        st.session_state.setdefault("user_display_name", auth_name)

    st.divider()
    st.markdown("**Pages**")
    st.markdown("Use the navigation above to book desks, rooms, or leave feedback.")

    if st.button("New conversation", use_container_width=True):
        for key in ("messages", "session_id", "user_id", "user_display_name"):
            st.session_state.pop(key, None)
        st.rerun()

# --- Session initialisation ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# --- Main chat UI ---
st.title("DeskMate")
st.caption(
    "Book a desk or room, manage your bookings, or leave feedback — just ask."
)

# Replay conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask me to book a desk, cancel a booking, give feedback..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    from places_ui_user.api_client import agent_chat

    with st.chat_message("assistant"):
        with st.spinner(""):
            try:
                reply = agent_chat(
                    message=prompt,
                    session_id=st.session_state.session_id,
                    user_id=st.session_state.get("user_id", 1),
                    user_display_name=st.session_state.get("user_display_name", "User"),
                )
            except Exception as exc:
                reply = (
                    f"Sorry, I could not reach the agent server. "
                    f"Please check it is running on port 8001. ({exc})"
                )
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
