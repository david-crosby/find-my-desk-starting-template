#!/usr/bin/env python3
"""
Microsoft Places client for interacting with the Graph API.
Handles workspace retrieval, availability checking, and booking creation.
"""

import os
from typing import Any

import requests
from sqlalchemy.orm import Session

# We import the local database models to fallback for tags
from places_core.models import Desk

TENANT_ID = os.getenv("MS_PLACES_TENANT_ID")
CLIENT_ID = os.getenv("MS_PLACES_CLIENT_ID")
CLIENT_SECRET = os.getenv("MS_PLACES_CLIENT_SECRET")


def _get_graph_token() -> str:
    """Retrieves an app-only access token for Microsoft Graph via MSAL credentials."""
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    response = requests.post(url, data=payload, timeout=10)
    response.raise_for_status()
    return response.json()["access_token"]


def get_available_desks(
    building: str, start_time: str, end_time: str, db: Session
) -> list[dict[str, Any]]:
    """
    Queries Microsoft Graph for workspaces in a given building, checks their
    availability, and falls back to the local SQLite database for metadata tags.
    """
    token = _get_graph_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # 1. Fetch workspaces from Places API
    places_url = "https://graph.microsoft.com/beta/places/microsoft.graph.workspace"
    response = requests.get(places_url, headers=headers, timeout=10)
    response.raise_for_status()
    workspaces = response.json().get("value", [])

    # Filter by building 
    filtered_workspaces = [
        w for w in workspaces if w.get("building") == building
    ]

    if not filtered_workspaces:
        return []

    # Extract emails to check availability
    desk_emails = [
        w["emailAddress"] for w in filtered_workspaces if "emailAddress" in w
    ]
    if not desk_emails:
        return []

    # 2. Check Availability via getSchedule
    schedule_url = f"https://graph.microsoft.com/v1.0/users/{desk_emails[0]}/calendar/getSchedule"
    schedule_payload = {
        "schedules": desk_emails,
        "startTime": {"dateTime": start_time, "timeZone": "UTC"},
        "endTime": {"dateTime": end_time, "timeZone": "UTC"},
        "availabilityViewInterval": 60,
    }

    schedule_resp = requests.post(
        schedule_url, headers=headers, json=schedule_payload, timeout=10
    )
    schedule_resp.raise_for_status()
    schedules = schedule_resp.json().get("value", [])

    available_emails = set()
    for schedule in schedules:
        events = schedule.get("scheduleItems", [])
        # If there are no busy events, the desk is considered available
        is_busy = any(
            item.get("status") in ["busy", "tentative", "oof"] for item in events
        )
        if not is_busy:
            available_emails.add(schedule["scheduleId"])

    # 3. Fallback to SQLite for metadata tags
    available_desks = []
    for workspace in filtered_workspaces:
        email = workspace.get("emailAddress")
        if email in available_emails:
            desk_metadata = db.query(Desk).filter(Desk.desk_email_address == email).first()

            tags = []
            desk_zone = None

            if desk_metadata:
                desk_zone = desk_metadata.section.name if desk_metadata.section else None
                if desk_metadata.is_window_seat:
                    tags.append("Window")
                if desk_metadata.section and desk_metadata.section.name == "Quiet Zone":
                    tags.append("Quiet")
                if desk_metadata.has_dual_monitors:
                    tags.append("Collaboration") 

            available_desks.append({
                "email": email,
                "display_name": workspace.get("displayName", "Unknown Desk"),
                "zone": desk_zone,
                "tags": tags,
            })

    return available_desks


def book_desk(user_upn: str, desk_email: str, start_time: str, end_time: str) -> dict[str, Any]:
    """
    Creates a calendar event on the user's Graph calendar with the desk as an attendee.
    """
    token = _get_graph_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    events_url = f"https://graph.microsoft.com/v1.0/users/{user_upn}/events"
    event_payload = {
        "subject": "DeskMate Booking",
        "start": {"dateTime": start_time, "timeZone": "UTC"},
        "end": {"dateTime": end_time, "timeZone": "UTC"},
        "attendees": [
            {"emailAddress": {"address": desk_email}, "type": "resource"}
        ],
        "showAs": "free", # Allows user's calendar to not be completely blocked
    }

    response = requests.post(
        events_url, headers=headers, json=event_payload, timeout=10
    )
    response.raise_for_status()
    return response.json()