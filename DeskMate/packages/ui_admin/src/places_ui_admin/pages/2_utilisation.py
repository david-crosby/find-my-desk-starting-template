"""Workspace Utilisation — nightly batch metrics from the bookings database."""

import pandas as pd
import streamlit as st

from places_ui_admin.api_client import get_analytics_summary

st.set_page_config(page_title="Utilisation", layout="wide")
from places_core.streamlit_auth import require_login
require_login()
st.title("Workspace Utilisation")

try:
    data = get_analytics_summary()
except Exception as exc:
    st.error(f"Could not load analytics: {exc}")
    st.stop()

# ── KPI row ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Bookings", data["total_bookings"])
c2.metric("Active Desks", data["active_desks"])
c3.metric("No-show Rate (4-week rolling)", f"{data['rolling_4w_no_show_rate_pct']}%")
c4.metric("Cancellation Rate", f"{data['cancellation_rate_pct']}%")

st.divider()

# ── Daily trends ──────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Daily desk bookings (last 30 days)")
    daily_desk = data.get("daily_desk_bookings", {})
    if daily_desk:
        df_desk = pd.DataFrame(
            {"Date": list(daily_desk.keys()), "Bookings": list(daily_desk.values())}
        ).set_index("Date")
        st.bar_chart(df_desk)
    else:
        st.info("No desk booking data in the last 30 days.")

with col_right:
    st.subheader("Daily utilisation rate % (last 30 days)")
    util = data.get("daily_utilisation_pct", {})
    if util:
        df_util = pd.DataFrame(
            {"Date": list(util.keys()), "Utilisation %": list(util.values())}
        ).set_index("Date")
        st.line_chart(df_util)
    else:
        st.info("No utilisation data yet.")

st.divider()

# ── Booking source breakdown ──────────────────────────────────────────────────
st.subheader("Booking source breakdown")
source = data.get("source_breakdown", {})
if source:
    df_source = pd.DataFrame(
        {"Source": list(source.keys()), "Bookings": list(source.values())}
    ).set_index("Source")
    st.bar_chart(df_source)
else:
    st.info("No source data yet.")

st.divider()

# ── Status breakdown ──────────────────────────────────────────────────────────
st.subheader("Booking status breakdown")
status = data.get("status_breakdown", {})
if status:
    df_status = pd.DataFrame(
        {"Status": list(status.keys()), "Count": list(status.values())}
    ).set_index("Status")
    st.bar_chart(df_status)

st.divider()

# ── Real-time note ────────────────────────────────────────────────────────────
st.info(
    "**Real-time pipeline** (live floor heatmaps, sensor occupancy) requires "
    "Microsoft Graph workplace sensor integration. "
    "See `GET /workplace/sensorDevices` in the MS Graph API docs."
)
