#!/usr/bin/env python3
"""Nightly allocation engine to process queued desk bookings."""

import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy.orm import Session, joinedload

# Add project root to path to allow imports from other packages
sys.path.insert(0, str(Path(__file__).parent.parent))

from allocation import allocate_desk
from places_core.db import SessionLocal
from places_core.models import Allocation, Booking, Desk, Section
from places_core.services.notifications import send_allocation_notification, send_waitlist_notification


def run_nightly_allocation(db: Session):
    """
    Processes all 'queued' bookings for the following day and allocates the
    best available desk based on user preferences.
    """
    tomorrow = date.today() + timedelta(days=1)
    tomorrow_str = tomorrow.isoformat()
    print(f"--- Running nightly allocation for {tomorrow_str} ---")

    # 1. Get all bookings queued for tomorrow, ordered by request time
    queued_bookings = (
        db.query(Booking)
        .options(joinedload(Booking.user))
        .filter(Booking.date == tomorrow_str, Booking.status == "queued")
        .order_by(Booking.requested_at)
        .all()
    )

    if not queued_bookings:
        print("No queued bookings to process. Exiting.")
        return

    print(f"Found {len(queued_bookings)} bookings to process.")

    # 2. Get all desks that are already booked for tomorrow
    booked_desk_ids = {
        row[0]
        for row in db.query(Booking.desk_id).filter(
            Booking.date == tomorrow_str,
            Booking.desk_id.isnot(None),
            Booking.status.in_(["allocated", "confirmed"]),
        )
    }

    # 3. Get all active desks and filter out the already booked ones
    all_desks = (
        db.query(Desk)
        .options(joinedload(Desk.section).joinedload(Section.building))
        .filter(Desk.is_active == True)
        .all()
    )
    available_desks = [d for d in all_desks if d.id not in booked_desk_ids]
    desk_map_by_email = {d.desk_email_address: d for d in all_desks}

    processed_count = 0
    allocated_count = 0

    # 4. Process each booking
    for booking in queued_bookings:
        print(f"Processing booking ID {booking.id} for user {booking.user.email}...")

        if not available_desks:
            print("  -> No desks available. Marking as waitlisted.")
            booking.status = "waitlisted"
            continue

        # 5. Find the best desk from the currently available pool
        best_desk_email, match_score = allocate_desk(
            booking.user.entra_id, available_desks, db, tomorrow
        )

        if best_desk_email and (allocated_desk := desk_map_by_email.get(best_desk_email)):
            print(f"  -> Allocated desk: {best_desk_email} with score {match_score:.2f}%")
            booking.status = "allocated"
            booking.desk_id = allocated_desk.id
            booking.desk = allocated_desk  # Associate object for notification

            db.add(Allocation(booking_id=booking.id, desk_id=allocated_desk.id, score=match_score, allocation_run_date=date.today()))

            # Send confirmation notification
            send_allocation_notification(booking)

            available_desks = [d for d in available_desks if d.id != allocated_desk.id]
            allocated_count += 1
        else:
            print("  -> No suitable desk found. Marking as waitlisted.")
            booking.status = "waitlisted"
            send_waitlist_notification(booking)

        processed_count += 1

    print("\n--- Allocation run complete ---")
    print(f"Processed: {processed_count} bookings")
    print(f"Allocated: {allocated_count} desks")
    print(f"Waitlisted: {processed_count - allocated_count} bookings")


if __name__ == "__main__":
    db_session = SessionLocal()
    try:
        run_nightly_allocation(db_session)
        db_session.commit()
    except Exception as e:
        print(f"An error occurred during allocation: {e}")
        db_session.rollback()
    finally:
        db_session.close()