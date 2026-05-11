#!/usr/bin/env python3
"""
APScheduler script to run the nightly allocation engine at the scheduled time.
"""

import os
import sys
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

# Add project root to path to allow imports from other packages
sys.path.insert(0, str(Path(__file__).parent))

from allocation.run import run_nightly_allocation
from places_core.db import SessionLocal

# Load environment variables from .env file
load_dotenv()


def allocation_job():
    """
    Wrapper function for the nightly allocation job.

    This creates a new database session for the job run and ensures it is
    closed properly, whether the job succeeds or fails.
    """
    print("Scheduler starting allocation job...")
    db_session = SessionLocal()
    try:
        run_nightly_allocation(db_session)
        db_session.commit()
        print("Allocation job finished successfully and changes committed.")
    except Exception as e:
        print(f"An error occurred during scheduled allocation: {e}")
        db_session.rollback()
    finally:
        db_session.close()
        print("Database session closed.")


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="UTC")
    run_time = os.getenv("ALLOCATION_RUN_TIME", "23:00")
    hour, minute = map(int, run_time.split(":"))

    scheduler.add_job(allocation_job, "cron", hour=hour, minute=minute)

    print(f"Scheduler started. Allocation job is scheduled to run daily at {run_time} UTC.")
    print("Press Ctrl+C to exit.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()