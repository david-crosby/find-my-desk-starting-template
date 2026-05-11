from collections.abc import Generator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from places_core.auth import is_global_admin, verify_token
from places_core.db import SessionLocal
from places_core.settings import settings


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Entra ID bearer token auth ────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """
    Validate the Entra ID Bearer token from the Authorization header.
    Returns the decoded JWT claims on success.
    Raises HTTP 401 if the token is missing or invalid.

    When MS_PLACES_ENABLED is false the backend runs in dev/demo mode and
    auth is bypassed — a synthetic claims dict is returned instead so local
    development works without Azure credentials.
    """
    if not settings.ms_places_enabled:
        return {"sub": "demo", "name": "Demo User", "email": "demo@deskmate.local", "wids": []}

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorisation token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return verify_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired.")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}")


def require_global_admin(claims: dict = Depends(get_current_user)) -> dict:
    """
    Require the authenticated user to hold the Global Administrator role in
    Entra ID.  Used as a FastAPI dependency on all admin routes.

    In dev/demo mode (ms_places_enabled=false) this check is also bypassed.
    """
    if not settings.ms_places_enabled:
        return claims

    if not is_global_admin(claims):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Global Administrator role required to access this endpoint.",
        )
    return claims
