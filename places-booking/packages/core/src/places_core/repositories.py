from sqlalchemy.orm import Session

from . import models


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email).first()


def list_desks(
    db: Session, floor_id: int | None = None, active_only: bool = True
) -> list[models.Desk]:
    q = db.query(models.Desk)
    if floor_id:
        q = q.filter(models.Desk.floor_id == floor_id)
    if active_only:
        q = q.filter(models.Desk.is_active == True)  # noqa: E712
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
        db.commit()
        db.refresh(booking)
    return booking
