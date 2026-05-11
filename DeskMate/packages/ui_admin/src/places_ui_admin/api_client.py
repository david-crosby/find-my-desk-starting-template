import httpx

from places_core.settings import settings
from places_core.streamlit_auth import get_auth_headers

_backend = httpx.Client(base_url=settings.backend_url, timeout=10.0)


def list_buildings() -> list[dict]:
    return _backend.get("/admin/buildings", headers=get_auth_headers()).raise_for_status().json()


def list_floors(building_id: int | None = None) -> list[dict]:
    params: dict = {}
    if building_id:
        params["building_id"] = building_id
    return _backend.get("/admin/floors", params=params, headers=get_auth_headers()).raise_for_status().json()


def list_desks(floor_id: int | None = None) -> list[dict]:
    params: dict = {}
    if floor_id:
        params["floor_id"] = floor_id
    return _backend.get("/desks/", params=params, headers=get_auth_headers()).raise_for_status().json()


def list_rooms(floor_id: int | None = None) -> list[dict]:
    params: dict = {}
    if floor_id:
        params["floor_id"] = floor_id
    return _backend.get("/rooms/", params=params, headers=get_auth_headers()).raise_for_status().json()


def toggle_desk(desk_id: int) -> dict:
    return _backend.patch(f"/admin/desks/{desk_id}/toggle", headers=get_auth_headers()).raise_for_status().json()


def list_all_bookings() -> list[dict]:
    return _backend.get("/bookings/", headers=get_auth_headers()).raise_for_status().json()


def get_analytics_summary() -> dict:
    return _backend.get("/admin/analytics/summary", headers=get_auth_headers()).raise_for_status().json()


def get_agent_analytics() -> dict:
    return _backend.get("/admin/analytics/agent", headers=get_auth_headers()).raise_for_status().json()
