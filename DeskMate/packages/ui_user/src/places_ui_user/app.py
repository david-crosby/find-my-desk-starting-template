import uuid

import streamlit as st

st.set_page_config(
    page_title="DeskMate",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Sidebar: user identity (demo mode — replace with SSO in production) ---
with st.sidebar:
    st.markdown("### Who are you?")
    st.caption("In production this comes from Microsoft Entra SSO.")

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

    st.divider()
    st.markdown("**Pages**")
    st.markdown("Use the navigation above to book desks, rooms, or leave feedback.")

    if st.button("New conversation", use_container_width=True):
        st.session_state.pop("messages", None)
        st.session_state.pop("session_id", None)
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
