import pandas as pd
import streamlit as st

from places_ui_admin.api_client import list_all_bookings

st.set_page_config(page_title="All Bookings", page_icon="📋", layout="wide")
st.title("All Bookings")

bookings = list_all_bookings()

if not bookings:
    st.info("No bookings found.")
else:
    df = pd.DataFrame(bookings)

    status_filter = st.multiselect(
        "Filter by status", options=df["status"].unique().tolist(), default=df["status"].unique().tolist()
    )
    df = df[df["status"].isin(status_filter)]

    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"{len(df)} booking(s) shown.")
