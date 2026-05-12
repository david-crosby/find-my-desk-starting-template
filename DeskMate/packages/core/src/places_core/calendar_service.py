"""
Microsoft Graph calendar integration.

Creates, updates, and deletes Outlook calendar events when desk bookings are
made, allocated, or cancelled. Respects the user's calendar_sync_enabled flag.

Requires application permissions: Calendars.ReadWrite
Uses the same client-credentials token flow as teams_notify.py.

When ms_places_enabled=False (demo mode) all calls are silently skipped and
the function returns None — no calendar changes are made.
"""
import httpx

from .settings import settings

_GRAPH_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"

_DEFAULT_TZ = "UTC"
_AM_START = "08:00:00"
_AM_END = "12:00:00"
_PM_START = "13:00:00"
_PM_END = "17:00:00"
_ALLDAY_END_OFFSET = 1  # all-day events end at midnight next day


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
    except Exception:
        return None


def _desk_location(booking) -> str:
    desk = getattr(booking, "desk", None)
    if not desk:
        return "Desk TBD"
    parts = [desk.label]
    section = getattr(desk, "section", None)
    if section:
        parts.append(section.zone_label or section.name)
        floor = getattr(section, "floor", None)
        if floor:
            parts.append(floor.name or f"Floor {floor.number}")
            building = getattr(floor, "building", None)
            if building:
                parts.append(building.name)
    return ", ".join(parts)


def _desk_amenities_html(booking) -> str:
    desk = getattr(booking, "desk", None)
    if not desk:
        return ""
    tags = []
    if getattr(desk, "num_monitors", 1) > 1:
        tags.append(f"{desk.num_monitors} monitors")
    if getattr(desk, "has_docking_station", False):
        tags.append("docking station")
    if getattr(desk, "has_standing_desk", False):
        tags.append("sit-stand desk")
    if getattr(desk, "is_window_seat", False):
        tags.append("window seat")
    if getattr(desk, "is_accessible", False):
        tags.append("accessible")
    return (", ".join(tags)) if tags else ""


def _build_event_body(booking, is_provisional: bool) -> dict:
    date_str = booking.date
    location = _desk_location(booking)
    amenities = _desk_amenities_html(booking)

    if is_provisional:
        subject = f"DeskMate: Desk booking pending — {date_str}"
        status_line = "<p><strong>Status:</strong> Pending — your desk will be confirmed by the overnight allocation run.</p>"
    else:
        desk = getattr(booking, "desk", None)
        desk_label = desk.label if desk else "TBD"
        subject = f"DeskMate: {desk_label} — {date_str}"
        status_line = f"<p><strong>Status:</strong> Confirmed</p>"

    amenity_line = f"<p><strong>Amenities:</strong> {amenities}</p>" if amenities else ""
    body_html = (
        f"<p><strong>Location:</strong> {location}</p>"
        f"{status_line}"
        f"{amenity_line}"
        "<p>Check in via a registered monitor or through DeskMate when you arrive.</p>"
    )

    # Determine start/end times
    start_time = getattr(booking, "start_time", None)
    end_time = getattr(booking, "end_time", None)

    if not start_time:
        # All-day event
        from datetime import date, timedelta
        d = date.fromisoformat(date_str)
        next_d = d + timedelta(days=1)
        return {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_html},
            "start": {"dateTime": f"{date_str}T00:00:00", "timeZone": _DEFAULT_TZ},
            "end": {"dateTime": f"{next_d.isoformat()}T00:00:00", "timeZone": _DEFAULT_TZ},
            "isAllDay": True,
            "location": {"displayName": location},
            "showAs": "free" if is_provisional else "busy",
        }
    else:
        s = start_time if ":" in start_time else f"{start_time}:00"
        if end_time:
            e = end_time if ":" in end_time else f"{end_time}:00"
        else:
            e = _PM_END if start_time >= "12:00" else _AM_END
        return {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_html},
            "start": {"dateTime": f"{date_str}T{s}", "timeZone": _DEFAULT_TZ},
            "end": {"dateTime": f"{date_str}T{e}", "timeZone": _DEFAULT_TZ},
            "isAllDay": False,
            "location": {"displayName": location},
            "showAs": "free" if is_provisional else "busy",
        }


def create_calendar_event(booking, db) -> str | None:
    """
    Create an Outlook calendar event for the booking.
    Returns the Graph event ID, or None if not sent.
    """
    if not settings.ms_places_enabled:
        return None
    user = getattr(booking, "user", None)
    if not user or not user.entra_id:
        return None
    if not getattr(user, "calendar_sync_enabled", True):
        return None

    token = _get_app_token()
    if not token:
        return None

    is_provisional = not getattr(booking, "desk_id", None)
    payload = _build_event_body(booking, is_provisional=is_provisional)

    try:
        resp = httpx.post(
            f"{_GRAPH_BASE}/users/{user.entra_id}/events",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json().get("id")
    except Exception:
        return None


def update_calendar_event(booking, db) -> bool:
    """
    Update an existing Outlook calendar event with confirmed desk details.
    Called after the allocation engine assigns a desk.
    """
    if not settings.ms_places_enabled:
        return False
    event_id = getattr(booking, "graph_event_id", None)
    if not event_id:
        # No event to update — create a fresh one
        new_id = create_calendar_event(booking, db)
        if new_id:
            booking.graph_event_id = new_id
            db.commit()
        return bool(new_id)

    user = getattr(booking, "user", None)
    if not user or not user.entra_id:
        return False

    token = _get_app_token()
    if not token:
        return False

    payload = _build_event_body(booking, is_provisional=False)

    try:
        resp = httpx.patch(
            f"{_GRAPH_BASE}/users/{user.entra_id}/events/{event_id}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=10.0,
        )
        return resp.status_code in (200, 204)
    except Exception:
        return False


def delete_calendar_event(booking, db) -> bool:
    """
    Delete the Outlook calendar event when a booking is cancelled or auto-released.
    """
    if not settings.ms_places_enabled:
        return False
    event_id = getattr(booking, "graph_event_id", None)
    if not event_id:
        return False
    user = getattr(booking, "user", None)
    if not user or not user.entra_id:
        return False

    token = _get_app_token()
    if not token:
        return False

    try:
        resp = httpx.delete(
            f"{_GRAPH_BASE}/users/{user.entra_id}/events/{event_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        return resp.status_code in (200, 204)
    except Exception:
        return False
