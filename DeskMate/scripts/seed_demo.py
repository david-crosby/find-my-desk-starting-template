#!/usr/bin/env python3
"""Seed the database from data/users.json plus generated spatial and booking data."""
import json
import random
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
for _pkg in ("core", "backend", "agent"):
    _src = _ROOT / "packages" / _pkg / "src"
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from places_core.db import SessionLocal
from places_core.models import (
    AgentSession,
    Booking,
    BookingPolicy,
    Building,
    Desk,
    Floor,
    Room,
    Section,
    User,
)

USERS_JSON = Path(__file__).parent.parent / "data" / "users.json"

SECTION_NAMES = ["Window Bank", "Quiet Zone", "Collaboration Zone", "Core Desk Area"]

# Per-section desk amenity profiles
SECTION_DESK_PROFILES = {
    "Window Bank": {
        "is_window_seat": True,
        "has_standing_desk": False,
        "has_dual_monitors": False,
        "has_docking_station": True,
        "is_accessible": False,
    },
    "Quiet Zone": {
        "is_window_seat": False,
        "has_standing_desk": True,
        "has_dual_monitors": True,
        "has_docking_station": True,
        "is_accessible": False,
    },
    "Collaboration Zone": {
        "is_window_seat": False,
        "has_standing_desk": False,
        "has_dual_monitors": True,
        "has_docking_station": True,
        "is_accessible": False,
    },
    "Core Desk Area": {
        "is_window_seat": False,
        "has_standing_desk": False,
        "has_dual_monitors": False,
        "has_docking_station": False,
        "is_accessible": False,
    },
}

BUILDING_COORDS = {
    "London": ("51.5074", "-0.1278"),
    "Leeds": ("53.8008", "-1.5491"),
    "Edinburgh": ("55.9533", "-3.1883"),
}

BUILDING_ADDRESSES = {
    "London": "1 Canada Square, Canary Wharf, London E14 5AB",
    "Leeds": "1 Whitehall Road, Leeds LS1 4HR",
    "Edinburgh": "1 Festival Square, Edinburgh EH3 9SR",
}


def parse_desk_prefs(prefs: list[str]) -> dict:
    flags = {
        "requires_standing_desk": False,
        "prefers_window_seat": False,
        "dual_monitor_required": False,
        "docking_station_required": False,
        "accessible_desk_preferred": False,
        "near_team_preferred": False,
        "preferred_noise_level": "no_preference",
    }
    for p in prefs:
        if p == "standing-desk":
            flags["requires_standing_desk"] = True
        elif p == "window-seat":
            flags["prefers_window_seat"] = True
        elif p == "dual-monitor":
            flags["dual_monitor_required"] = True
        elif p == "docking-station":
            flags["docking_station_required"] = True
        elif p == "accessible-desk":
            flags["accessible_desk_preferred"] = True
        elif p == "near-team":
            flags["near_team_preferred"] = True
        elif p == "quiet-area":
            flags["preferred_noise_level"] = "quiet"
    return flags


def make_desks(section: Section, prefix: str, count: int, amenities: dict) -> list[Desk]:
    desks = []
    for i in range(1, count + 1):
        overrides = {}
        if i % 5 == 0:
            overrides["is_accessible"] = True
        if i % 3 == 0 and not amenities.get("has_standing_desk"):
            overrides["has_standing_desk"] = True
        if i % 4 == 0 and not amenities.get("has_dual_monitors"):
            overrides["has_dual_monitors"] = True
        desks.append(
            Desk(
                section=section,
                label=f"{prefix}{i:02d}",
                is_active=True,
                desk_mode="reservable",
                coord_x=i * 120,
                coord_y=section.id * 80 if section.id else 80,
                **{**amenities, **overrides},
            )
        )
    return desks


def _clear(db) -> None:
    """Delete all rows in dependency order so FK constraints are not violated."""
    db.query(AgentSession).delete()
    db.query(Booking).delete()
    db.query(User).delete()
    db.query(Desk).delete()
    db.query(Room).delete()
    db.query(Section).delete()
    db.query(Floor).delete()
    db.query(Building).delete()
    db.query(BookingPolicy).delete()
    db.commit()
    print("Existing data cleared.")


def seed():
    random.seed(42)
    db = SessionLocal()
    try:
        _clear(db)

        # --- Default booking policy ---
        default_policy = BookingPolicy(
            name="Standard",
            max_advance_days=30,
            max_booking_duration_hours=9,
            auto_release_enabled=True,
            auto_release_threshold_mins=30,
            check_in_required=True,
            approval_required=False,
            gdpr_data_retention_days=365,
        )
        exec_policy = BookingPolicy(
            name="Executive Floor",
            max_advance_days=60,
            max_booking_duration_hours=9,
            auto_release_enabled=False,
            auto_release_threshold_mins=60,
            check_in_required=True,
            approval_required=True,
            gdpr_data_retention_days=730,
        )
        db.add_all([default_policy, exec_policy])
        db.flush()

        # --- Buildings, floors, sections, desks, rooms ---
        buildings: dict[str, Building] = {}
        # floor[building_name][floor_number] → Floor
        floors: dict[str, dict[int, Floor]] = {}
        # section[building_name][floor_number][section_name] → Section
        sections: dict[str, dict[int, dict[str, Section]]] = {}

        for location_name, (lat, lng) in BUILDING_COORDS.items():
            bldg = Building(
                name=location_name,
                address=BUILDING_ADDRESSES[location_name],
                building_lat=lat,
                building_lng=lng,
            )
            db.add(bldg)
            db.flush()
            buildings[location_name] = bldg
            floors[location_name] = {}
            sections[location_name] = {}

            for floor_num, floor_name in [(0, "Ground"), (1, "First")]:
                fl = Floor(building=bldg, number=floor_num, name=floor_name)
                db.add(fl)
                db.flush()
                floors[location_name][floor_num] = fl
                sections[location_name][floor_num] = {}

                desk_counter = {"n": 0}

                for sname in SECTION_NAMES:
                    sec = Section(floor=fl, name=sname, zone_label=sname)
                    db.add(sec)
                    db.flush()
                    sections[location_name][floor_num][sname] = sec

                    amenities = SECTION_DESK_PROFILES[sname]
                    # prefix: location initial + floor initial + section initial
                    prefix = (
                        f"{location_name[0]}"
                        f"{floor_name[0]}"
                        f"{sname[0]}-"
                    )
                    desk_count = 8 if sname == "Core Desk Area" else 5
                    new_desks = make_desks(sec, prefix, desk_count, amenities)
                    db.add_all(new_desks)

                # Meeting rooms on this floor
                room_configs = [
                    (f"Boardroom {floor_name}", 12),
                    (f"Huddle {floor_name} A", 4),
                    (f"Meeting Room {floor_name} 1", 8),
                ]
                for rname, cap in room_configs:
                    db.add(Room(floor=fl, name=rname, capacity=cap, is_active=True))

        db.flush()

        # --- Users from JSON ---
        raw_users = json.loads(USERS_JSON.read_text())

        # Build a lookup: email → user row (for line manager resolution)
        user_email_map: dict[str, User] = {}

        for u in raw_users:
            bldg = buildings.get(u["location"])
            home_floor = floors.get(u["location"], {}).get(0)  # default ground floor
            neighbourhood = u.get("preferredNeighbourhood")
            home_sec = None
            if home_floor and neighbourhood:
                home_sec = sections.get(u["location"], {}).get(0, {}).get(neighbourhood)

            prefs = parse_desk_prefs(u.get("deskPreferences") or [])
            accessibility = u.get("accessibilityNeeds")
            if accessibility == "ergonomic-chair":
                prefs["ergonomic_chair_required"] = True

            user_obj = User(
                entra_id=u["id"],
                employee_id=u["employeeId"],
                email=u["email"],
                display_name=u["fullName"],
                is_admin=False,
                team=u.get("team"),
                primary_team_id=u.get("team"),
                role=u.get("role"),
                employment_type="permanent",
                home_building=bldg,
                home_floor=home_floor,
                home_section=home_sec,
                preferred_neighbourhood=neighbourhood,
                default_working_pattern=u.get("defaultWorkingPattern"),
                anchor_days=u.get("anchorDays"),
                team_anchor_days=u.get("anchorDays"),
                booking_window_days=u.get("bookingWindowDays", 14),
                line_manager_email=u.get("lineManager", {}).get("email"),
                workplan_visibility="team",
                onboarding_completed=True,
                **prefs,
            )
            db.add(user_obj)
            db.flush()
            user_email_map[user_obj.email] = user_obj

        # Resolve line_manager_id now that all users exist
        for user_obj in user_email_map.values():
            if user_obj.line_manager_email:
                mgr = user_email_map.get(user_obj.line_manager_email)
                if mgr:
                    user_obj.line_manager_id = mgr.id

        db.flush()

        # --- Admin user ---
        admin = User(
            email="admin@thebank.com",
            display_name="Facilities Admin",
            is_admin=True,
            employment_type="permanent",
            home_building=buildings["London"],
            onboarding_completed=True,
        )
        db.add(admin)
        db.flush()

        # --- Sample bookings ---
        all_users = list(user_email_map.values())
        all_desks = db.query(Desk).filter(Desk.is_active == True).all()  # noqa: E712

        sample_dates = ["2026-05-11", "2026-05-12", "2026-05-13", "2026-05-14", "2026-05-15"]
        for date in sample_dates:
            booked_desks: set[int] = set()
            # Book roughly 40% of desks per day
            desk_pool = random.sample(all_desks, k=min(len(all_desks) // 2, 40))
            for desk in desk_pool:
                if desk.id in booked_desks:
                    continue
                user = random.choice(all_users)
                db.add(
                    Booking(
                        user=user,
                        desk=desk,
                        date=date,
                        start_time="09:00",
                        end_time="18:00",
                        status="confirmed",
                        booking_source=random.choice(["web_app", "agent_ai", "teams_tab"]),
                        approval_status="not_required",
                    )
                )
                booked_desks.add(desk.id)

        # --- Sample agent sessions ---
        intents = ["book", "amend", "cancel", "query", "recurring", "advisory"]
        for i, user_obj in enumerate(all_users[:10]):
            db.add(
                AgentSession(
                    user=user_obj,
                    session_id=f"demo-session-{i+1:03d}",
                    utterance_raw="Book me a desk near my team tomorrow",
                    intent_classified="book",
                    slots_extracted={"when": "2026-05-12", "where": "near_team"},
                    slots_inferred={"building": user_obj.home_building.name if user_obj.home_building else None},
                    slots_missing=[],
                    clarification_turns=0,
                    confidence_score=92,
                    user_accepted_rank=1,
                    fallback_triggered=False,
                    model_version="claude-sonnet-4-6",
                )
            )

        db.commit()
        print("Demo data loaded successfully.")
        print(f"  Buildings : {db.query(Building).count()}")
        print(f"  Floors    : {db.query(Floor).count()}")
        print(f"  Sections  : {db.query(Section).count()}")
        print(f"  Desks     : {db.query(Desk).count()}")
        print(f"  Rooms     : {db.query(Room).count()}")
        print(f"  Users     : {db.query(User).count()}")
        print(f"  Bookings  : {db.query(Booking).count()}")
        print(f"  AgentSess : {db.query(AgentSession).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
