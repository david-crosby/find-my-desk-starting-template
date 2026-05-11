from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from places_core.models import Building, Desk, Floor, Room, Section
from places_core.schemas import (
    BuildingCreate,
    BuildingRead,
    DeskBase,
    DeskRead,
    FloorRead,
    RoomBase,
    RoomRead,
    SectionRead,
)

from ..deps import get_db

router = APIRouter()


@router.get("/buildings", response_model=list[BuildingRead])
def list_buildings(db: Session = Depends(get_db)):
    """Return all buildings."""
    return db.query(Building).all()


@router.post("/buildings", response_model=BuildingRead, status_code=201)
def create_building(payload: BuildingCreate, db: Session = Depends(get_db)):
    """Create a new building."""
    building = Building(**payload.model_dump())
    db.add(building)
    db.commit()
    db.refresh(building)
    return building


@router.get("/floors", response_model=list[FloorRead])
def list_floors(building_id: int | None = None, db: Session = Depends(get_db)):
    """Return floors, optionally filtered by building."""
    q = db.query(Floor)
    if building_id:
        q = q.filter(Floor.building_id == building_id)
    return q.all()


@router.get("/sections", response_model=list[SectionRead])
def list_sections(floor_id: int | None = None, db: Session = Depends(get_db)):
    """Return sections (neighbourhoods), optionally filtered by floor."""
    q = db.query(Section)
    if floor_id:
        q = q.filter(Section.floor_id == floor_id)
    return q.all()


@router.post("/desks", response_model=DeskRead, status_code=201)
def create_desk(payload: DeskBase, db: Session = Depends(get_db)):
    """Create a new desk within a section."""
    desk = Desk(**payload.model_dump())
    db.add(desk)
    db.commit()
    db.refresh(desk)
    return desk


@router.patch("/desks/{desk_id}/toggle")
def toggle_desk(desk_id: int, db: Session = Depends(get_db)):
    """Toggle a desk between active and inactive."""
    desk = db.get(Desk, desk_id)
    if not desk:
        raise HTTPException(404, "Desk not found")
    desk.is_active = not desk.is_active
    db.commit()
    return {"id": desk_id, "is_active": desk.is_active}


@router.post("/rooms", response_model=RoomRead, status_code=201)
def create_room(payload: RoomBase, db: Session = Depends(get_db)):
    """Create a new meeting room on a floor."""
    room = Room(**payload.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room
