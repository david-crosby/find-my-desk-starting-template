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


def list_sections(floor_id: int | None = None) -> list[dict]:
    params: dict = {}
    if floor_id:
        params["floor_id"] = floor_id
    return _backend.get("/admin/sections", params=params, headers=get_auth_headers()).raise_for_status().json()


def toggle_section_restrict(section_id: int) -> dict:
    return _backend.patch(f"/admin/sections/{section_id}/toggle-restrict", headers=get_auth_headers()).raise_for_status().json()


def toggle_desk_exec(desk_id: int) -> dict:
    return _backend.patch(f"/admin/desks/{desk_id}/toggle-exec", headers=get_auth_headers()).raise_for_status().json()


def get_weights() -> dict:
    return _backend.get("/admin/weights", headers=get_auth_headers()).raise_for_status().json()


def update_weights(fields: dict) -> dict:
    return _backend.put("/admin/weights", json=fields, headers=get_auth_headers()).raise_for_status().json()


def get_org_rules() -> dict:
    return _backend.get("/admin/rules", headers=get_auth_headers()).raise_for_status().json()


def update_org_rules(fields: dict) -> dict:
    return _backend.put("/admin/rules", json=fields, headers=get_auth_headers()).raise_for_status().json()


def run_allocation(target_date: str | None = None) -> dict:
    params = {"target_date": target_date} if target_date else {}
    return _backend.post("/admin/allocation/run", params=params, headers=get_auth_headers(), timeout=60.0).raise_for_status().json()


def list_users_admin() -> list[dict]:
    return _backend.get("/admin/users", headers=get_auth_headers()).raise_for_status().json()


def update_user_admin(user_id: int, fields: dict) -> dict:
    return _backend.patch(f"/admin/users/{user_id}", json=fields, headers=get_auth_headers()).raise_for_status().json()


def run_allocation_demo(target_date: str | None = None, num_users: int = 10) -> dict:
    params: dict = {"num_users": num_users}
    if target_date:
        params["target_date"] = target_date
    return _backend.post("/admin/allocation/demo", params=params, headers=get_auth_headers(), timeout=60.0).raise_for_status().json()
