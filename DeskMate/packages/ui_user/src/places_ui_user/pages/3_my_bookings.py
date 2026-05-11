import streamlit as st

from places_ui_user.api_client import cancel_booking, get_booking_feedback, list_my_bookings

st.set_page_config(page_title="My Bookings", layout="wide")
st.title("My Bookings")

user_id: int = st.session_state.get("user_id", 1)
bookings = list_my_bookings(user_id)

if not bookings:
    st.info("You have no bookings.")
    st.stop()

# Sort so that upcoming bookings appear first
bookings_sorted = sorted(bookings, key=lambda b: b["date"], reverse=True)

for b in bookings_sorted:
    resource = "Desk" if b.get("desk_id") else "Room"
    resource_id = b.get("desk_id") or b.get("room_id", "")
    status_label = b["status"].replace("_", " ").title()
    label = f"{b['date']}  |  {resource} #{resource_id}  |  {status_label}"

    with st.expander(label):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.json(b)

        with col2:
            # Cancellation — allow for queued or confirmed bookings
            if b["status"] in ("queued", "confirmed", "allocated"):
                if st.button("Cancel booking", key=f"cancel_{b['id']}"):
                    cancel_booking(b["id"])
                    st.success("Booking cancelled.")
                    st.rerun()

            # Feedback prompt — show for completed bookings without feedback
            if b["status"] == "completed":
                existing = get_booking_feedback(b["id"])
                if existing:
                    st.success("Feedback submitted. Thank you.")
                else:
                    st.info("How was your visit?")
                    if st.button("Leave feedback via DeskMate", key=f"fb_{b['id']}"):
                        st.session_state["feedback_booking_id"] = b["id"]
                        st.switch_page("pages/4_feedback.py")
