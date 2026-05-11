from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from places_core import repositories, schemas
from places_core.models import Room

from ..deps import get_db
from ..services.availability import get_available_rooms

router = APIRouter()


@router.get("/", response_model=list[schemas.RoomRead])
def list_rooms(
    floor_id: int | None = None, min_capacity: int = 1, db: Session = Depends(get_db)
):
    return repositories.list_rooms(db, floor_id=floor_id, min_capacity=min_capacity)


@router.get("/available", response_model=list[schemas.RoomRead])
def available_rooms(
    date: str,
    start_time: str,
    end_time: str,
    min_capacity: int = 1,
    floor_id: int | None = None,
    db: Session = Depends(get_db),
):
    return get_available_rooms(db, date, start_time, end_time, min_capacity, floor_id)


@router.get("/{room_id}", response_model=schemas.RoomRead)
def get_room(room_id: int, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if not room:
        raise HTTPException(404, "Room not found")
    return room
