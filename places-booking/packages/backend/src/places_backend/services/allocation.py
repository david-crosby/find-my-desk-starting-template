from sqlalchemy.orm import Session

from places_core.models import Desk, Room

from .availability import get_available_desks, get_available_rooms


def allocate_desk(db: Session, date: str, floor_id: int | None = None) -> Desk | None:
    available = get_available_desks(db, date, floor_id=floor_id)
    return available[0] if available else None


def allocate_room(
    db: Session,
    date: str,
    start_time: str,
    end_time: str,
    min_capacity: int = 1,
    floor_id: int | None = None,
) -> Room | None:
    available = get_available_rooms(db, date, start_time, end_time, min_capacity, floor_id)
    return available[0] if available else None
