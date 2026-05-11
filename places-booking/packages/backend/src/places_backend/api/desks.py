from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from places_core import repositories, schemas
from places_core.models import Desk

from ..deps import get_db
from ..services.availability import get_available_desks

router = APIRouter()


@router.get("/", response_model=list[schemas.DeskRead])
def list_desks(floor_id: int | None = None, db: Session = Depends(get_db)):
    return repositories.list_desks(db, floor_id=floor_id)


@router.get("/available", response_model=list[schemas.DeskRead])
def available_desks(date: str, floor_id: int | None = None, db: Session = Depends(get_db)):
    return get_available_desks(db, date, floor_id=floor_id)


@router.get("/{desk_id}", response_model=schemas.DeskRead)
def get_desk(desk_id: int, db: Session = Depends(get_db)):
    desk = db.get(Desk, desk_id)
    if not desk:
        raise HTTPException(404, "Desk not found")
    return desk
