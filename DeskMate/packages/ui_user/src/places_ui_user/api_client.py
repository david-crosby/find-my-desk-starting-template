import httpx

from places_core.settings import settings

_backend = httpx.Client(base_url=settings.backend_url, timeout=10.0)
_agent = httpx.Client(base_url=settings.agent_url, timeout=30.0)


def agent_chat(message: str, session_id: str, user_id: int) -> str:
    resp = _agent.post(
        "/chat",
        json={"session_id": session_id, "message": message, "user_id": user_id},
    )
    resp.raise_for_status()
    return resp.json()["reply"]


def list_desks(floor_id: int | None = None) -> list[dict]:
    params: dict = {}
    if floor_id:
        params["floor_id"] = floor_id
    resp = _backend.get("/desks/", params=params)
    resp.raise_for_status()
    return resp.json()


def list_rooms(floor_id: int | None = None, min_capacity: int = 1) -> list[dict]:
    params: dict = {"min_capacity": min_capacity}
    if floor_id:
        params["floor_id"] = floor_id
    resp = _backend.get("/rooms/", params=params)
    resp.raise_for_status()
    return resp.json()


def create_booking(payload: dict) -> dict:
    resp = _backend.post("/bookings/", json=payload)
    resp.raise_for_status()
    return resp.json()


def list_my_bookings(user_id: int) -> list[dict]:
    resp = _backend.get(f"/bookings/user/{user_id}")
    resp.raise_for_status()
    return resp.json()


def cancel_booking(booking_id: int) -> dict:
    resp = _backend.delete(f"/bookings/{booking_id}")
    resp.raise_for_status()
    return resp.json()
