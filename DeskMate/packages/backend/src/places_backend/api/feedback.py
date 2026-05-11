from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from places_core import repositories, schemas

from ..deps import get_db

router = APIRouter()


@router.post("/", response_model=schemas.FeedbackRead, status_code=201)
def create_feedback(payload: schemas.FeedbackCreate, db: Session = Depends(get_db)):
    """Submit post-visit feedback for a completed booking."""
    booking = repositories.get_booking(db, payload.booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")
    return repositories.create_feedback(db, **payload.model_dump())


@router.get("/booking/{booking_id}", response_model=list[schemas.FeedbackRead])
def list_booking_feedback(booking_id: int, db: Session = Depends(get_db)):
    """Return all feedback entries for a specific booking."""
    return repositories.list_feedback_for_booking(db, booking_id)


@router.get("/user/{user_id}", response_model=list[schemas.FeedbackRead])
def list_user_feedback(user_id: int, db: Session = Depends(get_db)):
    """Return all feedback submitted by a user."""
    return repositories.list_feedback_for_user(db, user_id)
