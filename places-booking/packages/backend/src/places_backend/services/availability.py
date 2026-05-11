from sqlalchemy.orm import Session

from places_core import repositories
from places_core.models import Booking, Desk, Room


def get_available_desks(
    db: Session, date: str, floor_id: int | None = None
) -> list[Desk]:
    booked_ids = {
        b.desk_id
        for b in db.query(Booking)
        .filter(
            Booking.date == date,
            Booking.status == "confirmed",
            Booking.desk_id.isnot(None),
        )
        .all()
    }
    all_desks = repositories.list_desks(db, floor_id=floor_id, active_only=True)
    return [d for d in all_desks if d.id not in booked_ids]


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
            Booking.status == "confirmed",
            Booking.room_id.isnot(None),
            Booking.start_time < end_time,
            Booking.end_time > start_time,
        )
        .all()
    }
    all_rooms = repositories.list_rooms(db, floor_id=floor_id, min_capacity=min_capacity)
    return [r for r in all_rooms if r.id not in booked_ids]
