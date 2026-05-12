import httpx

from places_core.settings import settings
from places_core.streamlit_auth import get_auth_headers

_backend = httpx.Client(base_url=settings.backend_url, timeout=10.0)
_agent = httpx.Client(base_url=settings.agent_url, timeout=60.0)


def agent_chat(
    message: str,
    session_id: str,
    user_id: int,
    user_display_name: str = "User",
) -> str:
    """Send a message to the DeskMate agent and return its reply."""
    resp = _agent.post(
        "/chat",
        headers=get_auth_headers(),
        json={
            "session_id": session_id,
            "message": message,
            "user_id": user_id,
            "user_display_name": user_display_name,
        },
    )
    resp.raise_for_status()
    return resp.json()["reply"]


def get_me() -> dict:
    """Return the signed-in user's database record, created on first sign-in."""
    resp = _backend.get("/users/me", headers=get_auth_headers())
    resp.raise_for_status()
    return resp.json()


def list_users() -> list[dict]:
    """Return all users — used by the UI for the demo user selector."""
    resp = _backend.get("/users/", headers=get_auth_headers())
    resp.raise_for_status()
    return resp.json()


def get_user(user_id: int) -> dict:
    resp = _backend.get(f"/users/{user_id}", headers=get_auth_headers())
    resp.raise_for_status()
    return resp.json()


def list_desks(floor_id: int | None = None) -> list[dict]:
    params: dict = {}
    if floor_id:
        params["floor_id"] = floor_id
    resp = _backend.get("/desks/", params=params, headers=get_auth_headers())
    resp.raise_for_status()
    return resp.json()


def list_rooms(floor_id: int | None = None, min_capacity: int = 1) -> list[dict]:
    params: dict = {"min_capacity": min_capacity}
    if floor_id:
        params["floor_id"] = floor_id
    resp = _backend.get("/rooms/", params=params, headers=get_auth_headers())
    resp.raise_for_status()
    return resp.json()


def create_booking(payload: dict) -> dict:
    resp = _backend.post("/bookings/", json=payload, headers=get_auth_headers())
    resp.raise_for_status()
    return resp.json()


def list_my_bookings(user_id: int) -> list[dict]:
    resp = _backend.get(f"/bookings/user/{user_id}", headers=get_auth_headers())
    resp.raise_for_status()
    return resp.json()


def cancel_booking(booking_id: int) -> dict:
    resp = _backend.delete(f"/bookings/{booking_id}", headers=get_auth_headers())
    resp.raise_for_status()
    return resp.json()


def submit_feedback(payload: dict) -> dict:
    """Submit post-visit feedback for a booking."""
    resp = _backend.post("/feedback/", json=payload, headers=get_auth_headers())
    resp.raise_for_status()
    return resp.json()


def get_booking_feedback(booking_id: int) -> list[dict]:
    resp = _backend.get(f"/feedback/booking/{booking_id}", headers=get_auth_headers())
    resp.raise_for_status()
    return resp.json()
