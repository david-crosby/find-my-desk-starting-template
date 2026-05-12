import random
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from places_core import repositories, schemas
from places_core.allocation import run_nightly_allocation
from places_core.models import AgentSession, Allocation, Booking, Building, Desk, Floor, Room, Section, User
from places_core.schemas import (
    BuildingCreate,
    BuildingRead,
    DeskBase,
    DeskRead,
    FloorRead,
    OrgRulesRead,
    OrgRulesUpdate,
    RoomBase,
    RoomRead,
    SectionRead,
    WeightsRead,
    WeightsUpdate,
)

from ..deps import get_db, require_global_admin

# All routes in this router require the Global Administrator role.
router = APIRouter(dependencies=[Depends(require_global_admin)])


@router.get("/buildings", response_model=list[BuildingRead])
def list_buildings(db: Session = Depends(get_db)):
    """Return all buildings."""
    return db.query(Building).all()


@router.post("/buildings", response_model=BuildingRead, status_code=201)
def create_building(payload: BuildingCreate, db: Session = Depends(get_db)):
    """Create a new building."""
    building = Building(**payload.model_dump())
    db.add(building)
    db.commit()
    db.refresh(building)
    return building


@router.get("/floors", response_model=list[FloorRead])
def list_floors(building_id: int | None = None, db: Session = Depends(get_db)):
    """Return floors, optionally filtered by building."""
    q = db.query(Floor)
    if building_id:
        q = q.filter(Floor.building_id == building_id)
    return q.all()


@router.get("/sections", response_model=list[SectionRead])
def list_sections(floor_id: int | None = None, db: Session = Depends(get_db)):
    """Return sections (neighbourhoods), optionally filtered by floor."""
    q = db.query(Section)
    if floor_id:
        q = q.filter(Section.floor_id == floor_id)
    return q.all()


@router.post("/desks", response_model=DeskRead, status_code=201)
def create_desk(payload: DeskBase, db: Session = Depends(get_db)):
    """Create a new desk within a section."""
    desk = Desk(**payload.model_dump())
    db.add(desk)
    db.commit()
    db.refresh(desk)
    return desk


@router.patch("/desks/{desk_id}/toggle")
def toggle_desk(desk_id: int, db: Session = Depends(get_db)):
    """Toggle a desk between active and inactive."""
    desk = db.get(Desk, desk_id)
    if not desk:
        raise HTTPException(404, "Desk not found")
    desk.is_active = not desk.is_active
    db.commit()
    return {"id": desk_id, "is_active": desk.is_active}


@router.post("/rooms", response_model=RoomRead, status_code=201)
def create_room(payload: RoomBase, db: Session = Depends(get_db)):
    """Create a new meeting room on a floor."""
    room = Room(**payload.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


# ── Allocation weights ────────────────────────────────────────────────────────

@router.get("/weights", response_model=WeightsRead)
def get_weights(db: Session = Depends(get_db)):
    return repositories.get_active_weights(db)


@router.put("/weights", response_model=WeightsRead)
def update_weights(payload: WeightsUpdate, db: Session = Depends(get_db)):
    return repositories.update_weights(db, payload.model_dump(exclude_none=True))


# ── Org rules ─────────────────────────────────────────────────────────────────

@router.get("/rules", response_model=OrgRulesRead)
def get_rules(db: Session = Depends(get_db)):
    return repositories.get_org_rules(db)


@router.put("/rules", response_model=OrgRulesRead)
def update_rules(payload: OrgRulesUpdate, db: Session = Depends(get_db)):
    return repositories.update_org_rules(db, payload.model_dump(exclude_none=True))


@router.patch("/sections/{section_id}/toggle-restrict")
def toggle_section_restrict(section_id: int, db: Session = Depends(get_db)):
    section = db.get(Section, section_id)
    if not section:
        raise HTTPException(404, "Section not found")
    return repositories.toggle_section_restrict(db, section_id)


@router.patch("/desks/{desk_id}/toggle-exec")
def toggle_desk_exec(desk_id: int, db: Session = Depends(get_db)):
    desk = db.get(Desk, desk_id)
    if not desk:
        raise HTTPException(404, "Desk not found")
    return repositories.toggle_desk_exec(db, desk_id)


# ── Allocation run ────────────────────────────────────────────────────────────

def _allocation_details(run_date_str: str, db: Session, booking_ids: set[int] | None = None) -> list[dict]:
    """Build a per-booking detail list from Allocation records for a given date."""
    q = (
        db.query(Allocation)
        .options(
            joinedload(Allocation.booking).joinedload(Booking.user),
            joinedload(Allocation.booking).joinedload(Booking.desk).joinedload(Desk.section).joinedload(Section.floor).joinedload(Floor.building),
        )
        .filter(Allocation.allocation_run_date == run_date_str)
    )
    if booking_ids is not None:
        q = q.filter(Allocation.booking_id.in_(booking_ids))
    allocs = q.all()
    details = []
    for alloc in allocs:
        booking = alloc.booking
        user = booking.user if booking else None
        desk = booking.desk if booking else None
        section = desk.section if desk else None
        floor = section.floor if section else None
        building = floor.building if floor else None
        details.append({
            "user_name": user.display_name if user else "Unknown",
            "is_vip": user.is_vip if user else False,
            "is_anchor_day": booking.is_anchor_day_booking if booking else False,
            "booking_source": booking.booking_source if booking else None,
            "desk_label": desk.label if desk else None,
            "section": section.zone_label or section.name if section else None,
            "floor": floor.name or f"Floor {floor.number}" if floor else None,
            "building": building.name if building else None,
            "score": alloc.score,
            "match_pct": alloc.match_percentage,
            "status": booking.status if booking else "failed",
            "notes": alloc.allocation_notes,
        })
    return details


@router.post("/allocation/run")
def run_allocation(target_date: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Trigger the nightly allocation engine immediately for a given date.

    Defaults to tomorrow if no date is provided.
    Processes all queued bookings with desk_id=None for that date.
    """
    run_date = date.fromisoformat(target_date) if target_date else date.today() + timedelta(days=1)
    run_date_str = run_date.isoformat()

    queued_count = (
        db.query(Booking)
        .filter(Booking.date == run_date_str, Booking.status == "queued", Booking.desk_id.is_(None))
        .count()
    )
    if queued_count == 0:
        return {"date": run_date_str, "stats": {"allocated": 0, "failed": 0, "escalated": 0}, "details": [], "queued_before": 0}

    stats = run_nightly_allocation(db, run_date)
    details = _allocation_details(run_date_str, db)
    return {"date": run_date_str, "stats": stats, "details": details, "queued_before": queued_count}


@router.post("/allocation/demo")
def run_allocation_demo(
    target_date: str | None = None,
    num_users: int = 10,
    db: Session = Depends(get_db),
) -> dict:
    """Create synthetic queued bookings for demo purposes, then run the allocation engine.

    Picks num_users random users who do not already have a booking on target_date,
    creates queued bookings marked booking_source='demo', runs the full allocation,
    and returns detailed per-user results. Demo bookings are kept in the database
    so they appear in analytics.
    """
    run_date = date.fromisoformat(target_date) if target_date else date.today() + timedelta(days=1)
    run_date_str = run_date.isoformat()

    # Remove previous demo bookings (and their allocations) for this date so re-runs work cleanly
    old_demo_ids = [
        r[0] for r in db.query(Booking.id).filter(
            Booking.date == run_date_str, Booking.booking_source == "demo"
        ).all()
    ]
    if old_demo_ids:
        db.query(Allocation).filter(Allocation.booking_id.in_(old_demo_ids)).delete(synchronize_session=False)
        db.query(Booking).filter(Booking.id.in_(old_demo_ids)).delete(synchronize_session=False)
        db.commit()

    # Only exclude users who already have an unprocessed queued booking on this date
    # (desk not yet assigned). Users with allocated/completed bookings are fine —
    # a second demo booking simply lets the engine make an additional allocation.
    blocked_user_ids = {
        r[0] for r in db.query(Booking.user_id).filter(
            Booking.date == run_date_str,
            Booking.status == "queued",
            Booking.desk_id.is_(None),
            Booking.booking_source != "demo",
        ).all()
    }
    candidates = db.query(User).filter(User.id.notin_(blocked_user_ids)).all()
    if not candidates:
        raise HTTPException(400, "No eligible users found — all users already have unprocessed queued bookings on this date.")

    selected = random.sample(candidates, min(num_users, len(candidates)))

    for user in selected:
        anchor_days: list = user.anchor_days or []
        is_anchor = run_date.strftime("%A").lower() in [d.lower() for d in anchor_days]
        db.add(Booking(
            user_id=user.id,
            date=run_date_str,
            status="queued",
            booking_source="demo",
            is_anchor_day_booking=is_anchor,
        ))

    db.commit()

    # Capture the IDs of the bookings we just created
    demo_booking_ids = {
        r[0] for r in db.query(Booking.id).filter(
            Booking.date == run_date_str,
            Booking.booking_source == "demo",
            Booking.status == "queued",
        ).all()
    }

    stats = run_nightly_allocation(db, run_date)
    details = _allocation_details(run_date_str, db, booking_ids=demo_booking_ids)

    return {
        "date": run_date_str,
        "simulated_users": len(selected),
        "stats": stats,
        "details": details,
    }


# ── User management ──────────────────────────────────────────────────────────

_ADMIN_USER_PATCHABLE = {
    "display_name", "department", "role", "employment_type",
    "entra_team_type", "is_vip",
    "home_building_id", "home_floor_id", "home_section_id", "preferred_neighbourhood",
    "anchor_days", "booking_window_days", "line_manager_email",
    "preferred_noise_level", "prefers_window_seat", "prefers_near_lift",
    "prefers_near_exit", "prefers_near_toilets", "avoids_ac",
    "preferred_monitors", "prefers_ultrawide", "requires_standing_desk",
    "docking_station_required", "ergonomic_chair_required", "accessible_desk_preferred",
    "near_team_preferred", "ai_autonomy_level",
}


@router.get("/users", response_model=list[schemas.UserRead])
def list_users(db: Session = Depends(get_db)):
    """Return all users."""
    return repositories.list_users(db)


@router.patch("/users/{user_id}", response_model=schemas.UserRead)
def update_user(user_id: int, fields: dict, db: Session = Depends(get_db)):
    """Admin update of any user field including identity, home location, and allocation flags."""
    unknown = set(fields) - _ADMIN_USER_PATCHABLE
    if unknown:
        raise HTTPException(400, f"Unknown fields: {sorted(unknown)}")
    user = repositories.update_user_preferences(db, user_id, fields)
    if not user:
        raise HTTPException(404, "User not found")
    return user


# ── Analytics endpoints ───────────────────────────────────────────────────────

@router.get("/analytics/summary")
def analytics_summary(db: Session = Depends(get_db)) -> dict:
    """
    Workspace utilisation and booking behaviour metrics derived from the
    bookings database (nightly batch pipeline equivalent).
    """
    all_bookings = db.query(Booking).all()
    active_desks = db.query(Desk).filter(Desk.is_active == True).count()  # noqa: E712

    status_counts: Counter = Counter(b.status for b in all_bookings)
    source_counts: Counter = Counter(b.booking_source for b in all_bookings)

    total = len(all_bookings)
    no_show = status_counts.get("no_show", 0)
    cancelled = status_counts.get("cancelled", 0)
    completed = status_counts.get("completed", 0)
    active_total = total - cancelled

    no_show_rate = round(no_show / active_total * 100, 1) if active_total else 0
    cancellation_rate = round(cancelled / total * 100, 1) if total else 0

    # Bookings per day — last 30 days
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    daily: dict[str, int] = defaultdict(int)
    desk_daily: dict[str, int] = defaultdict(int)
    room_daily: dict[str, int] = defaultdict(int)
    source_by_date: dict[str, Counter] = defaultdict(Counter)
    advance_days_list: list[int] = []
    repeat_desk: Counter = Counter()

    for b in all_bookings:
        if b.date >= cutoff:
            daily[b.date] += 1
            if b.desk_id:
                desk_daily[b.date] += 1
                repeat_desk[b.desk_id] += 1
            if b.room_id:
                room_daily[b.date] += 1
            source_by_date[b.date][b.booking_source] += 1

        if b.booking_created_at and b.date:
            try:
                created = b.booking_created_at.date()
                booked = date.fromisoformat(b.date)
                advance_days_list.append((booked - created).days)
            except (ValueError, AttributeError):
                pass

    avg_advance_days = round(sum(advance_days_list) / len(advance_days_list), 1) if advance_days_list else None

    # 4-week rolling no-show average
    four_weeks_ago = (date.today() - timedelta(weeks=4)).isoformat()
    recent = [b for b in all_bookings if b.date >= four_weeks_ago]
    recent_active = [b for b in recent if b.status != "cancelled"]
    recent_no_show = sum(1 for b in recent if b.status == "no_show")
    rolling_no_show_rate = round(recent_no_show / len(recent_active) * 100, 1) if recent_active else 0

    # Utilisation rate: average % of active desks booked per day
    daily_util = {}
    for d, count in desk_daily.items():
        daily_util[d] = round(count / active_desks * 100, 1) if active_desks else 0

    # Most-used desks (top 10)
    top_desks = [{"desk_id": k, "bookings": v} for k, v in repeat_desk.most_common(10)]

    return {
        "total_bookings": total,
        "active_desks": active_desks,
        "status_breakdown": dict(status_counts),
        "source_breakdown": dict(source_counts),
        "no_show_rate_pct": no_show_rate,
        "rolling_4w_no_show_rate_pct": rolling_no_show_rate,
        "cancellation_rate_pct": cancellation_rate,
        "avg_advance_booking_days": avg_advance_days,
        "daily_bookings": dict(sorted(daily.items())),
        "daily_desk_bookings": dict(sorted(desk_daily.items())),
        "daily_room_bookings": dict(sorted(room_daily.items())),
        "daily_utilisation_pct": dict(sorted(daily_util.items())),
        "top_desks_by_usage": top_desks,
        "note_realtime": (
            "Live floor heatmaps and sensor occupancy require Microsoft Graph "
            "workplace sensor integration (GET /workplace/sensorDevices)."
        ),
    }


@router.get("/analytics/agent")
def analytics_agent(db: Session = Depends(get_db)) -> dict:
    """AI agent performance metrics from agent_sessions table."""
    sessions = db.query(AgentSession).all()
    total = len(sessions)
    if not total:
        return {"total_sessions": 0}

    fallbacks = sum(1 for s in sessions if s.fallback_triggered)
    rated = [s for s in sessions if s.user_accepted_rank is not None]
    first_pick = sum(1 for s in rated if s.user_accepted_rank == 1)
    clarification_turns = [s.clarification_turns for s in sessions]
    confidence_scores = [s.confidence_score for s in sessions if s.confidence_score is not None]
    intent_counts: Counter = Counter(s.intent_classified for s in sessions if s.intent_classified)

    return {
        "total_sessions": total,
        "fallback_rate_pct": round(fallbacks / total * 100, 1),
        "first_suggestion_acceptance_rate_pct": (
            round(first_pick / len(rated) * 100, 1) if rated else None
        ),
        "avg_clarification_turns": (
            round(sum(clarification_turns) / len(clarification_turns), 2)
            if clarification_turns else 0
        ),
        "avg_confidence_score": (
            round(sum(confidence_scores) / len(confidence_scores), 1)
            if confidence_scores else None
        ),
        "intent_breakdown": dict(intent_counts),
        "sessions_with_feedback": sum(1 for s in sessions if s.feedback_rating is not None),
    }
