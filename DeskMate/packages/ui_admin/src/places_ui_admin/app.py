import httpx
import streamlit as st
from places_core.streamlit_auth import logout, require_login

st.set_page_config(page_title="DeskMate Admin", page_icon="⚙️", layout="wide")

require_login()

with st.sidebar:
    auth_name = st.session_state.get("auth_name", "Admin")
    auth_email = st.session_state.get("auth_email", "")
    st.markdown(f"**{auth_name}**")
    if auth_email:
        st.caption(auth_email)
    if st.button("Sign out", use_container_width=True):
        logout()

st.title("DeskMate — Management Dashboard")
st.caption("Workspace utilisation, booking behaviour, and AI agent performance.")

try:
    from places_ui_admin.api_client import get_analytics_summary, get_agent_analytics

    summary = get_analytics_summary()
    agent = get_agent_analytics()
except httpx.HTTPStatusError as exc:
    if exc.response.status_code == 401:
        st.warning("Not signed in — complete the Microsoft sign-in flow to access the dashboard.")
    elif exc.response.status_code == 403:
        st.error(
            "Access denied — your account needs the **DeskMate Admin** role. "
            "Ask your Azure admin to assign it via Enterprise Applications → DeskMate → Users and groups."
        )
    else:
        st.error(f"Backend returned an unexpected error ({exc.response.status_code}).")
    st.stop()
except httpx.RequestError:
    st.warning("Backend not reachable. Start the API server on port 8000.")
    st.stop()

# ── Row 1: Workspace utilisation ─────────────────────────────────────────────
st.subheader("Workspace Utilisation")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Bookings", summary.get("total_bookings", "—"))
c2.metric("Active Desks", summary.get("active_desks", "—"))
c3.metric(
    "No-show Rate (4-week rolling)",
    f"{summary.get('rolling_4w_no_show_rate_pct', '—')}%",
)
c4.metric(
    "Cancellation Rate",
    f"{summary.get('cancellation_rate_pct', '—')}%",
)

# ── Row 2: Booking behaviour ──────────────────────────────────────────────────
st.subheader("Booking Behaviour")
b1, b2, b3, b4 = st.columns(4)

status = summary.get("status_breakdown", {})
source = summary.get("source_breakdown", {})

b1.metric("Confirmed / Allocated", status.get("confirmed", 0) + status.get("allocated", 0))
b2.metric("Agent AI Bookings", source.get("agent_ai", 0))
b3.metric("Avg Advance Booking Days", summary.get("avg_advance_booking_days", "—"))
b4.metric("Completed Visits", status.get("completed", 0))

# ── Row 3: AI agent performance ───────────────────────────────────────────────
st.subheader("AI Agent Performance")
a1, a2, a3, a4 = st.columns(4)
a1.metric("Total Agent Sessions", agent.get("total_sessions", "—"))
a2.metric(
    "First-pick Acceptance",
    f"{agent.get('first_suggestion_acceptance_rate_pct', '—')}%"
    if agent.get("first_suggestion_acceptance_rate_pct") is not None else "—",
)
a3.metric(
    "Avg Clarification Turns",
    agent.get("avg_clarification_turns", "—"),
)
a4.metric(
    "Fallback Rate",
    f"{agent.get('fallback_rate_pct', '—')}%",
)

st.divider()
st.caption(
    "Use the sidebar to drill into Utilisation, Bookings, Desks & Rooms, or AI Agent metrics. "
    + summary.get("note_realtime", "")
)
