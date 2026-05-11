from sqlalchemy.orm import Session

from places_core import repositories
from places_core.models import Booking, Desk, Room


def get_available_desks(
    db: Session,
    date: str,
    building_id: int | None = None,
    floor_id: int | None = None,
    has_standing_desk: bool | None = None,
    has_dual_monitors: bool | None = None,
    has_docking_station: bool | None = None,
    is_accessible: bool | None = None,
    is_window_seat: bool | None = None,
) -> list[Desk]:
    booked_ids = {
        b.desk_id
        for b in db.query(Booking)
        .filter(
            Booking.date == date,
            Booking.status.in_(["queued", "confirmed", "allocated"]),
            Booking.desk_id.isnot(None),
        )
        .all()
    }

    all_desks = repositories.list_desks(
        db, floor_id=floor_id, building_id=building_id, active_only=True
    )

    result = []
    for d in all_desks:
        if d.id in booked_ids:
            continue
        if has_standing_desk and not d.has_standing_desk:
            continue
        if has_dual_monitors and not d.has_dual_monitors:
            continue
        if has_docking_station and not d.has_docking_station:
            continue
        if is_accessible and not d.is_accessible:
            continue
        if is_window_seat and not d.is_window_seat:
            continue
        result.append(d)

    return result


def get_available_rooms(
    db: Session,
    date: str,
    start_time: str,
    end_time: str,
    min_capacity: int = 1,
    floor_id: int | None = None,
) -> list[Room]:
    booked_ids = {
        b.room_id
        for b in db.query(Booking)
        .filter(
            Booking.date == date,
            Booking.status.in_(["queued", "confirmed", "allocated"]),
            Booking.room_id.isnot(None),
            Booking.start_time < end_time,
            Booking.end_time > start_time,
        )
        .all()
    }
    all_rooms = repositories.list_rooms(db, floor_id=floor_id, min_capacity=min_capacity)
    return [r for r in all_rooms if r.id not in booked_ids]
