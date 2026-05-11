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
        "description": "Book a specific desk for a user on a date.",
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
        "description": "Book a meeting room for a user.",
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
]


def dispatch_tool(name: str, args: dict) -> dict | list:
    handlers = {
        "check_desk_availability": _check_desk_availability,
        "book_desk": _book_desk,
        "check_room_availability": _check_room_availability,
        "book_room": _book_room,
        "list_my_bookings": _list_my_bookings,
        "cancel_booking": _cancel_booking,
    }
    handler = handlers.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    return handler(**args)


def _check_desk_availability(date: str, floor_id: int | None = None) -> list:
    params: dict = {"date": date}
    if floor_id:
        params["floor_id"] = floor_id
    resp = _client.get("/desks/available", params=params)
    resp.raise_for_status()
    return resp.json()


def _book_desk(user_id: int, desk_id: int, date: str) -> dict:
    resp = _client.post("/bookings/", json={"user_id": user_id, "desk_id": desk_id, "date": date})
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
