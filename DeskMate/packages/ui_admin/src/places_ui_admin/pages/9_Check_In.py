from datetime import date, timedelta

import pandas as pd
import streamlit as st
from places_core.streamlit_auth import require_login

from places_ui_admin.api_client import (
    get_checkin_analytics,
    list_desks,
    list_users_admin,
    simulate_checkin,
)

st.set_page_config(page_title="Check-In — DeskMate Admin", layout="wide")
require_login()

st.title("Peripheral Check-In")
st.caption(
    "Monitor-based presence detection powered by Microsoft Places. When a user "
    "connects to a registered monitor, DeskMate checks them in automatically, "
    "reassigns wrong-desk situations, and sends Teams notifications for conflicts."
)

# ── Load analytics ────────────────────────────────────────────────────────────

try:
    data = get_checkin_analytics()
except Exception as exc:
    st.error(f"Could not load check-in data. ({exc})")
    st.stop()

total = data.get("total_events", 0)

# ── Summary metrics ───────────────────────────────────────────────────────────

st.subheader("Summary")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Events", total)
m2.metric("Checked In", f"{data.get('check_in_rate_pct', 0):.1f}%")
m3.metric("Reassigned", f"{data.get('reassignment_rate_pct', 0):.1f}%",
          help="User connected to a free desk that wasn't their assigned one — booking was moved.")
m4.metric("Conflicts", f"{data.get('conflict_rate_pct', 0):.1f}%",
          help="User connected to a desk booked by a different person — Teams alert sent.")
m5.metric("No Booking", f"{data.get('no_booking_rate_pct', 0):.1f}%",
          help="User connected to a monitor but had no booking for today.")

st.divider()

# ── Daily trend chart ─────────────────────────────────────────────────────────

daily = data.get("daily_by_outcome", {})
if daily:
    st.subheader("Daily Check-In Events by Outcome")
    rows = []
    for day, outcomes in daily.items():
        for outcome, count in outcomes.items():
            rows.append({"Date": day, "Outcome": outcome, "Count": count})
    df_daily = pd.DataFrame(rows)
    if not df_daily.empty:
        pivot = df_daily.pivot_table(index="Date", columns="Outcome", values="Count", fill_value=0).reset_index()
        st.bar_chart(pivot.set_index("Date"))
    st.divider()

# ── Outcome & method breakdown ────────────────────────────────────────────────

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Outcome Breakdown")
    outcomes = data.get("outcome_breakdown", {})
    if outcomes:
        df_out = pd.DataFrame(
            [{"Outcome": k, "Count": v} for k, v in outcomes.items()]
        )
        st.dataframe(df_out, use_container_width=True, hide_index=True)
    else:
        st.info("No data yet.")

with col_b:
    st.subheader("Method Breakdown")
    methods = data.get("method_breakdown", {})
    if methods:
        df_meth = pd.DataFrame(
            [{"Method": k, "Count": v} for k, v in methods.items()]
        )
        st.dataframe(df_meth, use_container_width=True, hide_index=True)
    else:
        st.info("No data yet.")

st.divider()

# ── Recent events ─────────────────────────────────────────────────────────────

st.subheader("Recent Events")
recent = data.get("recent_events", [])
if recent:
    df_recent = pd.DataFrame(recent)
    display_cols = ["checked_in_at", "user", "desk", "outcome", "method", "was_reassigned", "notification_sent"]
    df_recent = df_recent[[c for c in display_cols if c in df_recent.columns]]
    df_recent.columns = [c.replace("_", " ").title() for c in df_recent.columns]
    st.dataframe(df_recent, use_container_width=True, hide_index=True)
else:
    st.info("No check-in events recorded yet. Use the simulator below to test.")

st.divider()

# ── Demo simulation ───────────────────────────────────────────────────────────

st.subheader("Simulate Check-In")
st.caption(
    "Trigger the full check-in logic as if a user connected to a monitor — "
    "useful for demos and testing without a physical peripheral."
)

try:
    all_desks = list_desks()
    all_users = list_users_admin()
except Exception as exc:
    st.error(f"Could not load desk/user data. ({exc})")
    st.stop()

# Desks that have monitors registered
monitored_desks = [d for d in all_desks if d.get("id")]

sim_col1, sim_col2 = st.columns(2)

with sim_col1:
    sim_device_id = st.text_input(
        "Device ID to simulate",
        placeholder="MON-SERIAL-12345",
        help="Must match a device ID registered in the Peripheral Monitors tab of Desks & Rooms.",
    )

with sim_col2:
    user_options = {f"{u['display_name']} ({u['email']})": u for u in sorted(all_users, key=lambda u: u["display_name"])}
    selected_user_label = st.selectbox("User to simulate check-in for", list(user_options.keys()))

if st.button("Run Simulation", type="primary"):
    if not sim_device_id.strip():
        st.warning("Enter a device ID to simulate.")
    else:
        selected_user = user_options[selected_user_label]
        try:
            result = simulate_checkin(sim_device_id.strip(), selected_user["id"])
        except Exception as exc:
            st.error(f"Simulation failed. ({exc})")
            result = None

        if result:
            outcome = result.get("outcome")
            if outcome == "checked_in":
                st.success(f"Checked in at **{result.get('desk')}**.")
            elif outcome == "reassigned":
                st.warning(
                    f"Booking **reassigned** to {result.get('desk')} "
                    f"(was on a different desk). "
                    f"Teams notification: {'sent' if result.get('notification_sent') else 'not sent (demo mode)'}."
                )
            elif outcome == "conflict":
                st.error(
                    f"**Conflict** — {result.get('desk')} is booked by "
                    f"{result.get('booked_by', 'another user')}. "
                    f"Teams notification: {'sent' if result.get('notification_sent') else 'not sent (demo mode)'}."
                )
            elif outcome == "no_booking":
                st.warning(
                    f"No booking found for today at {result.get('desk')}. "
                    f"Teams notification: {'sent' if result.get('notification_sent') else 'not sent (demo mode)'}."
                )
            elif outcome == "error":
                st.error(f"Error: {result.get('reason')} — check the device ID is registered.")
