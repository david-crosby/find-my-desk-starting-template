from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from places_core import repositories, schemas

from ..deps import get_db

router = APIRouter()

_PATCHABLE_FIELDS = {
    "home_building_id", "home_floor_id", "home_section_id", "preferred_neighbourhood",
    "anchor_days", "default_working_pattern", "preferred_noise_level", "prefers_window_seat",
    "requires_standing_desk", "dual_monitor_required", "docking_station_required",
    "accessible_desk_preferred", "ergonomic_chair_required", "near_team_preferred",
    "ai_autonomy_level", "onboarding_completed",
}


@router.get("/", response_model=list[schemas.UserRead])
def list_users(db: Session = Depends(get_db)):
    return repositories.list_users(db)


@router.get("/{user_id}", response_model=schemas.UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = repositories.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.patch("/{user_id}/preferences", response_model=schemas.UserRead)
def update_preferences(user_id: int, fields: dict, db: Session = Depends(get_db)):
    """Partial update of a user's booking preferences. Used by the agent during onboarding."""
    unknown = set(fields) - _PATCHABLE_FIELDS
    if unknown:
        raise HTTPException(400, f"Unknown preference fields: {sorted(unknown)}")
    user = repositories.update_user_preferences(db, user_id, fields)
    if not user:
        raise HTTPException(404, "User not found")
    return user
