"""
Auto-release service.

Runs periodically via the backend scheduler. Finds desk bookings whose
check-in cutoff has passed without a check-in and marks them as no_show,
freeing the desk for walk-in bookings or re-allocation.

Cutoff rules (all configurable in OrgRules):
  All-day booking (no start_time): checkin_cutoff_allday  default 10:00
  AM booking (start_time < 12:00): checkin_cutoff_am      default 10:00
  PM booking (start_time >= 12:00): checkin_cutoff_pm     default 14:00
"""
from datetime import datetime

from sqlalchemy.orm import Session

from .calendar_service import delete_calendar_event
from .models import Booking, OrgRules
from .teams_notify import send_desk_alert


def _booking_type(booking: Booking) -> str:
    if not booking.start_time:
        return "allday"
    return "am" if booking.start_time < "12:00" else "pm"


def _cutoff_for(booking: Booking, rules: OrgRules) -> str:
    btype = _booking_type(booking)
    if btype == "am":
        return rules.checkin_cutoff_am
    if btype == "pm":
        return rules.checkin_cutoff_pm
    return rules.checkin_cutoff_allday


def run_auto_release(db: Session) -> dict:
    """
    Release all qualifying unchecked bookings for today.
    Safe to call repeatedly — processed bookings move to no_show and are
    excluded from subsequent runs.
    """
    rules = db.get(OrgRules, 1)
    if not rules or not rules.enable_auto_release:
        return {"released": 0, "skipped": True}

    now = datetime.now()
    today = now.date().isoformat()
    current_hhmm = now.strftime("%H:%M")

    # Active bookings for today with an assigned desk that haven't been checked in
    candidates = (
        db.query(Booking)
        .filter(
            Booking.date == today,
            Booking.status.in_(["confirmed", "allocated"]),
            Booking.desk_id.isnot(None),
        )
        .all()
    )

    released_ids = []
    for booking in candidates:
        # Same-day bookings are exempt — the user booked knowing they were coming in
        if booking.booking_created_at and booking.booking_created_at.date().isoformat() == today:
            continue

        cutoff = _cutoff_for(booking, rules)
        if current_hhmm < cutoff:
            continue

        booking.status = "no_show"
        released_ids.append(booking.id)

        # Remove the Outlook calendar event
        try:
            delete_calendar_event(booking, db)
        except Exception:
            pass

        # Notify the user via Teams if integration is enabled
        if booking.user:
            user = booking.user
            desk = booking.desk
            desk_label = desk.label if desk else "your desk"
            send_desk_alert(
                entra_id=user.entra_id or "",
                subject="Desk booking released",
                body=(
                    f"Hi {user.display_name}, your booking for {desk_label} today was "
                    f"released at {cutoff} as no check-in was detected. "
                    "The desk is now available for others. Book again via DeskMate if you still need a space."
                ),
            )

    if released_ids:
        db.commit()

    return {"released": len(released_ids), "booking_ids": released_ids, "run_at": current_hhmm}
