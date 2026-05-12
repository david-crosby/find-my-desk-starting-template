from datetime import date, timedelta

import streamlit as st
from places_core.streamlit_auth import require_login

from places_ui_admin.api_client import (
    get_org_rules,
    run_allocation,
    run_allocation_demo,
    update_org_rules,
)

st.set_page_config(page_title="Allocation Engine — DeskMate Admin", layout="wide")
require_login()

st.title("Allocation Engine")
st.caption(
    "Run the weighted desk allocation algorithm manually, simulate it with demo data, "
    "or configure the time it runs automatically each night."
)

# ── Load config ───────────────────────────────────────────────────────────────

try:
    rules = get_org_rules()
except Exception as exc:
    st.error(f"Could not load configuration. ({exc})")
    st.stop()


# ── Helper: render results table ──────────────────────────────────────────────

def _render_results(result: dict) -> None:
    stats = result.get("stats", {})
    details = result.get("details", [])
    run_date = result.get("date", "—")

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Date", run_date)
    col_b.metric("Allocated", stats.get("allocated", 0))
    col_c.metric("Failed", stats.get("failed", 0))
    col_d.metric("Escalated (anchor day unmet)", stats.get("escalated", 0))

    if not details:
        st.info("No allocation details to show.")
        return

    st.markdown("#### Per-booking results")

    for row in sorted(details, key=lambda r: r.get("match_pct") or 0, reverse=True):
        status = row.get("status", "unknown")
        match_pct = row.get("match_pct") or 0.0
        score = row.get("score") or 0.0
        desk = row.get("desk_label") or "—"
        section = row.get("section") or "—"
        floor_name = row.get("floor") or "—"
        building = row.get("building") or "—"
        user = row.get("user_name", "Unknown")
        vip = row.get("is_vip", False)
        anchor = row.get("is_anchor_day", False)
        notes = row.get("notes") or ""
        source = row.get("booking_source") or ""

        if status == "allocated":
            bar_color = "green" if match_pct >= 70 else "orange" if match_pct >= 40 else "red"
            icon = "✅"
        elif notes == "anchor_day_unmet":
            bar_color = "red"
            icon = "⚠️"
        else:
            bar_color = "red"
            icon = "❌"

        tags = []
        if vip:
            tags.append("VIP")
        if anchor:
            tags.append("Anchor Day")
        if source == "demo":
            tags.append("Demo")
        tag_str = "  `" + "`  `".join(tags) + "`" if tags else ""

        with st.container(border=True):
            h1, h2 = st.columns([3, 1])
            with h1:
                st.markdown(f"{icon} **{user}**{tag_str}")
                if status == "allocated":
                    st.markdown(
                        f"**{desk}** — {section}, {floor_name}, {building}"
                    )
                else:
                    st.markdown(f"_No desk allocated_ — {notes or 'no eligible desk found'}")
            with h2:
                if status == "allocated":
                    st.metric("Match", f"{match_pct:.0f}%")
                    st.progress(int(match_pct))
                else:
                    st.metric("Match", "—")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Nightly schedule
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("Nightly Schedule")

current_time_str = rules.get("allocation_run_time", "23:00")
try:
    h, m = map(int, current_time_str.split(":"))
except ValueError:
    h, m = 23, 0

import datetime as _dt
new_time = st.time_input(
    "Run allocation at",
    value=_dt.time(h, m),
    help="The allocation engine runs automatically each night at this time, processing all queued bookings for the following day.",
)

if st.button("Save Schedule"):
    try:
        update_org_rules({"allocation_run_time": new_time.strftime("%H:%M")})
        st.success(f"Schedule saved — allocation will run at {new_time.strftime('%H:%M')} each night.")
    except Exception as exc:
        st.error(f"Could not save schedule. ({exc})")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Manual run
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("Run Now")
st.caption(
    "Process all queued bookings with no desk assigned for a given date. "
    "This is the same routine that runs automatically each night."
)

tomorrow = date.today() + timedelta(days=1)
run_date = st.date_input("Date to allocate", value=tomorrow, key="run_date")

if st.button("Run Allocation Now", type="primary"):
    with st.spinner(f"Running allocation for {run_date.isoformat()}…"):
        try:
            result = run_allocation(target_date=run_date.isoformat())
        except Exception as exc:
            st.error(f"Allocation failed. ({exc})")
            st.stop()

    queued = result.get("queued_before", 0)
    if queued == 0:
        st.info(f"No queued bookings found for {run_date.isoformat()}. Nothing to allocate.")
    else:
        st.success(f"Allocation complete for {run_date.isoformat()}.")
        _render_results(result)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Demo simulation
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("Demo Simulation")
st.caption(
    "Populate the system with synthetic queued bookings for a selected date, "
    "then run the full allocation engine and watch it assign desks in real time. "
    "Demo bookings are kept in the database and appear in analytics."
)

demo_col1, demo_col2 = st.columns(2)
demo_date = demo_col1.date_input(
    "Simulation date",
    value=date.today() + timedelta(days=30),
    min_value=date.today() + timedelta(days=1),
    key="demo_date",
    help="Choose a future date. Dates with many existing bookings will have fewer available users to simulate.",
)
num_users = demo_col2.slider(
    "Number of users to simulate",
    min_value=2,
    max_value=30,
    value=10,
    step=1,
)

st.markdown(
    f"Will select **{num_users}** random users who have no existing booking on "
    f"**{demo_date.isoformat()}**, create queued desk bookings for them, "
    "then run the full weighted allocation engine."
)

if st.button("Run Demo Simulation", type="primary", key="run_demo"):
    steps = [
        "Selecting random users…",
        "Creating queued bookings…",
        "Running pre-filter (hard rules: exec protection, restricted areas)…",
        "Scoring desks (people prefs, environment, equipment, historical)…",
        "Assigning desks — VIPs first, then anchor-day bookings, then general…",
        "Recording allocation results…",
        "Done.",
    ]

    with st.status("Running allocation simulation…", expanded=True) as status_box:
        import time as _time

        result = None
        error = None

        for i, step in enumerate(steps[:-1]):
            st.write(step)
            _time.sleep(0.6)

        try:
            result = run_allocation_demo(
                target_date=demo_date.isoformat(),
                num_users=num_users,
            )
        except Exception as exc:
            error = exc

        st.write(steps[-1])
        if error:
            status_box.update(label="Simulation failed.", state="error", expanded=True)
        else:
            status_box.update(label="Simulation complete.", state="complete", expanded=False)

    if error:
        st.error(f"Demo failed. ({error})")
    else:
        simulated = result.get("simulated_users", num_users)
        st.success(
            f"Simulated {simulated} users on {demo_date.isoformat()}. "
            "Results below — scroll down to see every allocation decision."
        )
        _render_results(result)
