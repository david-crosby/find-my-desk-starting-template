from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from places_core import repositories, schemas

from ..deps import get_db

router = APIRouter()


@router.post("/", response_model=schemas.BookingRead, status_code=201)
def create_booking(payload: schemas.BookingCreate, db: Session = Depends(get_db)):
    return repositories.create_booking(db, **payload.model_dump())


@router.get("/user/{user_id}", response_model=list[schemas.BookingRead])
def list_user_bookings(user_id: int, db: Session = Depends(get_db)):
    return repositories.list_bookings_for_user(db, user_id)


@router.get("/", response_model=list[schemas.BookingRead])
def list_all_bookings(db: Session = Depends(get_db)):
    return repositories.list_all_bookings(db)


@router.get("/{booking_id}", response_model=schemas.BookingRead)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = repositories.get_booking(db, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    return booking


@router.delete("/{booking_id}", response_model=schemas.BookingRead)
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = repositories.cancel_booking(db, booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    return booking
