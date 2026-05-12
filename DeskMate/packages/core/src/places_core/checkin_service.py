"""
Peripheral check-in service.

Called when a user connects a monitor that is registered as a DeskMate
peripheral check-in device. Implements four outcome paths:

  checked_in  — user's booking matches this desk; booking marked checked_in.
  reassigned  — user has a booking for a different desk; this desk is free,
                so the booking is moved here and the user is notified.
  conflict    — this desk is booked by a different user; the connecting user
                is notified and their booking is untouched.
  no_booking  — user has no booking today; they are notified.
"""
from datetime import date

from sqlalchemy.orm import Session

from .models import Booking, Desk, DeskMonitor, PeripheralCheckIn, User
from .teams_notify import send_desk_alert


def _desk_label(desk: Desk) -> str:
    section = desk.section
    floor = section.floor if section else None
    building = floor.building if floor else None
    parts = [desk.label]
    if section:
        parts.append(section.zone_label or section.name)
    if floor:
        parts.append(floor.name or f"Floor {floor.number}")
    if building:
        parts.append(building.name)
    return ", ".join(parts)


def _active_booking_for_user(db: Session, user_id: int, date_str: str) -> Booking | None:
    return (
        db.query(Booking)
        .filter(
            Booking.user_id == user_id,
            Booking.date == date_str,
            Booking.status.in_(["allocated", "confirmed", "queued", "checked_in"]),
        )
        .first()
    )


def _booking_on_desk(db: Session, desk_id: int, date_str: str) -> Booking | None:
    return (
        db.query(Booking)
        .filter(
            Booking.desk_id == desk_id,
            Booking.date == date_str,
            Booking.status.in_(["allocated", "confirmed", "checked_in"]),
        )
        .first()
    )


def process_peripheral_checkin(
    db: Session,
    device_id: str,
    entra_id: str,
    method: str = "peripheral",
) -> dict:
    """
    Core check-in logic. Returns a result dict with at minimum an 'outcome' key.
    """
    today = date.today().isoformat()

    # ── Resolve device → desk ─────────────────────────────────────────────────
    monitor = db.query(DeskMonitor).filter(DeskMonitor.device_id == device_id).first()
    if not monitor:
        return {"outcome": "error", "reason": "unknown_device", "device_id": device_id}

    desk = db.get(Desk, monitor.desk_id)
    if not desk:
        return {"outcome": "error", "reason": "desk_not_found"}

    # ── Resolve user ──────────────────────────────────────────────────────────
    user = db.query(User).filter(User.entra_id == entra_id).first()
    if not user:
        return {"outcome": "error", "reason": "unknown_user", "entra_id": entra_id}

    desk_display = _desk_label(desk)
    user_booking = _active_booking_for_user(db, user.id, today)
    desk_booking = _booking_on_desk(db, desk.id, today)

    event = PeripheralCheckIn(
        user_id=user.id,
        desk_id=desk.id,
        device_id=device_id,
        method=method,
        outcome="checked_in",  # will be overwritten below
    )

    # ── Case 1: correct desk ──────────────────────────────────────────────────
    if user_booking and user_booking.desk_id == desk.id:
        user_booking.status = "checked_in"
        event.booking_id = user_booking.id
        event.outcome = "checked_in"
        db.add(event)
        db.commit()
        return {"outcome": "checked_in", "desk": desk_display, "user": user.display_name}

    # ── Case 2: wrong desk but this desk is free — reassign ──────────────────
    if user_booking and (desk_booking is None or desk_booking.user_id == user.id):
        original_desk_id = user_booking.desk_id
        user_booking.desk_id = desk.id
        user_booking.status = "checked_in"
        event.booking_id = user_booking.id
        event.outcome = "reassigned"
        event.was_reassigned = True
        event.original_desk_id = original_desk_id
        db.add(event)
        db.commit()

        sent = send_desk_alert(
            entra_id=user.entra_id or "",
            subject="Desk booking moved",
            body=(
                f"Hi {user.display_name}, you connected to {desk_display} — "
                "your desk booking has been automatically moved here. "
                "No further action needed."
            ),
        )
        event.notification_sent = sent
        db.commit()
        return {
            "outcome": "reassigned",
            "desk": desk_display,
            "user": user.display_name,
            "original_desk_id": original_desk_id,
            "notification_sent": sent,
        }

    # ── Case 3: desk booked by someone else — conflict ────────────────────────
    if desk_booking and desk_booking.user_id != user.id:
        booked_by = db.get(User, desk_booking.user_id)
        event.outcome = "conflict"
        event.conflict_user_id = booked_by.id if booked_by else None
        if user_booking:
            event.booking_id = user_booking.id
        db.add(event)
        db.commit()

        sent = send_desk_alert(
            entra_id=user.entra_id or "",
            subject="Desk already booked",
            body=(
                f"Hi {user.display_name}, {desk_display} is booked by "
                f"{booked_by.display_name if booked_by else 'another colleague'} today. "
                "Please move to your assigned desk or book an available one."
            ),
        )
        event.notification_sent = sent
        db.commit()
        return {
            "outcome": "conflict",
            "desk": desk_display,
            "user": user.display_name,
            "booked_by": booked_by.display_name if booked_by else None,
            "notification_sent": sent,
        }

    # ── Case 4: no booking ────────────────────────────────────────────────────
    event.outcome = "no_booking"
    db.add(event)
    db.commit()

    sent = send_desk_alert(
        entra_id=user.entra_id or "",
        subject="No desk booking found",
        body=(
            f"Hi {user.display_name}, you connected to {desk_display} but have no desk "
            "booking for today. Use DeskMate to book a desk so your attendance is recorded."
        ),
    )
    event.notification_sent = sent
    db.commit()
    return {
        "outcome": "no_booking",
        "desk": desk_display,
        "user": user.display_name,
        "notification_sent": sent,
    }
