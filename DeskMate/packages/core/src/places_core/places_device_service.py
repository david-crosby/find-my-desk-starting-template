"""
Microsoft Places workplace sensor device registration.

Pushes DeskMate peripheral monitors into the MS Graph workplace sensor
database so they appear in Microsoft Places analytics and trigger the
Graph change-notification webhook when a user connects.

Graph API (beta): /workplace/sensorDevices
Required permission: PlaceDevice.ReadWrite.All (application)

In demo mode (ms_places_enabled=False) all calls return mock responses
so the UI still functions without live Azure credentials.
"""
import httpx

from .settings import settings

_GRAPH_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
_GRAPH_BASE = "https://graph.microsoft.com/beta"

_SENSOR_TYPES = ["badge", "occupancy", "peopleCount", "heartbeat", "infrared", "ipAddress", "wifi"]


def _get_app_token() -> str | None:
    if not (settings.azure_tenant_id and settings.azure_client_id and settings.azure_client_secret):
        return None
    try:
        resp = httpx.post(
            _GRAPH_TOKEN_URL.format(tenant=settings.azure_tenant_id),
            data={
                "grant_type": "client_credentials",
                "client_id": settings.azure_client_id,
                "client_secret": settings.azure_client_secret,
                "scope": "https://graph.microsoft.com/.default",
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as exc:
        return None


def _desk_display_name(monitor) -> str:
    desk = getattr(monitor, "desk", None)
    if not desk:
        return monitor.label or monitor.device_id
    parts = [monitor.label or desk.label]
    section = getattr(desk, "section", None)
    if section:
        floor = getattr(section, "floor", None)
        if floor:
            building = getattr(floor, "building", None)
            parts.append(floor.name or f"Floor {floor.number}")
            if building:
                parts.append(building.name)
    return " — ".join(parts)


def register_device_in_places(monitor) -> dict:
    """
    POST /beta/workplace/sensorDevices to register or update a monitor in MS Places.

    Returns a result dict with keys: success (bool), graph_response (dict), error (str|None).
    In demo mode returns a mock success response.
    """
    if not settings.ms_places_enabled:
        return {
            "success": False,
            "demo_mode": True,
            "message": "MS Places integration is disabled (ms_places_enabled=false). Enable it with live Azure credentials to push devices.",
        }

    token = _get_app_token()
    if not token:
        return {"success": False, "error": "Could not obtain Graph access token. Check Azure credentials in settings."}

    desk = getattr(monitor, "desk", None)
    section = getattr(desk, "section", None) if desk else None
    floor = getattr(section, "floor", None) if section else None
    building = getattr(floor, "building", None) if floor else None

    payload: dict = {
        "deviceId": monitor.device_id,
        "displayName": _desk_display_name(monitor),
        "description": (
            f"DeskMate peripheral check-in monitor. "
            f"Position: {'Primary' if monitor.position == 1 else 'Secondary'}. "
            f"Desk: {desk.label if desk else 'unknown'}."
        ),
        "sensorType": monitor.sensor_type or "badge",
    }

    if monitor.mac_address:
        payload["macAddress"] = monitor.mac_address

    if monitor.manufacturer:
        payload["manufacturer"] = {"displayName": monitor.manufacturer}

    # Link to MS Places building if we have a Places building ID
    if building and getattr(building, "places_building_id", None):
        payload["placeId"] = building.places_building_id

    try:
        resp = httpx.post(
            f"{_GRAPH_BASE}/workplace/sensorDevices",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=15.0,
        )
        if resp.status_code in (200, 201):
            return {"success": True, "graph_response": resp.json()}
        else:
            return {"success": False, "error": f"Graph returned {resp.status_code}: {resp.text}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def list_places_devices() -> dict:
    """
    GET /beta/workplace/sensorDevices — list all devices registered in MS Places.

    Returns a result dict with keys: success (bool), devices (list), error (str|None).
    """
    if not settings.ms_places_enabled:
        return {
            "success": False,
            "demo_mode": True,
            "devices": [],
            "message": "MS Places integration is disabled. Enable it to browse registered devices.",
        }

    token = _get_app_token()
    if not token:
        return {"success": False, "devices": [], "error": "Could not obtain Graph access token."}

    try:
        resp = httpx.get(
            f"{_GRAPH_BASE}/workplace/sensorDevices",
            headers={"Authorization": f"Bearer {token}"},
            params={"$top": 200},
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"success": True, "devices": data.get("value", [])}
    except Exception as exc:
        return {"success": False, "devices": [], "error": str(exc)}


def delete_device_from_places(device_id: str) -> dict:
    """DELETE /beta/workplace/sensorDevices/{deviceId} — remove from MS Places."""
    if not settings.ms_places_enabled:
        return {"success": False, "demo_mode": True}

    token = _get_app_token()
    if not token:
        return {"success": False, "error": "Could not obtain Graph access token."}

    try:
        resp = httpx.delete(
            f"{_GRAPH_BASE}/workplace/sensorDevices/{device_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        return {"success": resp.status_code in (200, 204)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
