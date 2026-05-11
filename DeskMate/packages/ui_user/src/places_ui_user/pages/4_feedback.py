"""Feedback page — the DeskMate agent collects post-visit ratings in conversation."""

import uuid

import streamlit as st

from places_ui_user.api_client import agent_chat, list_my_bookings

st.set_page_config(page_title="Leave Feedback", layout="wide")
from places_core.streamlit_auth import require_login
require_login()
st.title("Leave Feedback")
st.caption("Tell DeskMate how your visit went. The agent will ask a few quick questions.")

user_id: int = st.session_state.get("user_id", 1)
user_display_name: str = st.session_state.get("user_display_name", "User")

# --- Determine which booking to give feedback on ---
# May have been pre-set by the My Bookings page redirect.
feedback_booking_id: int | None = st.session_state.get("feedback_booking_id")

with st.sidebar:
    st.markdown("### Select a booking")
    try:
        bookings = list_my_bookings(user_id)
        # Only show bookings that could have feedback
        eligible = [
            b for b in bookings
            if b["status"] in ("completed", "allocated", "confirmed")
        ]
    except Exception:
        eligible = []

    if eligible:
        booking_labels = {
            f"#{b['id']} — {b['date']} ({'desk' if b.get('desk_id') else 'room'})": b["id"]
            for b in eligible
        }
        default_label = next(
            (k for k, v in booking_labels.items() if v == feedback_booking_id),
            list(booking_labels.keys())[0],
        )
        selected_label = st.selectbox(
            "Booking", list(booking_labels.keys()), index=list(booking_labels.keys()).index(default_label)
        )
        selected_booking_id = booking_labels[selected_label]

        if selected_booking_id != st.session_state.get("feedback_booking_id"):
            st.session_state["feedback_booking_id"] = selected_booking_id
            # Reset the conversation when the user switches bookings
            st.session_state.pop("feedback_messages", None)
            st.session_state.pop("feedback_session_id", None)
            st.rerun()
    else:
        st.info("No eligible bookings for feedback.")
        st.stop()

    if st.button("New conversation", use_container_width=True):
        st.session_state.pop("feedback_messages", None)
        st.session_state.pop("feedback_session_id", None)
        st.rerun()

# --- Feedback chat session ---
if "feedback_session_id" not in st.session_state:
    st.session_state.feedback_session_id = str(uuid.uuid4())
if "feedback_messages" not in st.session_state:
    st.session_state.feedback_messages = []

booking_id = st.session_state.get("feedback_booking_id")

# Auto-start the feedback conversation if it hasn't started yet
if not st.session_state.feedback_messages and booking_id:
    opening = (
        f"I'd like to leave feedback for booking #{booking_id}. Can you help me with that?"
    )
    st.session_state.feedback_messages.append({"role": "user", "content": opening})

    with st.spinner(""):
        try:
            reply = agent_chat(
                message=opening,
                session_id=st.session_state.feedback_session_id,
                user_id=user_id,
                user_display_name=user_display_name,
            )
        except Exception as exc:
            reply = f"Could not reach the agent server. Is it running on port 8001? ({exc})"

    st.session_state.feedback_messages.append({"role": "assistant", "content": reply})

# Display conversation
for msg in st.session_state.feedback_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Continue the conversation
if prompt := st.chat_input("Reply here..."):
    st.session_state.feedback_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(""):
            try:
                reply = agent_chat(
                    message=prompt,
                    session_id=st.session_state.feedback_session_id,
                    user_id=user_id,
                    user_display_name=user_display_name,
                )
            except Exception as exc:
                reply = f"Could not reach the agent server. ({exc})"
        st.markdown(reply)

    st.session_state.feedback_messages.append({"role": "assistant", "content": reply})
