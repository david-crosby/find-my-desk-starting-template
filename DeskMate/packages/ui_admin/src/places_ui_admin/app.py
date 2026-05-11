import streamlit as st

st.set_page_config(page_title="Places Admin", page_icon="⚙️", layout="wide")

st.title("Places Admin Dashboard")
st.markdown(
    "Select a page from the **sidebar** to manage locations, floors, desks, rooms, and bookings."
)

col1, col2, col3 = st.columns(3)

with col1:
    from places_ui_admin.api_client import list_all_bookings

    try:
        bookings = list_all_bookings()
        confirmed = sum(1 for b in bookings if b["status"] == "confirmed")
        st.metric("Total bookings", len(bookings))
        st.metric("Confirmed", confirmed)
    except Exception:
        st.warning("Backend not reachable.")

with col2:
    from places_ui_admin.api_client import list_desks

    try:
        desks = list_desks()
        active = sum(1 for d in desks if d["is_active"])
        st.metric("Total desks", len(desks))
        st.metric("Active desks", active)
    except Exception:
        pass

with col3:
    from places_ui_admin.api_client import list_rooms

    try:
        rooms = list_rooms()
        st.metric("Total rooms", len(rooms))
    except Exception:
        pass
