import sys
from pathlib import Path
from datetime import date

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

# Ensure we can import from the root project directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from allocation import allocate_desk
from places_core.db import SessionLocal
from places_core.models import Booking, Desk

app = FastAPI(title="DeskMate API")


def get_db():
    """Dependency to get a SQLAlchemy session for the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AllocationRequest(BaseModel):
    user_id: str
    target_date: str


class AllocationResponse(BaseModel):
    desk_email: str | None
    match_score: float


@app.post("/allocate", response_model=AllocationResponse)
def allocate_desk_endpoint(
    request: AllocationRequest, db: Session = Depends(get_db)
):
    """
    Scores and allocates the best available desk for a user on a given date.
    """
    # 1. Find all desks that are already booked on the target date
    booked_desk_ids = (
        db.query(Booking.desk_id)
        .filter(
            Booking.date == request.target_date,
            Booking.desk_id.isnot(None),
            Booking.status.in_(["queued", "allocated", "confirmed"])
        )
        .subquery()
    )

    # 2. Get all available active desks, ensuring we eager load the section
    available_desks = (
        db.query(Desk)
        .options(joinedload(Desk.section))
        .filter(Desk.is_active == True, Desk.id.not_in(booked_desk_ids))
        .all()
    )

    # 3. Score and allocate the best desk
    try:
        target_date_obj = date.fromisoformat(request.target_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    desk_email, match_score = allocate_desk(request.user_id, available_desks, db, target_date_obj)

    return AllocationResponse(desk_email=desk_email, match_score=match_score)