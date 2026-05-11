from datetime import date, time, timedelta

import streamlit as st

from places_ui_user.api_client import create_booking, list_rooms

st.set_page_config(page_title="Book a Room", page_icon="🚪")
from places_core.streamlit_auth import require_login
require_login()
st.title("Book a Meeting Room")

col1, col2, col3 = st.columns(3)
with col1:
    booking_date = st.date_input(
        "Date", min_value=date.today(), value=date.today() + timedelta(days=1)
    )
with col2:
    start_time = st.time_input("Start time", value=time(9, 0))
with col3:
    end_time = st.time_input("End time", value=time(10, 0))

min_cap = st.number_input("Minimum capacity", min_value=1, value=2, step=1)

if st.button("Find available rooms", type="primary"):
    rooms = list_rooms(min_capacity=int(min_cap))
    if rooms:
        st.session_state["available_rooms"] = rooms
        st.success(f"{len(rooms)} room(s) available.")
    else:
        st.warning("No rooms match your criteria.")
        st.session_state.pop("available_rooms", None)

if "available_rooms" in st.session_state:
    rooms = st.session_state["available_rooms"]
    room_labels = {f"{r['name']} (cap {r['capacity']})": r["id"] for r in rooms}
    choice = st.selectbox("Select a room", list(room_labels.keys()))

    if st.button("Confirm booking"):
        booking = create_booking(
            {
                "user_id": st.session_state.get("user_id", 1),
                "room_id": room_labels[choice],
                "date": str(booking_date),
                "start_time": start_time.strftime("%H:%M"),
                "end_time": end_time.strftime("%H:%M"),
            }
        )
        st.success(f"Booked! Booking ID: **{booking['id']}**")
        del st.session_state["available_rooms"]
