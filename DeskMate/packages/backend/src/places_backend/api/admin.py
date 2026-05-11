from collections import Counter, defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from places_core.models import AgentSession, Booking, Building, Desk, Floor, Room, Section
from places_core.schemas import (
    BuildingCreate,
    BuildingRead,
    DeskBase,
    DeskRead,
    FloorRead,
    RoomBase,
    RoomRead,
    SectionRead,
)

from ..deps import get_db

router = APIRouter()


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
