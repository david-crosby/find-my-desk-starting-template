"""
Microsoft Places / Graph API client.

MS Places is the single source of truth for all desk and room inventory and
all booking data.  This client handles:
  - App-only authentication (client credentials via MSAL)
  - Workspace (desk) inventory from MS Places
  - Room inventory from MS Places
  - Availability checking via Exchange getSchedule
  - Booking creation / cancellation via Exchange calendar events
  - User calendar queries
  - Team presence (batch)

All methods raise httpx.HTTPStatusError on non-2xx responses and
RuntimeError if authentication fails.
"""
from __future__ import annotations

import httpx
from msal import ConfidentialClientApplication

from .settings import settings

_GRAPH_V1 = "https://graph.microsoft.com/v1.0"
_GRAPH_BETA = "https://graph.microsoft.com/beta"
_SCOPE = ["https://graph.microsoft.com/.default"]

# Well-known ID for the Global Administrator directory role in Entra ID.
GLOBAL_ADMIN_ROLE_WID = "62e90394-69f5-4237-9190-012177145e10"


class PlacesClient:
    """
    Microsoft Places + Graph API client using app-only (client credentials) auth.

    Instantiate once per process via get_places_client().
    """

    def __init__(self) -> None:
        if not all([settings.azure_tenant_id, settings.azure_client_id, settings.azure_client_secret]):
            raise RuntimeError(
                "AZURE_TENANT_ID, AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET must all be set "
                "before using the MS Places client."
            )
        self._msal = ConfidentialClientApplication(
            client_id=settings.azure_client_id,
            client_credential=settings.azure_client_secret,
            authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
        )

    # ── Auth ─────────────────────────────────────────────────────────────────

    def _token(self) -> str:
        result = self._msal.acquire_token_for_client(scopes=_SCOPE)
        if "access_token" not in result:
            raise RuntimeError(
                f"MS Graph app-only auth failed: {result.get('error_description', result)}"
            )
        return result["access_token"]

    def _h(self) -> dict:
        return {"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"}

    # ── Workspace (desk) inventory ────────────────────────────────────────────

    def list_workspaces(self, building: str | None = None) -> list[dict]:
        """
        Return all bookable workspaces from MS Places.
        GET /beta/places/microsoft.graph.workspace
        Each item: id, displayName, building, floorNumber, floorLabel,
        emailAddress, isWheelChairAccessible, tags.
        """
        resp = httpx.get(
            f"{_GRAPH_BETA}/places/microsoft.graph.workspace",
            headers=self._h(),
            params={"$top": 999},
        )
        resp.raise_for_status()
        workspaces = resp.json().get("value", [])
        if building:
            workspaces = [w for w in workspaces if w.get("building") == building]
        return workspaces

    # ── Room inventory ────────────────────────────────────────────────────────

    def list_rooms(self, building: str | None = None) -> list[dict]:
        """
        Return all rooms from MS Places.
        GET /beta/places/microsoft.graph.room
        Each item: id, displayName, building, floorNumber, capacity, emailAddress.
        """
        resp = httpx.get(
            f"{_GRAPH_BETA}/places/microsoft.graph.room",
            headers=self._h(),
            params={"$top": 999},
        )
        resp.raise_for_status()
        rooms = resp.json().get("value", [])
        if building:
            rooms = [r for r in rooms if r.get("building") == building]
        return rooms

    # ── Availability ──────────────────────────────────────────────────────────

    def check_availability(
        self,
        resource_emails: list[str],
        start_datetime: str,
        end_datetime: str,
        timezone: str = "GMT Standard Time",
    ) -> dict[str, bool]:
        """
        Check availability for a list of desk or room resource mailboxes via
        Exchange getSchedule.  Returns {email: is_available}.

        start_datetime / end_datetime: ISO 8601 without timezone suffix,
        e.g. "2026-05-12T09:00:00".
        """
        if not resource_emails:
            return {}

        organiser = resource_emails[0]
        resp = httpx.post(
            f"{_GRAPH_V1}/users/{organiser}/calendar/getSchedule",
            headers=self._h(),
            json={
                "schedules": resource_emails,
                "startTime": {"dateTime": start_datetime, "timeZone": timezone},
                "endTime": {"dateTime": end_datetime, "timeZone": timezone},
                "availabilityViewInterval": 60,
            },
        )
        resp.raise_for_status()

        result: dict[str, bool] = {}
        for schedule in resp.json().get("value", []):
            busy = any(
                item.get("status") in ("busy", "tentative", "oof")
                for item in schedule.get("scheduleItems", [])
            )
            result[schedule["scheduleId"]] = not busy
        return result

    def get_available_workspaces(
        self,
        start_datetime: str,
        end_datetime: str,
        building: str | None = None,
    ) -> list[dict]:
        """
        Return workspaces that are free for the requested time window.
        Combines list_workspaces + check_availability into a single call.
        """
        workspaces = self.list_workspaces(building=building)
        emails = [w["emailAddress"] for w in workspaces if "emailAddress" in w]
        if not emails:
            return []
        availability = self.check_availability(emails, start_datetime, end_datetime)
        return [w for w in workspaces if availability.get(w.get("emailAddress")) is True]

    # ── Booking via Exchange calendar event ───────────────────────────────────

    def book_workspace(
        self,
        user_upn: str,
        desk_email: str,
        start_datetime: str,
        end_datetime: str,
        subject: str = "DeskMate Desk Booking",
        timezone: str = "GMT Standard Time",
    ) -> dict:
        """
        Create a calendar event on the user's Exchange calendar with the desk
        resource mailbox as a resource attendee.  MS Places registers this as a
        workspace booking.

        POST /v1.0/users/{user_upn}/events
        Returns the created event — store event["id"] as ms_reservation_id.
        """
        resp = httpx.post(
            f"{_GRAPH_V1}/users/{user_upn}/events",
            headers=self._h(),
            json={
                "subject": subject,
                "start": {"dateTime": start_datetime, "timeZone": timezone},
                "end": {"dateTime": end_datetime, "timeZone": timezone},
                "attendees": [
                    {"emailAddress": {"address": desk_email}, "type": "resource"}
                ],
                "showAs": "free",
                "isOnlineMeeting": False,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def book_room(
        self,
        user_upn: str,
        room_email: str,
        start_datetime: str,
        end_datetime: str,
        subject: str = "DeskMate Meeting Room Booking",
        timezone: str = "GMT Standard Time",
    ) -> dict:
        """
        Book a meeting room by creating an Outlook calendar event.

        POST /v1.0/users/{user_upn}/events
        Returns the created event — store event["id"] as ms_reservation_id.
        """
        resp = httpx.post(
            f"{_GRAPH_V1}/users/{user_upn}/events",
            headers=self._h(),
            json={
                "subject": subject,
                "start": {"dateTime": start_datetime, "timeZone": timezone},
                "end": {"dateTime": end_datetime, "timeZone": timezone},
                "attendees": [
                    {"emailAddress": {"address": room_email}, "type": "resource"}
                ],
                "isOnlineMeeting": False,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def cancel_booking(self, user_upn: str, event_id: str) -> None:
        """
        Cancel a booking by deleting the Exchange calendar event.
        DELETE /v1.0/users/{user_upn}/events/{event_id}
        """
        httpx.delete(
            f"{_GRAPH_V1}/users/{user_upn}/events/{event_id}",
            headers=self._h(),
        ).raise_for_status()

    # ── User calendar ─────────────────────────────────────────────────────────

    def get_user_calendar(self, user_upn: str, date: str) -> list[dict]:
        """
        Return calendar events for a user on a given date (YYYY-MM-DD).
        GET /v1.0/users/{upn}/calendarView
        """
        resp = httpx.get(
            f"{_GRAPH_V1}/users/{user_upn}/calendarView",
            headers=self._h(),
            params={
                "startDateTime": f"{date}T00:00:00Z",
                "endDateTime": f"{date}T23:59:59Z",
                "$select": "id,subject,start,end,location,attendees,showAs",
                "$top": 50,
            },
        )
        resp.raise_for_status()
        return resp.json().get("value", [])

    # ── Team presence & workplans ─────────────────────────────────────────────

    def get_presence_batch(self, entra_ids: list[str]) -> list[dict]:
        """
        Return current presence for up to 650 users.
        POST /v1.0/communications/getPresencesByUserId
        Each result: {id, availability, activity}.
        """
        resp = httpx.post(
            f"{_GRAPH_V1}/communications/getPresencesByUserId",
            headers=self._h(),
            json={"ids": entra_ids[:650]},
        )
        resp.raise_for_status()
        return resp.json().get("value", [])

    def get_team_workplans(self, date: str, entra_ids: list[str]) -> list[dict]:
        """
        Return workspace bookings for a list of users on a given date by
        inspecting each user's calendar for resource-attendee events (desk bookings).
        """
        workplans = []
        for uid in entra_ids:
            try:
                events = self.get_user_calendar(uid, date)
                desk_events = [
                    e for e in events
                    if any(a.get("type") == "resource" for a in e.get("attendees", []))
                ]
                if desk_events:
                    workplans.append({"user_id": uid, "date": date, "bookings": desk_events})
            except httpx.HTTPStatusError:
                pass
        return workplans

    # ── Group membership ──────────────────────────────────────────────────────

    def get_group_members(self, group_id: str) -> list[dict]:
        """Return members of an Entra ID group. GET /v1.0/groups/{id}/members"""
        resp = httpx.get(
            f"{_GRAPH_V1}/groups/{group_id}/members",
            headers=self._h(),
            params={"$select": "id,displayName,mail"},
        )
        resp.raise_for_status()
        return resp.json().get("value", [])


# ── Module-level singleton ────────────────────────────────────────────────────

_client: PlacesClient | None = None


def get_places_client() -> PlacesClient:
    """Return the shared PlacesClient instance (lazy-initialised)."""
    global _client
    if _client is None:
        _client = PlacesClient()
    return _client
