from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from places_core.models import Desk, Floor, Location, Room
from places_core.schemas import DeskBase, DeskRead, FloorRead, LocationRead, RoomBase, RoomRead

from ..deps import get_db

router = APIRouter()


@router.get("/locations", response_model=list[LocationRead])
def list_locations(db: Session = Depends(get_db)):
    return db.query(Location).all()


@router.get("/floors", response_model=list[FloorRead])
def list_floors(location_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Floor)
    if location_id:
        q = q.filter(Floor.location_id == location_id)
    return q.all()


@router.post("/desks", response_model=DeskRead, status_code=201)
def create_desk(payload: DeskBase, db: Session = Depends(get_db)):
    desk = Desk(**payload.model_dump())
    db.add(desk)
    db.commit()
    db.refresh(desk)
    return desk


@router.patch("/desks/{desk_id}/toggle")
def toggle_desk(desk_id: int, db: Session = Depends(get_db)):
    desk = db.get(Desk, desk_id)
    if not desk:
        raise HTTPException(404, "Desk not found")
    desk.is_active = not desk.is_active
    db.commit()
    return {"id": desk_id, "is_active": desk.is_active}


@router.post("/rooms", response_model=RoomRead, status_code=201)
def create_room(payload: RoomBase, db: Session = Depends(get_db)):
    room = Room(**payload.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room
