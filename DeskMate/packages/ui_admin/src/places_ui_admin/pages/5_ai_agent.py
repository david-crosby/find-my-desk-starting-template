"""AI Agent Performance — first-suggestion acceptance, clarification turns, fallback rate."""

import pandas as pd
import streamlit as st

from places_ui_admin.api_client import get_agent_analytics

st.set_page_config(page_title="AI Agent Performance", layout="wide")
st.title("AI Agent Performance")
st.caption("Metrics from the DeskMate agent session log.")

try:
    data = get_agent_analytics()
except Exception as exc:
    st.error(f"Could not load agent analytics: {exc}")
    st.stop()

if data.get("total_sessions", 0) == 0:
    st.info("No agent sessions recorded yet. Start a conversation in the User UI.")
    st.stop()

# ── KPI row ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Sessions", data["total_sessions"])

acceptance = data.get("first_suggestion_acceptance_rate_pct")
c2.metric(
    "First-pick Acceptance Rate",
    f"{acceptance}%" if acceptance is not None else "Insufficient data",
)

c3.metric("Avg Clarification Turns", data.get("avg_clarification_turns", "—"))
c4.metric("Fallback Rate", f"{data.get('fallback_rate_pct', '—')}%")

st.divider()

# ── Intent breakdown ──────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Intent breakdown")
    intent = data.get("intent_breakdown", {})
    if intent:
        df_intent = pd.DataFrame(
            {"Intent": list(intent.keys()), "Sessions": list(intent.values())}
        ).set_index("Intent")
        st.bar_chart(df_intent)
    else:
        st.info("No intent data recorded yet.")

with col_right:
    st.subheader("Key metrics summary")
    rows = [
        ("Total sessions", data["total_sessions"]),
        ("Sessions with feedback", data.get("sessions_with_feedback", 0)),
        ("Avg confidence score", data.get("avg_confidence_score", "—")),
        ("First-pick acceptance", f"{acceptance}%" if acceptance is not None else "—"),
        ("Avg clarification turns", data.get("avg_clarification_turns", "—")),
        ("Fallback rate", f"{data.get('fallback_rate_pct', '—')}%"),
    ]
    df_summary = pd.DataFrame(rows, columns=["Metric", "Value"])
    st.dataframe(df_summary, use_container_width=True, hide_index=True)

st.divider()
st.info(
    "**Target benchmarks** — First-pick acceptance: >70% | "
    "Avg clarification turns: <1.5 | Fallback rate: <5%"
)
