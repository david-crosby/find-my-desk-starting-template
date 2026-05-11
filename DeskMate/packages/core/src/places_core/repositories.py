from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import models


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> models.User | None:
    return db.get(models.User, user_id)


def list_users(db: Session) -> list[models.User]:
    return db.query(models.User).all()


def update_user_preferences(db: Session, user_id: int, fields: dict) -> models.User | None:
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    for key, value in fields.items():
        if hasattr(user, key):
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def list_buildings(db: Session) -> list[models.Building]:
    return db.query(models.Building).all()


def list_floors(db: Session, building_id: int | None = None) -> list[models.Floor]:
    q = db.query(models.Floor)
    if building_id:
        q = q.filter(models.Floor.building_id == building_id)
    return q.all()


def list_sections(db: Session, floor_id: int | None = None) -> list[models.Section]:
    q = db.query(models.Section)
    if floor_id:
        q = q.filter(models.Section.floor_id == floor_id)
    return q.all()


def list_desks(
    db: Session,
    section_id: int | None = None,
    floor_id: int | None = None,
    building_id: int | None = None,
    active_only: bool = True,
) -> list[models.Desk]:
    q = db.query(models.Desk)
    if active_only:
        q = q.filter(models.Desk.is_active == True)  # noqa: E712
    if section_id:
        q = q.filter(models.Desk.section_id == section_id)
    elif floor_id:
        q = q.join(models.Section).filter(models.Section.floor_id == floor_id)
    elif building_id:
        q = (
            q.join(models.Section)
            .join(models.Floor)
            .filter(models.Floor.building_id == building_id)
        )
    return q.all()


def list_rooms(
    db: Session, floor_id: int | None = None, min_capacity: int = 1
) -> list[models.Room]:
    q = db.query(models.Room).filter(models.Room.is_active == True)  # noqa: E712
    if floor_id:
        q = q.filter(models.Room.floor_id == floor_id)
    if min_capacity > 1:
        q = q.filter(models.Room.capacity >= min_capacity)
    return q.all()


def create_booking(db: Session, **kwargs) -> models.Booking:
    booking = models.Booking(**kwargs)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_booking(db: Session, booking_id: int) -> models.Booking | None:
    return db.get(models.Booking, booking_id)


def list_bookings_for_user(db: Session, user_id: int) -> list[models.Booking]:
    return db.query(models.Booking).filter(models.Booking.user_id == user_id).all()


def list_all_bookings(db: Session) -> list[models.Booking]:
    return db.query(models.Booking).all()


def cancel_booking(db: Session, booking_id: int) -> models.Booking | None:
    booking = get_booking(db, booking_id)
    if booking:
        booking.status = "cancelled"
        booking.booking_cancelled_at = datetime.now(timezone.utc)
        booking.cancellation_reason = "user_cancelled"
        db.commit()
        db.refresh(booking)
    return booking


def create_agent_session(db: Session, **kwargs) -> models.AgentSession:
    session = models.AgentSession(**kwargs)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_agent_session(db: Session, session_id: int) -> models.AgentSession | None:
    return db.get(models.AgentSession, session_id)


def list_bookings_on_date(db: Session, date: str) -> list[models.Booking]:
    return (
        db.query(models.Booking)
        .filter(models.Booking.date == date, models.Booking.status == "confirmed")
        .all()
    )


def list_queued_bookings_for_date(db: Session, date: str) -> list[models.Booking]:
    return (
        db.query(models.Booking)
        .filter(models.Booking.date == date, models.Booking.status == "queued")
        .all()
    )


def create_allocation(db: Session, **kwargs) -> models.Allocation:
    allocation = models.Allocation(**kwargs)
    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    return allocation


def get_allocation_for_booking(db: Session, booking_id: int) -> models.Allocation | None:
    return (
        db.query(models.Allocation)
        .filter(models.Allocation.booking_id == booking_id)
        .first()
    )


def create_checkin(db: Session, **kwargs) -> models.CheckIn:
    checkin = models.CheckIn(**kwargs)
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return checkin


def list_checkins_for_date(db: Session, date_prefix: str) -> list[models.CheckIn]:
    """Return checkins whose detected_at timestamp starts with the given date string (YYYY-MM-DD)."""
    return (
        db.query(models.CheckIn)
        .filter(models.CheckIn.detected_at >= date_prefix)
        .all()
    )


def create_feedback(db: Session, **kwargs) -> models.Feedback:
    feedback = models.Feedback(**kwargs)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def list_feedback_for_booking(db: Session, booking_id: int) -> list[models.Feedback]:
    return (
        db.query(models.Feedback)
        .filter(models.Feedback.booking_id == booking_id)
        .all()
    )


def list_feedback_for_user(db: Session, user_id: int) -> list[models.Feedback]:
    return (
        db.query(models.Feedback)
        .filter(models.Feedback.user_id == user_id)
        .all()
    )
