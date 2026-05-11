import httpx

from places_core.settings import settings

_backend = httpx.Client(base_url=settings.backend_url, timeout=10.0)


def list_locations() -> list[dict]:
    return _backend.get("/admin/locations").raise_for_status().json()


def list_floors(location_id: int | None = None) -> list[dict]:
    params: dict = {}
    if location_id:
        params["location_id"] = location_id
    return _backend.get("/admin/floors", params=params).raise_for_status().json()


def list_desks(floor_id: int | None = None) -> list[dict]:
    params: dict = {}
    if floor_id:
        params["floor_id"] = floor_id
    return _backend.get("/desks/", params=params).raise_for_status().json()


def list_rooms(floor_id: int | None = None) -> list[dict]:
    params: dict = {}
    if floor_id:
        params["floor_id"] = floor_id
    return _backend.get("/rooms/", params=params).raise_for_status().json()


def toggle_desk(desk_id: int) -> dict:
    return _backend.patch(f"/admin/desks/{desk_id}/toggle").raise_for_status().json()


def list_all_bookings() -> list[dict]:
    return _backend.get("/bookings/").raise_for_status().json()
