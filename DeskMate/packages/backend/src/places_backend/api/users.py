from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from places_core import repositories, schemas

from ..deps import get_db

router = APIRouter()


@router.get("/", response_model=list[schemas.UserRead])
def list_users(db: Session = Depends(get_db)):
    """Return all users — used by the agent and admin UI to resolve user identities."""
    return repositories.list_users(db)


@router.get("/{user_id}", response_model=schemas.UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Return a single user by ID."""
    user = repositories.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user
