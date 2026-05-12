import streamlit as st
from places_core.streamlit_auth import require_login

from places_ui_admin.api_client import (
    list_buildings,
    list_floors,
    list_sections,
    list_users_admin,
    update_user_admin,
)

st.set_page_config(page_title="Users — DeskMate Admin", layout="wide")
require_login()

st.title("User Management")
st.caption(
    "Browse all users and edit their home office location, Entra group type, "
    "and allocation preferences. When Microsoft Entra integration is enabled, "
    "department, job title, and office location are synced automatically on login."
)

# ── Load data ─────────────────────────────────────────────────────────────────

try:
    all_users = list_users_admin()
    buildings = list_buildings()
except Exception as exc:
    st.error(f"Could not load data. ({exc})")
    st.stop()

building_by_id = {b["id"]: b for b in buildings}

# ── Search / select ───────────────────────────────────────────────────────────

search = st.text_input("Search by name or email", placeholder="Start typing…")
filtered = (
    [u for u in all_users
     if search.lower() in u["display_name"].lower() or search.lower() in (u["email"] or "").lower()]
    if search else all_users
)

if not filtered:
    st.info("No users match your search.")
    st.stop()

filtered_sorted = sorted(filtered, key=lambda u: u["display_name"].lower())
options = {f"{u['display_name']}  ({u['email']})": u for u in filtered_sorted}
selected_label = st.selectbox("Select user", list(options.keys()), label_visibility="collapsed")
user = options[selected_label]
user_id = user["id"]

st.divider()

# ── Edit form ─────────────────────────────────────────────────────────────────

st.subheader(user["display_name"])

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### Identity")
    display_name = st.text_input("Display name", value=user.get("display_name") or "")
    department = st.text_input(
        "Department",
        value=user.get("department") or "",
        help="Synced from Entra on login when integration is enabled. Editable here as an override.",
    )
    role = st.text_input(
        "Job title / role",
        value=user.get("role") or "",
        help="Synced from Entra jobTitle on login when integration is enabled.",
    )
    emp_options = ["permanent", "contractor", "visitor"]
    emp_type = st.selectbox(
        "Employment type",
        emp_options,
        index=emp_options.index(user.get("employment_type") or "permanent"),
    )

with col_right:
    st.markdown("#### Entra & Allocation")
    entra_types = ["team", "lab", "platform", "exec", "external"]
    et_current = user.get("entra_team_type") or "team"
    entra_team_type = st.selectbox(
        "Entra group type",
        entra_types,
        index=entra_types.index(et_current) if et_current in entra_types else 0,
        help=(
            "Controls which allocation weight fires when clustering colleagues: "
            "team → w_same_team, lab → w_same_lab, platform → w_same_platform."
        ),
    )
    is_vip = st.toggle("VIP / Executive", value=user.get("is_vip") or False,
                       help="VIP users are allocated first and may only use exec-protected desks.")

    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    current_anchor = [d.capitalize() for d in (user.get("anchor_days") or [])]
    anchor_days = st.multiselect(
        "Anchor days",
        days_of_week,
        default=[d for d in current_anchor if d in days_of_week],
        help="Days the user is required to be in office. Affects escalation logic in the allocation engine.",
    )

# ── Home location ─────────────────────────────────────────────────────────────

st.markdown("#### Home Office Location")
st.caption(
    "Set where this user normally works. The allocation engine weights desks in their "
    "home section/floor/building using the w_home_neighbourhood score. "
    "When Entra integration is on, building is inferred from officeLocation on first login."
)

loc1, loc2, loc3 = st.columns(3)

with loc1:
    building_options = [None] + buildings
    building_idx = next(
        (i + 1 for i, b in enumerate(buildings) if b["id"] == user.get("home_building_id")), 0
    )
    selected_building = st.selectbox(
        "Building",
        building_options,
        index=building_idx,
        format_func=lambda b: "— None —" if b is None else b["name"],
    )

floors = list_floors(building_id=selected_building["id"]) if selected_building else []

with loc2:
    floor_options = [None] + floors
    floor_idx = next(
        (i + 1 for i, f in enumerate(floors) if f["id"] == user.get("home_floor_id")), 0
    )
    selected_floor = st.selectbox(
        "Floor",
        floor_options,
        index=floor_idx,
        format_func=lambda f: "— None —" if f is None else (f.get("name") or f"Floor {f['number']}"),
    )

sections = list_sections(floor_id=selected_floor["id"]) if selected_floor else []

with loc3:
    section_options = [None] + sections
    section_idx = next(
        (i + 1 for i, s in enumerate(sections) if s["id"] == user.get("home_section_id")), 0
    )
    selected_section = st.selectbox(
        "Section / neighbourhood",
        section_options,
        index=section_idx,
        format_func=lambda s: "— None —" if s is None else (s.get("zone_label") or s["name"]),
    )

# ── Save ──────────────────────────────────────────────────────────────────────

st.divider()

if st.button("Save Changes", type="primary"):
    payload = {
        "display_name": display_name or user["display_name"],
        "department": department or None,
        "role": role or None,
        "employment_type": emp_type,
        "entra_team_type": entra_team_type,
        "is_vip": is_vip,
        "anchor_days": [d.lower() for d in anchor_days],
        "home_building_id": selected_building["id"] if selected_building else None,
        "home_floor_id": selected_floor["id"] if selected_floor else None,
        "home_section_id": selected_section["id"] if selected_section else None,
    }
    try:
        update_user_admin(user_id, payload)
        st.success(f"Changes saved for {payload['display_name']}.")
    except Exception as exc:
        st.error(f"Save failed. ({exc})")
