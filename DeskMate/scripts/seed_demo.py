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

from places_core.db import SessionLocal, engine
from places_core.models import Base
from places_core.models import (
    AgentSession,
    Allocation,
    AllocationWeights,
    Booking,
    BookingPolicy,
    Building,
    Desk,
    Feedback,
    Floor,
    OrgRules,
    Room,
    Section,
    User,
)

USERS_JSON = Path(__file__).parent.parent / "data" / "users.json"

SECTION_NAMES = ["Window Bank", "Quiet Zone", "Collaboration Zone", "Core Desk Area"]
# Added to London buildings only — restricted access
LONDON_EXTRA_SECTIONS = ["Executive Suite", "Secure Zone"]

# Baseline amenity profile per section — seed will add per-desk variation
SECTION_DESK_PROFILES = {
    "Window Bank": {
        "is_window_seat": True,
        "has_standing_desk": False,
        "num_monitors": 1,
        "has_docking_station": True,
        "is_accessible": False,
        "noise_level_rating": 2.5,
    },
    "Quiet Zone": {
        "is_window_seat": False,
        "has_standing_desk": True,
        "num_monitors": 2,
        "has_docking_station": True,
        "is_accessible": False,
        "noise_level_rating": 1.5,
    },
    "Collaboration Zone": {
        "is_window_seat": False,
        "has_standing_desk": False,
        "num_monitors": 2,
        "has_docking_station": True,
        "is_accessible": False,
        "noise_level_rating": 3.5,
    },
    "Core Desk Area": {
        "is_window_seat": False,
        "has_standing_desk": False,
        "num_monitors": 1,
        "has_docking_station": False,
        "is_accessible": False,
        "noise_level_rating": 3.0,
    },
    "Executive Suite": {
        "is_window_seat": True,
        "has_standing_desk": True,
        "num_monitors": 2,
        "has_docking_station": True,
        "is_accessible": True,
        "noise_level_rating": 1.8,
        "is_exec_desk": True,
    },
    "Secure Zone": {
        "is_window_seat": False,
        "has_standing_desk": False,
        "num_monitors": 2,
        "has_docking_station": True,
        "is_accessible": False,
        "noise_level_rating": 2.0,
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

# Proximity layout: for a section of N desks, which desk indices (1-based) are near each facility
PROXIMITY_PATTERNS = {
    "near_lift": lambda i, n: i <= max(1, n // 4),
    "near_exit": lambda i, n: i >= n - max(0, n // 4) + 1,
    "near_toilets": lambda i, n: (n // 2) <= i <= (n // 2) + 1,
    "near_ac_unit": lambda i, n: i % 4 == 0,
}


def parse_desk_prefs(prefs: list[str], monitor_pref: int = 1) -> dict:
    flags = {
        "requires_standing_desk": False,
        "prefers_window_seat": False,
        "preferred_monitors": monitor_pref,
        "prefers_ultrawide": False,
        "docking_station_required": False,
        "accessible_desk_preferred": False,
        "near_team_preferred": False,
        "preferred_noise_level": "no_preference",
        "prefers_near_lift": False,
        "prefers_near_exit": False,
        "prefers_near_toilets": False,
        "avoids_ac": False,
    }
    for p in prefs:
        if p == "standing-desk":
            flags["requires_standing_desk"] = True
        elif p == "window-seat":
            flags["prefers_window_seat"] = True
        elif p == "ultrawide":
            flags["prefers_ultrawide"] = True
        elif p == "docking-station":
            flags["docking_station_required"] = True
        elif p == "accessible-desk":
            flags["accessible_desk_preferred"] = True
        elif p == "near-team":
            flags["near_team_preferred"] = True
        elif p == "quiet-area":
            flags["preferred_noise_level"] = "quiet"
        elif p == "near-lift":
            flags["prefers_near_lift"] = True
        elif p == "near-exit":
            flags["prefers_near_exit"] = True
        elif p == "near-toilets":
            flags["prefers_near_toilets"] = True
        elif p == "avoid-ac":
            flags["avoids_ac"] = True
    return flags


def make_desks(section: Section, prefix: str, count: int, amenities: dict) -> list[Desk]:
    desks = []
    base_noise = amenities.get("noise_level_rating", 3.0)
    is_exec = amenities.get("is_exec_desk", False)

    for i in range(1, count + 1):
        overrides: dict = {}

        # Accessibility: every 5th desk
        if i % 5 == 0:
            overrides["is_accessible"] = True

        # Occasional extra standing desks in non-standing sections
        if i % 3 == 0 and not amenities.get("has_standing_desk"):
            overrides["has_standing_desk"] = True

        # Some desks get extra monitors (e.g. 3 monitors for power users)
        if i % 6 == 0 and amenities.get("num_monitors", 1) >= 2:
            overrides["num_monitors"] = 3

        # A few desks get ultrawide screens
        if i % 7 == 0:
            overrides["has_ultrawide"] = True

        # Per-desk proximity to facilities
        n = count
        overrides["near_lift"] = PROXIMITY_PATTERNS["near_lift"](i, n)
        overrides["near_exit"] = PROXIMITY_PATTERNS["near_exit"](i, n)
        overrides["near_toilets"] = PROXIMITY_PATTERNS["near_toilets"](i, n)
        overrides["near_ac_unit"] = PROXIMITY_PATTERNS["near_ac_unit"](i, n)

        # Per-desk noise variance ± 0.5 from section baseline
        noise_variance = random.uniform(-0.5, 0.5)
        desk_noise = round(max(1.0, min(5.0, base_noise + noise_variance)), 1)

        # Email address for MS Places integration
        desk_email = f"{prefix.lower().replace('-', '')}{i:02d}@desks.thebank.com"

        desks.append(
            Desk(
                section=section,
                label=f"{prefix}{i:02d}",
                is_active=True,
                desk_mode="reservable",
                is_exec_desk=is_exec,
                noise_level_rating=desk_noise,
                coord_x=i * 120,
                coord_y=section.id * 80 if section.id else 80,
                desk_email_address=desk_email,
                **{
                    k: v for k, v in amenities.items()
                    if k not in ("noise_level_rating", "is_exec_desk") and k not in overrides
                },
                **overrides,
            )
        )
    return desks


def _clear(db) -> None:
    db.query(Feedback).delete()
    db.query(Allocation).delete()
    db.query(AgentSession).delete()
    db.query(Booking).delete()
    db.query(User).delete()
    db.query(Desk).delete()
    db.query(Room).delete()
    db.query(Section).delete()
    db.query(Floor).delete()
    db.query(Building).delete()
    db.query(BookingPolicy).delete()
    db.query(AllocationWeights).delete()
    db.query(OrgRules).delete()
    db.commit()
    print("Existing data cleared.")


def seed():
    random.seed(42)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        _clear(db)

        # --- Booking policies ---
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

        # --- Default allocation weights ---
        db.add(AllocationWeights(
            name="Default",
            is_active=True,
        ))
        db.add(OrgRules(id=1))
        db.flush()

        # --- Buildings, floors, sections, desks, rooms ---
        buildings: dict[str, Building] = {}
        floors: dict[str, dict[int, Floor]] = {}
        # sections[building_name][floor_number][section_name] → Section
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

                section_list = list(SECTION_NAMES)
                # Executive Suite and Secure Zone only in London
                if location_name == "London":
                    section_list += LONDON_EXTRA_SECTIONS

                for sname in section_list:
                    is_restricted = sname in LONDON_EXTRA_SECTIONS
                    sec = Section(
                        floor=fl,
                        name=sname,
                        zone_label=sname,
                        is_restricted=is_restricted,
                    )
                    db.add(sec)
                    db.flush()
                    sections[location_name][floor_num][sname] = sec

                    amenities = SECTION_DESK_PROFILES[sname]
                    prefix = f"{location_name[0]}{floor_name[0]}{sname[0]}-"
                    desk_count = 4 if sname in LONDON_EXTRA_SECTIONS else (8 if sname == "Core Desk Area" else 5)
                    new_desks = make_desks(sec, prefix, desk_count, amenities)
                    db.add_all(new_desks)

                # Meeting rooms
                for rname, cap in [
                    (f"Boardroom {floor_name}", 12),
                    (f"Huddle {floor_name} A", 4),
                    (f"Meeting Room {floor_name} 1", 8),
                ]:
                    db.add(Room(floor=fl, name=rname, capacity=cap, is_active=True))

        db.flush()

        # Build a flat section name→id lookup for each London floor (for restricted_section_ids)
        london_section_name_to_ids: dict[str, list[int]] = {}
        for floor_num in sections.get("London", {}):
            for sname, sec in sections["London"][floor_num].items():
                london_section_name_to_ids.setdefault(sname, []).append(sec.id)

        # --- Users from JSON ---
        raw_users = json.loads(USERS_JSON.read_text())
        user_email_map: dict[str, User] = {}

        for u in raw_users:
            bldg = buildings.get(u["location"])
            home_floor = floors.get(u["location"], {}).get(0)
            neighbourhood = u.get("preferredNeighbourhood")
            home_sec = None
            if home_floor and neighbourhood:
                home_sec = sections.get(u["location"], {}).get(0, {}).get(neighbourhood)

            prefs = parse_desk_prefs(
                u.get("deskPreferences") or [],
                u.get("monitorPreference", 1),
            )
            accessibility = u.get("accessibilityNeeds")
            if accessibility == "ergonomic-chair":
                prefs["ergonomic_chair_required"] = True

            # Resolve restricted_section_ids from zone names in JSON
            restricted_zones = u.get("restrictedZones") or []
            restricted_ids: list[int] = []
            for zone_name in restricted_zones:
                restricted_ids.extend(london_section_name_to_ids.get(zone_name, []))

            user_obj = User(
                entra_id=u["id"],
                employee_id=u["employeeId"],
                email=u["email"],
                display_name=u["fullName"],
                is_admin=False,
                team=u.get("team"),
                primary_team_id=u.get("team"),
                entra_team_type=u.get("teamType", "team"),
                is_vip=u.get("isVip", False),
                restricted_section_ids=restricted_ids if restricted_ids else None,
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
                line_manager_email=(u.get("lineManager") or {}).get("email"),
                follow_colleagues=u.get("followColleagues") or [],
                workplan_visibility="team",
                onboarding_completed=True,
                **prefs,
            )
            db.add(user_obj)
            db.flush()
            user_email_map[user_obj.email] = user_obj

        # Resolve line_manager_id
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
            entra_team_type="team",
        )
        db.add(admin)
        db.flush()

        # Update line managers that reference admin@thebank.com
        for user_obj in user_email_map.values():
            if user_obj.line_manager_email == "admin@thebank.com":
                user_obj.line_manager_id = admin.id

        db.flush()

        # --- Populate recently_used_desk_ids and favourite_desk_ids ---
        all_users_list = list(user_email_map.values())
        all_desks = db.query(Desk).filter(Desk.is_active == True).all()  # noqa: E712

        # Only regular (non-exec, non-restricted) desks for general users
        regular_desks = [d for d in all_desks if not d.is_exec_desk and not d.section.is_restricted]
        exec_desks = [d for d in all_desks if d.is_exec_desk]

        for user_obj in all_users_list:
            if user_obj.is_vip:
                pool = exec_desks if exec_desks else regular_desks
            else:
                pool = regular_desks

            if pool:
                sample_desks = random.sample(pool, k=min(5, len(pool)))
                user_obj.recently_used_desk_ids = [d.id for d in sample_desks]
                user_obj.favourite_desk_ids = [sample_desks[0].id] if sample_desks else []

        db.flush()

        # --- Sample bookings (confirmed) ---
        sample_dates = ["2026-05-11", "2026-05-12", "2026-05-13", "2026-05-14", "2026-05-15"]
        completed_bookings: list[Booking] = []

        for date_str in sample_dates:
            booked_desks: set[int] = set()
            desk_pool = random.sample(regular_desks, k=min(len(regular_desks) // 2, 40))
            for desk in desk_pool:
                if desk.id in booked_desks:
                    continue
                user = random.choice(all_users_list)
                # Skip VIPs from regular desk pool in sample bookings
                if user.is_vip:
                    continue
                bk = Booking(
                    user=user,
                    desk=desk,
                    date=date_str,
                    start_time="09:00",
                    end_time="18:00",
                    status="completed" if date_str < "2026-05-13" else "confirmed",
                    booking_source=random.choice(["web_app", "agent_ai", "teams_tab"]),
                    approval_status="not_required",
                )
                db.add(bk)
                booked_desks.add(desk.id)
                if bk.status == "completed":
                    completed_bookings.append(bk)

        # VIP sample bookings on exec desks
        vip_users = [u for u in all_users_list if u.is_vip]
        for vip in vip_users:
            vip_pool = exec_desks if exec_desks else regular_desks
            for date_str in sample_dates[:3]:
                if vip_pool:
                    desk = random.choice(vip_pool)
                    db.add(Booking(
                        user=vip,
                        desk=desk,
                        date=date_str,
                        start_time="09:00",
                        end_time="18:00",
                        status="completed",
                        booking_source="web_app",
                        approval_status="approved",
                        is_anchor_day_booking=True,
                    ))

        db.flush()

        # --- Sample feedback on completed bookings ---
        for bk in completed_bookings[:20]:
            # Skew ratings to be mostly positive with some variance
            overall = random.choices([5, 4, 3, 2, 1], weights=[30, 40, 20, 7, 3])[0]
            db.add(Feedback(
                booking=bk,
                user_id=bk.user_id,
                rating=overall,
                desk_comfort=max(1, min(5, overall + random.randint(-1, 1))),
                noise_rating=max(1, min(5, overall + random.randint(-1, 1))),
                equipment_rating=max(1, min(5, overall + random.randint(-1, 1))),
                comments=random.choice([
                    "Great spot, will book again.",
                    "A bit noisy near the corridor.",
                    "Perfect setup for focused work.",
                    "Monitor could use calibrating.",
                    None,
                ]),
            ))

        # --- Sample agent sessions ---
        for i, user_obj in enumerate(all_users_list[:10]):
            db.add(
                AgentSession(
                    user=user_obj,
                    session_id=f"demo-session-{i + 1:03d}",
                    utterance_raw="Book me a desk near my team tomorrow",
                    intent_classified="book",
                    slots_extracted={"when": "2026-05-12", "where": "near_team"},
                    slots_inferred={
                        "building": user_obj.home_building.name if user_obj.home_building else None
                    },
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
        print(f"  Buildings       : {db.query(Building).count()}")
        print(f"  Floors          : {db.query(Floor).count()}")
        print(f"  Sections        : {db.query(Section).count()}")
        print(f"  Desks           : {db.query(Desk).count()}")
        print(f"  Rooms           : {db.query(Room).count()}")
        print(f"  Users           : {db.query(User).count()}")
        print(f"  Bookings        : {db.query(Booking).count()}")
        print(f"  Feedback        : {db.query(Feedback).count()}")
        print(f"  AgentSessions   : {db.query(AgentSession).count()}")
        print(f"  AllocationWts   : {db.query(AllocationWeights).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
