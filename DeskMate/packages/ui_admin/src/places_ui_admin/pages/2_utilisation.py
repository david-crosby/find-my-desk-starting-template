import pandas as pd
import streamlit as st

from places_ui_admin.api_client import list_all_bookings, list_desks, list_rooms

st.set_page_config(page_title="Utilisation", page_icon="📊", layout="wide")
st.title("Utilisation")

bookings = list_all_bookings()
if not bookings:
    st.info("No booking data yet.")
    st.stop()

df = pd.DataFrame(bookings)
df["date"] = pd.to_datetime(df["date"])

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total bookings", len(df))
with col2:
    st.metric("Confirmed", int((df["status"] == "confirmed").sum()))
with col3:
    st.metric("Cancelled", int((df["status"] == "cancelled").sum()))

st.subheader("Bookings per day")
daily = df.groupby("date").size().reset_index(name="count")
st.bar_chart(daily.set_index("date")["count"])

desk_bookings = df[df["desk_id"].notna()]
room_bookings = df[df["room_id"].notna()]

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Desk utilisation")
    if not desk_bookings.empty:
        st.bar_chart(desk_bookings.groupby("date").size())
    else:
        st.info("No desk bookings yet.")

with col_b:
    st.subheader("Room utilisation")
    if not room_bookings.empty:
        st.bar_chart(room_bookings.groupby("date").size())
    else:
        st.info("No room bookings yet.")
