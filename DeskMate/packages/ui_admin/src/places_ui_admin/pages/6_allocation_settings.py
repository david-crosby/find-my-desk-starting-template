import streamlit as st
from places_core.streamlit_auth import require_login

from places_ui_admin.api_client import (
    get_org_rules,
    get_weights,
    list_buildings,
    list_desks,
    list_floors,
    list_sections,
    toggle_desk_exec,
    toggle_section_restrict,
    update_org_rules,
    update_weights,
)

st.set_page_config(page_title="Allocation Settings — DeskMate Admin", layout="wide")
require_login()

st.title("Allocation Settings")
st.caption(
    "Hard rules are enforced regardless of weighting. "
    "Weights influence the overnight allocation engine — higher means greater priority."
)

# ── Load current config ───────────────────────────────────────────────────────

try:
    rules = get_org_rules()
    weights = get_weights()
except Exception as exc:
    st.error(f"Could not load allocation settings from backend. ({exc})")
    st.stop()

# ── Helper: convert internal float (0–50) to UI scale (0–10) ─────────────────

def _to_ui(v: float) -> float:
    return round(v / 5, 1)


def _to_internal(v: float) -> float:
    return round(v * 5, 1)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Hard rules
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("Hard Rules")
st.caption("These constraints are enforced before any weighting is applied.")

col_r1, col_r2, col_r3 = st.columns(3)

new_exec = col_r1.toggle(
    "VIP / Exec Desk Protection",
    value=rules.get("enforce_exec_protection", True),
    help="Desks marked as exec-protected are reserved exclusively for VIP and executive users.",
)
new_anchor = col_r2.toggle(
    "Anchor Day Enforcement",
    value=rules.get("enforce_anchor_days", True),
    help="Users with anchor days set must be allocated a desk on those days before others.",
)
new_restricted = col_r3.toggle(
    "Restricted Area Enforcement",
    value=rules.get("enforce_restricted_areas", True),
    help="Restricted sections are only accessible to authorised users regardless of availability.",
)

if st.button("Save Rules", key="save_rules"):
    try:
        update_org_rules({
            "enforce_exec_protection": new_exec,
            "enforce_anchor_days": new_anchor,
            "enforce_restricted_areas": new_restricted,
        })
        st.success("Rules saved.")
    except Exception as exc:
        st.error(f"Failed to save rules. ({exc})")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Auto-release / check-in cutoffs
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("Desk Auto-Release")
st.caption(
    "If a desk has not been checked into by the cutoff time, it is automatically "
    "released for others to use and the booking is marked as no-show. "
    "The check-in cutoff varies by booking type."
)

import datetime as _dt

enable_release = st.toggle(
    "Enable auto-release",
    value=rules.get("enable_auto_release", True),
    help="When off, desks are never automatically released — check-in data is still recorded.",
)

r1, r2, r3 = st.columns(3)

def _parse_time(t: str, default_h: int, default_m: int) -> _dt.time:
    try:
        h, m = map(int, t.split(":"))
        return _dt.time(h, m)
    except Exception:
        return _dt.time(default_h, default_m)

cutoff_allday = r1.time_input(
    "All-day booking cutoff",
    value=_parse_time(rules.get("checkin_cutoff_allday", "10:00"), 10, 0),
    help="Booking with no specific start time — user must check in before this time.",
)
cutoff_am = r2.time_input(
    "AM booking cutoff",
    value=_parse_time(rules.get("checkin_cutoff_am", "10:00"), 10, 0),
    help="Bookings starting before midday — user must check in before this time.",
)
cutoff_pm = r3.time_input(
    "PM booking cutoff",
    value=_parse_time(rules.get("checkin_cutoff_pm", "14:00"), 14, 0),
    help="Bookings starting at midday or later — user must check in before this time.",
)

if st.button("Save Release Settings", key="save_release"):
    try:
        update_org_rules({
            "enable_auto_release": enable_release,
            "checkin_cutoff_allday": cutoff_allday.strftime("%H:%M"),
            "checkin_cutoff_am": cutoff_am.strftime("%H:%M"),
            "checkin_cutoff_pm": cutoff_pm.strftime("%H:%M"),
        })
        st.success("Auto-release settings saved.")
    except Exception as exc:
        st.error(f"Failed to save settings. ({exc})")

st.divider()

# ── Restricted sections ───────────────────────────────────────────────────────

st.markdown("#### Restricted Sections")
st.caption("Toggle sections that should only be accessible to authorised personnel.")

try:
    buildings = list_buildings()
    bldg_map = {b["name"]: b["id"] for b in buildings}
    sel_bldg = st.selectbox("Building", list(bldg_map.keys()), key="restrict_bldg")

    floors = list_floors(building_id=bldg_map[sel_bldg])
    floor_map = {f.get("name") or f"Floor {f['number']}": f["id"] for f in floors}
    sel_floor = st.selectbox("Floor", list(floor_map.keys()), key="restrict_floor")

    sections = list_sections(floor_id=floor_map[sel_floor])

    if sections:
        for sec in sections:
            label = sec.get("zone_label") or sec["name"]
            current = sec.get("is_restricted", False)
            badge = "🔒 Restricted" if current else "Open"
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{label}** — {badge}")
            if c2.button("Toggle", key=f"sec_{sec['id']}"):
                try:
                    toggle_section_restrict(sec["id"])
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not update section. ({exc})")
    else:
        st.info("No sections found for this floor.")
except Exception as exc:
    st.warning(f"Could not load section data. ({exc})")

st.divider()

# ── Exec-protected desks ──────────────────────────────────────────────────────

st.markdown("#### Exec-Protected Desks")
st.caption("Mark individual desks as exec-only. Only users with VIP status will be allocated these desks.")

try:
    bldg_map2 = {b["name"]: b["id"] for b in buildings}
    sel_bldg2 = st.selectbox("Building", list(bldg_map2.keys()), key="exec_bldg")
    floors2 = list_floors(building_id=bldg_map2[sel_bldg2])
    floor_map2 = {f.get("name") or f"Floor {f['number']}": f["id"] for f in floors2}
    sel_floor2 = st.selectbox("Floor", list(floor_map2.keys()), key="exec_floor")

    desks = list_desks(floor_id=floor_map2[sel_floor2])

    if desks:
        exec_desks = [d for d in desks if d.get("is_exec_desk")]
        non_exec = [d for d in desks if not d.get("is_exec_desk")]

        if exec_desks:
            st.markdown(f"**{len(exec_desks)} exec-protected** on this floor:")
            for d in exec_desks:
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"🔐 **{d['label']}**")
                if c2.button("Remove", key=f"exec_{d['id']}"):
                    toggle_desk_exec(d["id"])
                    st.rerun()

        if non_exec:
            with st.expander(f"Add exec protection ({len(non_exec)} standard desks)"):
                for d in non_exec:
                    c1, c2 = st.columns([4, 1])
                    c1.write(d["label"])
                    if c2.button("Protect", key=f"nexec_{d['id']}"):
                        toggle_desk_exec(d["id"])
                        st.rerun()
    else:
        st.info("No desks found for this floor.")
except Exception as exc:
    st.warning(f"Could not load desk data. ({exc})")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Allocation weights
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("Allocation Weights")
st.caption(
    "Adjust the priority given to each factor during the overnight desk allocation. "
    "0 = ignored, 10 = maximum priority. Changes take effect at the next allocation run (23:00)."
)

with st.form("weights_form"):

    st.markdown("##### People Preferences")
    st.caption("How strongly the engine prioritises keeping team members together.")
    pc1, pc2, pc3, pc4 = st.columns(4)
    w_same_team     = pc1.slider("Team members",     0.0, 10.0, _to_ui(weights["w_same_team"]),     0.5)
    w_same_lab      = pc2.slider("Lab members",      0.0, 10.0, _to_ui(weights["w_same_lab"]),      0.5)
    w_same_platform = pc3.slider("Platform members", 0.0, 10.0, _to_ui(weights["w_same_platform"]), 0.5)
    w_follow        = pc4.slider("Other colleagues", 0.0, 10.0, _to_ui(weights["w_follow_colleague"]), 0.5)

    st.markdown("##### Environment")
    st.caption("Desk environment and proximity preferences.")
    ec1, ec2, ec3 = st.columns(3)
    ec4, ec5, ec6 = st.columns(3)
    w_ac      = ec1.slider("Heat / AC avoidance",  0.0, 10.0, _to_ui(weights["w_avoid_ac_penalty"]), 0.5)
    w_window  = ec2.slider("Window seat",          0.0, 10.0, _to_ui(weights["w_window"]),           0.5)
    w_noise   = ec3.slider("Noise match",          0.0, 10.0, _to_ui(weights["w_noise_match"]),      0.5)
    w_lift    = ec4.slider("Near lift",            0.0, 10.0, _to_ui(weights["w_near_lift"]),        0.5)
    w_exit    = ec5.slider("Near exit",            0.0, 10.0, _to_ui(weights["w_near_exit"]),        0.5)
    w_toilet  = ec6.slider("Near toilets",         0.0, 10.0, _to_ui(weights["w_near_toilets"]),     0.5)

    st.markdown("##### Equipment")
    st.caption("Hardware and workstation requirements.")
    eq1, eq2, eq3 = st.columns(3)
    w_monitors = eq1.slider("Number of screens",  0.0, 10.0, _to_ui(weights["w_monitor_match"]), 0.5)
    w_standing = eq2.slider("Sit / Stand desk",   0.0, 10.0, _to_ui(weights["w_standing_desk"]), 0.5)
    w_ultra    = eq3.slider("Ultrawide screen",   0.0, 10.0, _to_ui(weights["w_ultrawide"]),     0.5)

    st.markdown("##### Other Preferences")
    st.caption("Historical patterns and feedback signals.")
    op1, op2, op3, op4 = st.columns(4)
    w_home     = op1.slider("Home neighbourhood",       0.0, 10.0, _to_ui(weights["w_home_neighbourhood"]),       0.5)
    w_fav      = op2.slider("Historical desk",          0.0, 10.0, _to_ui(weights["w_favourite_desk"]),           0.5)
    w_recent   = op3.slider("Recently used desk",       0.0, 10.0, _to_ui(weights["w_recently_used"]),            0.5)
    w_feedback = op4.slider("Positive feedback bonus",  0.0, 10.0, _to_ui(weights["w_positive_feedback"]),        0.5)

    st.markdown("##### Negative Feedback Penalty")
    st.caption("Penalty applied to desks a user has rated poorly (≤2 stars).")
    w_penalty = st.slider("Poor feedback penalty", 0.0, 10.0, _to_ui(weights["w_negative_feedback_penalty"]), 0.5)

    submitted = st.form_submit_button("Save Weights", type="primary", use_container_width=True)

if submitted:
    try:
        update_weights({
            "w_same_team":               _to_internal(w_same_team),
            "w_same_lab":                _to_internal(w_same_lab),
            "w_same_platform":           _to_internal(w_same_platform),
            "w_follow_colleague":        _to_internal(w_follow),
            "w_avoid_ac_penalty":        _to_internal(w_ac),
            "w_window":                  _to_internal(w_window),
            "w_noise_match":             _to_internal(w_noise),
            "w_near_lift":               _to_internal(w_lift),
            "w_near_exit":               _to_internal(w_exit),
            "w_near_toilets":            _to_internal(w_toilet),
            "w_monitor_match":           _to_internal(w_monitors),
            "w_standing_desk":           _to_internal(w_standing),
            "w_ultrawide":               _to_internal(w_ultra),
            "w_home_neighbourhood":      _to_internal(w_home),
            "w_favourite_desk":          _to_internal(w_fav),
            "w_recently_used":           _to_internal(w_recent),
            "w_positive_feedback":       _to_internal(w_feedback),
            "w_negative_feedback_penalty": _to_internal(w_penalty),
        })
        st.success("Weights saved. Changes will apply at tonight's allocation run (23:00).")
    except Exception as exc:
        st.error(f"Failed to save weights. ({exc})")
