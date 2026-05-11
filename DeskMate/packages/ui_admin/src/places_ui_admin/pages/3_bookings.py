"""Booking Behaviour — advance booking patterns, cancellations, repeat desk usage."""

import pandas as pd
import streamlit as st

from places_ui_admin.api_client import get_analytics_summary, list_all_bookings

st.set_page_config(page_title="Booking Behaviour", layout="wide")
st.title("Booking Behaviour")

try:
    bookings = list_all_bookings()
    summary = get_analytics_summary()
except Exception as exc:
    st.error(f"Could not load data: {exc}")
    st.stop()

if not bookings:
    st.info("No bookings found.")
    st.stop()

df = pd.DataFrame(bookings)
df["date"] = pd.to_datetime(df["date"])
if "booking_created_at" in df.columns:
    df["booking_created_at"] = pd.to_datetime(df["booking_created_at"], errors="coerce")
    df["advance_days"] = (df["date"] - df["booking_created_at"].dt.normalize()).dt.days.clip(lower=0)

# ── KPI row ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Bookings", len(df))
c2.metric("Avg Advance Booking Days", summary.get("avg_advance_booking_days", "—"))
c3.metric("No-shows", df[df["status"] == "no_show"].shape[0])
c4.metric("Cancellations", df[df["status"] == "cancelled"].shape[0])

st.divider()

# ── Advance booking distribution ─────────────────────────────────────────────
if "advance_days" in df.columns and df["advance_days"].notna().any():
    st.subheader("Advance booking distribution (days before visit)")
    hist_data = df["advance_days"].dropna().astype(int)
    hist_df = hist_data.value_counts().sort_index().reset_index()
    hist_df.columns = ["Days in advance", "Bookings"]
    st.bar_chart(hist_df.set_index("Days in advance"))
    st.divider()

# ── Repeat desk usage ─────────────────────────────────────────────────────────
st.subheader("Most booked desks (desk loyalty)")
top_desks = summary.get("top_desks_by_usage", [])
if top_desks:
    df_top = pd.DataFrame(top_desks)
    df_top.columns = ["Desk ID", "Bookings"]
    st.dataframe(df_top, use_container_width=True, hide_index=True)
else:
    st.info("No repeat desk data yet.")

st.divider()

# ── All bookings table ────────────────────────────────────────────────────────
st.subheader("All bookings")
status_options = df["status"].unique().tolist()
status_filter = st.multiselect("Filter by status", options=status_options, default=status_options)
source_options = df["booking_source"].unique().tolist() if "booking_source" in df.columns else []
source_filter = st.multiselect("Filter by source", options=source_options, default=source_options)

filtered = df[df["status"].isin(status_filter)]
if source_options:
    filtered = filtered[filtered["booking_source"].isin(source_filter)]

display_cols = [c for c in ["id", "user_id", "desk_id", "room_id", "date", "status", "booking_source", "advance_days"] if c in filtered.columns]
st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True)
st.caption(f"{len(filtered)} booking(s) shown.")
