#!/usr/bin/env python3
"""Entry-point script for the desk allocation engine.

All algorithm logic lives in places_core.allocation. This script provides
a convenient CLI for ad-hoc runs and local testing.
"""

import re
from datetime import date
from typing import Any

from places_core.allocation import (  # noqa: F401  (re-export for backwards compat)
    allocate_desk,
    run_nightly_allocation,
)
from places_core.db import SessionLocal
from places_core.models import Desk
from sqlalchemy.orm import joinedload


def translate_natural_language(query: str) -> dict[str, Any]:
    """Translate a natural language query into structured filter parameters."""
    params: dict[str, Any] = {"preferences": []}
    q = query.lower()

    if "quiet" in q or "silent" in q:
        params["preferences"].append("quiet-area")
    if "window" in q:
        params["preferences"].append("window-seat")
    if "stand" in q:
        params["preferences"].append("standing-desk")
    if "monitor" in q or "screen" in q:
        params["preferences"].append("dual-monitor")
    if "accessible" in q:
        params["preferences"].append("accessible-desk")
    if "team" in q or "colleague" in q:
        params["preferences"].append("near-team")
    if "ultrawide" in q or "wide screen" in q:
        params["preferences"].append("ultrawide")
    if "lift" in q or "elevator" in q:
        params["preferences"].append("near-lift")

    for loc in ["london", "leeds", "edinburgh"]:
        if re.search(r"\b" + loc + r"\b", q):
            params["location"] = loc.capitalize()
            break

    return params


if __name__ == "__main__":
    db = SessionLocal()
    try:
        query = "I need a quiet spot near the window in London"
        filters = translate_natural_language(query)
        print(f"Natural Language Query: '{query}'")
        print(f"Translated Filters: {filters}\n")

        sample_user_id = "aad-0001"
        all_desks = db.query(Desk).options(joinedload(Desk.section)).all()
        print(f"Running allocation for user_id: {sample_user_id}...")
        desk_email, match_score = allocate_desk(sample_user_id, all_desks, db, date.today())

        if desk_email:
            print(f"  -> Best desk: {desk_email} (Match Score: {match_score}%)")
        else:
            print("  -> No suitable desk found.")
    finally:
        db.close()
