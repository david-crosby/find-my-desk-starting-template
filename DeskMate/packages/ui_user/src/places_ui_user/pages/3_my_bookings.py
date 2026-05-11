import streamlit as st

from places_ui_user.api_client import cancel_booking, list_my_bookings

st.set_page_config(page_title="My Bookings", page_icon="📋")
st.title("My Bookings")

user_id: int = st.session_state.get("user_id", 1)
bookings = list_my_bookings(user_id)

if not bookings:
    st.info("You have no bookings.")
else:
    for b in bookings:
        resource = "desk" if b.get("desk_id") else "room"
        label = f"#{b['id']} — {b['date']} ({resource}) — {b['status']}"
        with st.expander(label):
            st.json(b)
            if b["status"] == "confirmed":
                if st.button("Cancel this booking", key=f"cancel_{b['id']}"):
                    cancel_booking(b["id"])
                    st.success("Booking cancelled.")
                    st.rerun()
