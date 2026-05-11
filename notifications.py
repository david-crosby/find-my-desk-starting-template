#!/usr/bin/env python3
"""Notification service for sending updates to users."""

import os
from dotenv import load_dotenv
import requests

from places_core.models import Booking

# Load environment variables from .env file
load_dotenv()

NOTIFICATION_WEBHOOK_URL = os.getenv("NOTIFICATION_WEBHOOK_URL")


def send_allocation_notification(booking: Booking):
    """
    Sends a notification to the user about their allocated desk.

    For the POC, this sends a request to a webhook URL if configured,
    otherwise it prints to the console.
    """
    if not booking.user or not booking.desk:
        print(f"  -> [!] Cannot send notification for booking {booking.id}: missing user or desk info.")
        return

    # The desk object should have section and building eager-loaded
    desk = booking.desk
    section = desk.section
    building = section.building if section else None
    building_name = building.name if building else "Unknown Building"

    message = (
        f"Hi {booking.user.name},\n\n"
        f"Your desk booking for {booking.date} has been confirmed!\n\n"
        f"  Building: {building_name}\n"
        f"  Floor: {desk.floor}\n"
        f"  Desk: {desk.desk_email_address}\n\n"
        "You will be checked in automatically when you arrive."
    )

    if NOTIFICATION_WEBHOOK_URL:
        payload = {
            "user_email": booking.user.email,
            "subject": f"Your DeskMate Booking for {booking.date} is Confirmed",
            "body": message,
        }
        try:
            response = requests.post(NOTIFICATION_WEBHOOK_URL, json=payload, timeout=5)
            response.raise_for_status()
            print(f"  -> Sent notification to webhook for {booking.user.email}")
        except requests.RequestException as e:
            print(f"  -> [!] Failed to send webhook notification: {e}")
            # Fallback to console for resilience
            print("\n--- CONSOLE NOTIFICATION (WEBHOOK FAILED) ---")
            print(message)
            print("---------------------------------------------\n")
    else:
        # Fallback to console if no webhook is configured
        print("\n--- CONSOLE NOTIFICATION ---")
        print(message)
        print("----------------------------\n")


def send_waitlist_notification(booking: Booking):
    """
    Sends a notification to the user that they have been waitlisted.
    """
    if not booking.user:
        print(f"  -> [!] Cannot send notification for booking {booking.id}: missing user info.")
        return

    message = (
        f"Hi {booking.user.name},\n\n"
        f"Unfortunately, we could not find a suitable desk for your booking on {booking.date} "
        "as all available desks were taken. You have been added to the waitlist.\n\n"
        "If a desk becomes available later, we will notify you."
    )

    # This function would also use the webhook logic, but is simplified here.
    print("\n--- CONSOLE NOTIFICATION ---")
    print(message)
    print("----------------------------\n")