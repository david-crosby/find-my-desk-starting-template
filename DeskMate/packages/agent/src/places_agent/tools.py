import httpx

from places_core.settings import settings

_client = httpx.Client(base_url=settings.backend_url, timeout=10.0)

TOOLS: list[dict] = [
    {
        "name": "check_desk_availability",
        "description": "List available desks for a given date, optionally filtered by floor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "ISO date, e.g. 2025-06-01"},
                "floor_id": {"type": "integer", "description": "Optional floor filter"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "book_desk",
        "description": "Book a specific desk for a user on a date. The booking is queued and confirmed overnight.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer"},
                "desk_id": {"type": "integer"},
                "date": {"type": "string"},
            },
            "required": ["user_id", "desk_id", "date"],
        },
    },
    {
        "name": "check_room_availability",
        "description": "List available meeting rooms for a time slot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "start_time": {"type": "string", "description": "HH:MM"},
                "end_time": {"type": "string", "description": "HH:MM"},
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
                "start_time": {"type": "string"},
                "end_time": {"type": "string"},
            },
            "required": ["user_id", "room_id", "date", "start_time", "end_time"],
        },
    },
    {
        "name": "list_my_bookings",
        "description": "Retrieve all bookings for a given user.",
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "required": ["user_id"],
        },
    },
    {
        "name": "cancel_booking",
        "description": "Cancel an existing booking by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"booking_id": {"type": "integer"}},
            "required": ["booking_id"],
        },
    },
    {
        "name": "list_buildings",
        "description": "List all available office buildings the user can book in.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_floors",
        "description": "List floors in a specific building.",
        "input_schema": {
            "type": "object",
            "properties": {
                "building_id": {
                    "type": "integer",
                    "description": "ID of the building to list floors for",
                }
            },
            "required": ["building_id"],
        },
    },
    {
        "name": "get_user_profile",
        "description": (
            "Fetch a user's profile including their home building, floor, preferred "
            "noise level, equipment requirements, and other booking preferences."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "required": ["user_id"],
        },
    },
    {
        "name": "submit_feedback",
        "description": (
            "Submit post-visit feedback for a completed booking. "
            "Call this after collecting ratings from the user."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "booking_id": {"type": "integer"},
                "user_id": {"type": "integer"},
                "rating": {
                    "type": "integer",
                    "description": "Overall experience rating 1-5",
                },
                "desk_comfort": {
                    "type": "integer",
                    "description": "Desk comfort rating 1-5 (optional)",
                },
                "noise_rating": {
                    "type": "integer",
                    "description": "Noise level satisfaction 1-5 (optional)",
                },
                "equipment_rating": {
                    "type": "integer",
                    "description": "Equipment quality rating 1-5 (optional)",
                },
                "comments": {
                    "type": "string",
                    "description": "Free-text comments (optional)",
                },
            },
            "required": ["booking_id", "user_id", "rating"],
        },
    },
    {
        "name": "get_completed_bookings",
        "description": (
            "Retrieve a user's completed bookings so the agent can prompt for "
            "feedback on any that have not yet been rated."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "required": ["user_id"],
        },
    },
]


def dispatch_tool(name: str, args: dict) -> dict | list:
    handlers = {
        "check_desk_availability": _check_desk_availability,
        "book_desk": _book_desk,
        "check_room_availability": _check_room_availability,
        "book_room": _book_room,
        "list_my_bookings": _list_my_bookings,
        "cancel_booking": _cancel_booking,
        "list_buildings": _list_buildings,
        "list_floors": _list_floors,
        "get_user_profile": _get_user_profile,
        "submit_feedback": _submit_feedback,
        "get_completed_bookings": _get_completed_bookings,
    }
    handler = handlers.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return handler(**args)
    except httpx.HTTPStatusError as exc:
        return {"error": f"Backend error {exc.response.status_code}: {exc.response.text}"}
    except httpx.RequestError as exc:
        return {"error": f"Could not reach backend: {exc}"}


def _check_desk_availability(date: str, floor_id: int | None = None) -> list:
    params: dict = {"date": date}
    if floor_id:
        params["floor_id"] = floor_id
    resp = _client.get("/desks/available", params=params)
    resp.raise_for_status()
    return resp.json()


def _book_desk(user_id: int, desk_id: int, date: str) -> dict:
    resp = _client.post(
        "/bookings/",
        json={
            "user_id": user_id,
            "desk_id": desk_id,
            "date": date,
            "booking_source": "agent_ai",
        },
    )
    resp.raise_for_status()
    return resp.json()


def _check_room_availability(
    date: str, start_time: str, end_time: str, min_capacity: int = 1
) -> list:
    resp = _client.get(
        "/rooms/available",
        params={
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "min_capacity": min_capacity,
        },
    )
    resp.raise_for_status()
    return resp.json()


def _book_room(
    user_id: int, room_id: int, date: str, start_time: str, end_time: str
) -> dict:
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


def _list_my_bookings(user_id: int) -> list:
    resp = _client.get(f"/bookings/user/{user_id}")
    resp.raise_for_status()
    return resp.json()


def _cancel_booking(booking_id: int) -> dict:
    resp = _client.delete(f"/bookings/{booking_id}")
    resp.raise_for_status()
    return resp.json()


def _list_buildings() -> list:
    resp = _client.get("/admin/buildings")
    resp.raise_for_status()
    return resp.json()


def _list_floors(building_id: int) -> list:
    resp = _client.get("/admin/floors", params={"building_id": building_id})
    resp.raise_for_status()
    return resp.json()


def _get_user_profile(user_id: int) -> dict:
    resp = _client.get(f"/users/{user_id}")
    resp.raise_for_status()
    return resp.json()


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
