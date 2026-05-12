from datetime import date

from sqlalchemy.orm import Session, joinedload

from places_core.allocation import allocate_desk as _weighted_allocate
from places_core.models import Desk, Room, User

from .availability import get_available_desks, get_available_rooms


def allocate_desk(
    db: Session,
    date_str: str,
    user_id: int | None = None,
    floor_id: int | None = None,
) -> Desk | None:
    """Allocate the best available desk for a user using the weighted scoring engine.

    Falls back to first-available if no user context is provided.
    """
    available = get_available_desks(db, date_str, floor_id=floor_id)
    if not available:
        return None

    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.entra_id:
            desks_with_sections = (
                db.query(Desk)
                .options(joinedload(Desk.section))
                .filter(Desk.id.in_([d.id for d in available]))
                .all()
            )
            try:
                target = date.fromisoformat(date_str)
            except ValueError:
                target = date.today()

            desk_email, _ = _weighted_allocate(user.entra_id, desks_with_sections, db, target)
            if desk_email:
                return next((d for d in available if d.desk_email_address == desk_email), None)

    return available[0]


def allocate_room(
    db: Session,
    date_str: str,
    start_time: str,
    end_time: str,
    min_capacity: int = 1,
    floor_id: int | None = None,
) -> Room | None:
    available = get_available_rooms(db, date_str, start_time, end_time, min_capacity, floor_id)
    return available[0] if available else None
