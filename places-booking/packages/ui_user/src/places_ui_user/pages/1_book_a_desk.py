from datetime import date, timedelta

import streamlit as st

from places_ui_user.api_client import create_booking, list_desks

st.set_page_config(page_title="Book a Desk", page_icon="💺")
st.title("Book a Desk")

col1, col2 = st.columns(2)
with col1:
    booking_date = st.date_input(
        "Date", min_value=date.today(), value=date.today() + timedelta(days=1)
    )
with col2:
    floor_id = st.number_input("Floor ID (0 = any)", min_value=0, value=0, step=1)

if st.button("Find available desks", type="primary"):
    desks = list_desks(floor_id=int(floor_id) if floor_id > 0 else None)
    if desks:
        st.session_state["available_desks"] = desks
        st.success(f"{len(desks)} desk(s) available.")
    else:
        st.warning("No desks available for this date/floor.")
        st.session_state.pop("available_desks", None)

if "available_desks" in st.session_state:
    desks = st.session_state["available_desks"]
    desk_labels = {f"Desk {d['label']} (floor {d['floor_id']})": d["id"] for d in desks}
    choice = st.selectbox("Select a desk", list(desk_labels.keys()))

    if st.button("Confirm booking"):
        booking = create_booking(
            {
                "user_id": st.session_state.get("user_id", 1),
                "desk_id": desk_labels[choice],
                "date": str(booking_date),
            }
        )
        st.success(f"Booked! Booking ID: **{booking['id']}**")
        del st.session_state["available_desks"]
