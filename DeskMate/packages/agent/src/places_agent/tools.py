import contextvars
import inspect

import httpx

from places_core.settings import settings

# Stores the Bearer token for the current request so all tool calls can
# forward it to the backend without threading it through every function signature.
_auth_token: contextvars.ContextVar[str] = contextvars.ContextVar("_auth_token", default="")


class _AuthedClient(httpx.Client):
    """httpx.Client that automatically injects the per-request auth token."""

    def request(self, method: str, url, **kwargs) -> httpx.Response:
        headers = dict(kwargs.pop("headers", None) or {})
        token = _auth_token.get()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return super().request(method, url, headers=headers, **kwargs)


_client = _AuthedClient(base_url=settings.backend_url, timeout=10.0)

TOOLS: list[dict] = [
    # ── Profile ──────────────────────────────────────────────────────────────
    {
        "name": "get_user_profile",
        "description": (
            "Fetch a user's full profile including their home building, preferred floor, "
            "equipment requirements, noise preference, accessibility needs, anchor days, "
            "AI autonomy level, and onboarding status. Call this silently at the start of "
            "every new session."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "required": ["user_id"],
        },
    },
    {
        "name": "update_user_profile",
        "description": (
            "Write preference updates back to the user's profile. Used during Tier 0 "
            "onboarding and whenever the user changes a preference. Pass only the fields "
            "that need updating — all others are left unchanged. "
            "Updatable fields: home_building_id (int), home_floor_id (int), "
            "home_section_id (int), preferred_neighbourhood (str), anchor_days (list), "
            "default_working_pattern (object), preferred_noise_level (str: silent/quiet/moderate/no_preference), "
            "prefers_window_seat (bool), requires_standing_desk (bool), "
            "preferred_monitors (int: 1/2/3), prefers_ultrawide (bool), "
            "docking_station_required (bool), accessible_desk_preferred (bool), "
            "ergonomic_chair_required (bool), near_team_preferred (bool), "
            "prefers_near_lift (bool), prefers_near_exit (bool), prefers_near_toilets (bool), "
            "avoids_ac (bool), ai_autonomy_level (str: book_with_confirm/"
            "book_autonomously/always_show_options), onboarding_completed (bool)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer"},
                "fields": {
                    "type": "object",
                    "description": "Key/value pairs of profile fields to update.",
                },
            },
            "required": ["user_id", "fields"],
        },
    },
    # ── Availability and booking ──────────────────────────────────────────────
    {
        "name": "check_desk_availability",
        "description": (
            "List available desks for a given date. Supports amenity filters for Tier 3 "
            "requirement matching. All filter parameters are optional — omit any that are "
            "not relevant to the user's request."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "ISO date, e.g. 2026-06-01"},
                "building_id": {"type": "integer", "description": "Filter by building"},
                "floor_id": {"type": "integer", "description": "Filter by floor"},
                "has_standing_desk": {"type": "boolean", "description": "Requires a sit-stand desk"},
                "min_monitors": {"type": "integer", "description": "Minimum number of monitors required (1, 2, or 3)"},
                "has_docking_station": {"type": "boolean", "description": "Requires a docking station"},
                "is_accessible": {"type": "boolean", "description": "Requires wheelchair-accessible desk"},
                "is_window_seat": {"type": "boolean", "description": "Prefers a window seat"},
                "has_ultrawide": {"type": "boolean", "description": "Requires an ultrawide monitor"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "book_desk",
        "description": "Book a specific desk for a user on a date. The booking is queued and confirmed overnight by the allocation engine.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer"},
                "desk_id": {"type": "integer"},
                "date": {"type": "string", "description": "ISO date, e.g. 2026-06-01"},
            },
            "required": ["user_id", "desk_id", "date"],
        },
    },
    {
        "name": "check_room_availability",
        "description": "List available meeting rooms for a given date and time slot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "start_time": {"type": "string", "description": "HH:MM (24-hour)"},
                "end_time": {"type": "string", "description": "HH:MM (24-hour)"},
                "min_capacity": {"type": "integer", "default": 1},
            },
            "required": ["date", "start_time", "end_time"],
        },
    },
    {
        "name": "book_room",
        "description": "Book a meeting room for a user. The booking is queued and confirmed overnight.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer"},
                "room_id": {"type": "integer"},
                "date": {"type": "string"},
                "start_time": {"type": "string", "description": "HH:MM (24-hour)"},
                "end_time": {"type": "string", "description": "HH:MM (24-hour)"},
            },
            "required": ["user_id", "room_id", "date", "start_time", "end_time"],
        },
    },
    # ── Booking management ────────────────────────────────────────────────────
    {
        "name": "list_my_bookings",
        "description": "Retrieve all bookings for a given user, including upcoming and past.",
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "required": ["user_id"],
        },
    },
    {
        "name": "get_booking_history",
        "description": (
            "Retrieve a user's booking history for Tier 5 pattern recognition. "
            "Returns all bookings so the agent can identify preferred desks, "
            "typical days, and office attendance patterns."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "required": ["user_id"],
        },
    },
    {
        "name": "cancel_booking",
        "description": "Cancel a single existing booking by ID. Use for single cancellations (Tier 6).",
        "input_schema": {
            "type": "object",
            "properties": {"booking_id": {"type": "integer"}},
            "required": ["booking_id"],
        },
    },
    {
        "name": "cancel_multiple_bookings",
        "description": (
            "Cancel two or more bookings at once. Only call this after the user has "
            "explicitly confirmed the full list of bookings to cancel (Tier 6 bulk cancellation rule)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "booking_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of booking IDs to cancel",
                }
            },
            "required": ["booking_ids"],
        },
    },
    # ── Location ──────────────────────────────────────────────────────────────
    {
        "name": "list_buildings",
        "description": "List all available office buildings the user can book in.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_floors",
        "description": "List floors in a specific building.",
        "input_schema": {
            "type": "object",
            "properties": {
                "building_id": {"type": "integer", "description": "ID of the building"}
            },
            "required": ["building_id"],
        },
    },
    # ── External context (partially integrated) ───────────────────────────────
    {
        "name": "get_team_workplans",
        "description": (
            "Find where colleagues plan to be on a given date (Tier 2 social context). "
            "Requires Microsoft Places connector. Returns 'not_integrated' status if "
            "the connector is not configured — inform the user and fall back to asking "
            "which building or floor the colleague will be on."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "ISO date"},
                "team": {"type": "string", "description": "Team name or colleague display name (optional)"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "get_building_occupancy",
        "description": (
            "Get forecast occupancy for a building on a given date (Tier 5). "
            "Returns 'not_integrated' status if occupancy data is unavailable — "
            "inform the user and reason from booking history instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "ISO date"},
                "building_id": {"type": "integer", "description": "Optional building filter"},
            },
            "required": ["date"],
        },
    },
    # ── Feedback ──────────────────────────────────────────────────────────────
    {
        "name": "submit_feedback",
        "description": "Submit post-visit feedback for a completed booking after collecting ratings from the user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "booking_id": {"type": "integer"},
                "user_id": {"type": "integer"},
                "rating": {"type": "integer", "description": "Overall experience rating 1–5"},
                "desk_comfort": {"type": "integer", "description": "Desk comfort rating 1–5 (optional)"},
                "noise_rating": {"type": "integer", "description": "Noise level satisfaction 1–5 (optional)"},
                "equipment_rating": {"type": "integer", "description": "Equipment quality rating 1–5 (optional)"},
                "comments": {"type": "string", "description": "Free-text comments (optional)"},
            },
            "required": ["booking_id", "user_id", "rating"],
        },
    },
    {
        "name": "get_completed_bookings",
        "description": "Retrieve a user's completed bookings so the agent can prompt for feedback on any not yet rated.",
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "required": ["user_id"],
        },
    },
]


def dispatch_tool(name: str, args: dict, auth_token: str = "") -> dict | list:
    handlers = {
        "get_user_profile": _get_user_profile,
        "update_user_profile": _update_user_profile,
        "check_desk_availability": _check_desk_availability,
        "book_desk": _book_desk,
        "check_room_availability": _check_room_availability,
        "book_room": _book_room,
        "list_my_bookings": _list_my_bookings,
        "get_booking_history": _get_booking_history,
        "cancel_booking": _cancel_booking,
        "cancel_multiple_bookings": _cancel_multiple_bookings,
        "list_buildings": _list_buildings,
        "list_floors": _list_floors,
        "get_team_workplans": _get_team_workplans,
        "get_building_occupancy": _get_building_occupancy,
        "submit_feedback": _submit_feedback,
        "get_completed_bookings": _get_completed_bookings,
    }
    _auth_token.set(auth_token)
    handler = handlers.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        sig = inspect.signature(handler)
        filtered = {k: v for k, v in args.items() if k in sig.parameters}
        return handler(**filtered)
    except httpx.HTTPStatusError as exc:
        return {"error": f"Backend error {exc.response.status_code}: {exc.response.text}"}
    except httpx.RequestError as exc:
        return {"error": f"Could not reach backend: {exc}"}


# ── Profile ───────────────────────────────────────────────────────────────────

def _get_user_profile(user_id: int) -> dict:
    resp = _client.get(f"/users/{user_id}")
    resp.raise_for_status()
    return resp.json()


def _update_user_profile(user_id: int, fields: dict) -> dict:
    resp = _client.patch(f"/users/{user_id}/preferences", json=fields)
    resp.raise_for_status()
    return resp.json()


# ── Availability and booking ──────────────────────────────────────────────────

def _check_desk_availability(
    date: str,
    building_id: int | None = None,
    floor_id: int | None = None,
    has_standing_desk: bool | None = None,
    min_monitors: int | None = None,
    has_docking_station: bool | None = None,
    is_accessible: bool | None = None,
    is_window_seat: bool | None = None,
    has_ultrawide: bool | None = None,
) -> list:
    params: dict = {"date": date}
    if building_id:
        params["building_id"] = building_id
    if floor_id:
        params["floor_id"] = floor_id
    if has_standing_desk is not None:
        params["has_standing_desk"] = has_standing_desk
    if min_monitors is not None:
        params["min_monitors"] = min_monitors
    if has_docking_station is not None:
        params["has_docking_station"] = has_docking_station
    if is_accessible is not None:
        params["is_accessible"] = is_accessible
    if is_window_seat is not None:
        params["is_window_seat"] = is_window_seat
    if has_ultrawide is not None:
        params["has_ultrawide"] = has_ultrawide
    resp = _client.get("/desks/available", params=params)
    resp.raise_for_status()
    return resp.json()


def _book_desk(user_id: int, desk_id: int, date: str) -> dict:
    resp = _client.post(
        "/bookings/",
        json={"user_id": user_id, "desk_id": desk_id, "date": date, "booking_source": "agent_ai"},
    )
    resp.raise_for_status()
    return resp.json()


def _check_room_availability(
    date: str, start_time: str, end_time: str, min_capacity: int = 1
) -> list:
    resp = _client.get(
        "/rooms/available",
        params={"date": date, "start_time": start_time, "end_time": end_time, "min_capacity": min_capacity},
    )
    resp.raise_for_status()
    return resp.json()


def _book_room(user_id: int, room_id: int, date: str, start_time: str, end_time: str) -> dict:
    resp = _client.post(
        "/bookings/",
        json={
            "user_id": user_id,
            "room_id": room_id,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "booking_source": "agent_ai",
        },
    )
    resp.raise_for_status()
    return resp.json()


# ── Booking management ────────────────────────────────────────────────────────

def _list_my_bookings(user_id: int) -> list:
    resp = _client.get(f"/bookings/user/{user_id}")
    resp.raise_for_status()
    return resp.json()


def _get_booking_history(user_id: int) -> list:
    resp = _client.get(f"/bookings/user/{user_id}")
    resp.raise_for_status()
    return resp.json()


def _cancel_booking(booking_id: int) -> dict:
    resp = _client.delete(f"/bookings/{booking_id}")
    resp.raise_for_status()
    return resp.json()


def _cancel_multiple_bookings(booking_ids: list[int]) -> dict:
    results = []
    errors = []
    for booking_id in booking_ids:
        try:
            resp = _client.delete(f"/bookings/{booking_id}")
            resp.raise_for_status()
            results.append(resp.json())
        except httpx.HTTPStatusError as exc:
            errors.append({"booking_id": booking_id, "error": exc.response.text})
    return {"cancelled": results, "errors": errors}


# ── Location ──────────────────────────────────────────────────────────────────

def _list_buildings() -> list:
    resp = _client.get("/desks/buildings")
    resp.raise_for_status()
    return resp.json()


def _list_floors(building_id: int) -> list:
    resp = _client.get("/desks/floors", params={"building_id": building_id})
    resp.raise_for_status()
    return resp.json()


# ── External context stubs ────────────────────────────────────────────────────

def _get_team_workplans(date: str, team: str | None = None) -> dict:
    return {
        "status": "not_integrated",
        "message": (
            "Team workplan data is not yet available. "
            "Microsoft Places connector has not been configured for this tenant."
        ),
    }


def _get_building_occupancy(date: str, building_id: int | None = None) -> dict:
    return {
        "status": "not_integrated",
        "message": (
            "Building occupancy forecast is not yet available. "
            "Occupancy sensor integration has not been configured."
        ),
    }


# ── Feedback ──────────────────────────────────────────────────────────────────

def _submit_feedback(
    booking_id: int,
    user_id: int,
    rating: int,
    desk_comfort: int | None = None,
    noise_rating: int | None = None,
    equipment_rating: int | None = None,
    comments: str | None = None,
) -> dict:
    payload: dict = {"booking_id": booking_id, "user_id": user_id, "rating": rating}
    if desk_comfort is not None:
        payload["desk_comfort"] = desk_comfort
    if noise_rating is not None:
        payload["noise_rating"] = noise_rating
    if equipment_rating is not None:
        payload["equipment_rating"] = equipment_rating
    if comments is not None:
        payload["comments"] = comments
    resp = _client.post("/feedback/", json=payload)
    resp.raise_for_status()
    return resp.json()


def _get_completed_bookings(user_id: int) -> list:
    bookings = _client.get(f"/bookings/user/{user_id}").raise_for_status().json()
    return [b for b in bookings if b.get("status") in ("completed", "allocated", "confirmed")]
