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
def available_desks(
    date: str,
    building_id: int | None = None,
    floor_id: int | None = None,
    has_standing_desk: bool | None = None,
    has_dual_monitors: bool | None = None,
    has_docking_station: bool | None = None,
    is_accessible: bool | None = None,
    is_window_seat: bool | None = None,
    db: Session = Depends(get_db),
):
    return get_available_desks(
        db, date,
        building_id=building_id,
        floor_id=floor_id,
        has_standing_desk=has_standing_desk,
        has_dual_monitors=has_dual_monitors,
        has_docking_station=has_docking_station,
        is_accessible=is_accessible,
        is_window_seat=is_window_seat,
    )


@router.get("/{desk_id}", response_model=schemas.DeskRead)
def get_desk(desk_id: int, db: Session = Depends(get_db)):
    desk = db.get(Desk, desk_id)
    if not desk:
        raise HTTPException(404, "Desk not found")
    return desk
