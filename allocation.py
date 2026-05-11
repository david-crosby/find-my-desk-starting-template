#!/usr/bin/env python3
"""Weighted allocation algorithm for finding the best desk for a user."""

import re
from datetime import date
from typing import Any

from sqlalchemy.orm import Session, joinedload

from places_core.db import SessionLocal
from places_core.models import Booking, Desk, User


def translate_natural_language(query: str) -> dict[str, Any]:
    """
    A simple helper function to translate a natural language query into
    structured filter parameters for desk searching.

    This is a placeholder for a more sophisticated NLU/agentic tool.
    In a real scenario, this would likely involve a call to an LLM like Claude
    to perform entity extraction.

    Args:
        query: The natural language query from the user.

    Returns:
        A dictionary of filter parameters.
    """
    params: dict[str, Any] = {"preferences": []}
    query_lower = query.lower()

    if "quiet" in query_lower:
        params["preferences"].append("quiet-area")
    if "window" in query_lower:
        params["preferences"].append("window-seat")
    if "standing" in query_lower:
        params["preferences"].append("standing-desk")
    if "monitor" in query_lower:
        params["preferences"].append("dual-monitor")
    if "accessible" in query_lower:
        params["preferences"].append("accessible-desk")
    if "team" in query_lower:
        params["preferences"].append("near-team")

    # A simple regex to find a location from the known list
    locations = ["london", "leeds", "edinburgh"]
    for loc in locations:
        if re.search(r"\b" + loc + r"\b", query_lower):
            params["location"] = loc.capitalize()
            break

    return params


def allocate_desk(
    user_id: str, available_desks: list[Desk], db: Session, target_date: date
) -> tuple[str | None, float]:
    """
    Finds the best available desk for a user based on a weighted scoring model.

    Args:
        user_id: The entra_id of the user making the request.
        available_desks: A list of available Desk objects from SQLAlchemy.
                         It's recommended to eager load desk.section for performance.
        db: The SQLAlchemy session.
        target_date: The date for which to find a desk.

    Returns:
        A tuple containing the email address of the best-matched desk and the
        match score as a percentage. Returns (None, 0.0) if no suitable
        desk is found.
    """
    user = db.query(User).filter(User.entra_id == user_id).first()
    if not user:
        return None, 0.0

    # --- Team Proximity Setup ---
    team_desk_sections = set()
    if user.team and user.near_team_preferred:
        target_date_str = target_date.isoformat()
        team_bookings = (
            db.query(Booking)
            .join(User)
            .options(joinedload(Booking.desk).joinedload(Desk.section))
            .filter(
                User.team == user.team,
                User.id != user.id,
                Booking.date == target_date_str,
                Booking.desk_id.isnot(None),
            )
            .all()
        )
        team_desk_sections = {b.desk.section_id for b in team_bookings if b.desk}

    scored_desks = []
    max_possible_score = 0

    # --- Calculate Max Possible Score based on the user's actual preferences ---
    if user.preferred_neighbourhood:
        max_possible_score += 50
    if user.prefers_window_seat:
        max_possible_score += 20
    if user.preferred_noise_level == "quiet":
        max_possible_score += 20
    if user.requires_standing_desk:
        max_possible_score += 20
    if user.dual_monitor_required:
        max_possible_score += 20
    if user.accessible_desk_preferred:
        max_possible_score += 20
    if user.near_team_preferred:
        max_possible_score += 30

    if max_possible_score == 0:
        # User has no preferences, so any available desk is a 100% match.
        if available_desks:
            return available_desks[0].desk_email_address, 100.0
        return None, 0.0

    for desk in available_desks:
        score = 0

        # 1. Primary Match: Preferred Neighbourhood (+50)
        if user.preferred_neighbourhood and desk.section.name == user.preferred_neighbourhood:
            score += 50

        # 2. Environmental Match: Desk attributes (+20 per match)
        if user.prefers_window_seat and desk.is_window_seat:
            score += 20
        if user.preferred_noise_level == "quiet" and desk.section.name == "Quiet Zone":
            score += 20
        if user.requires_standing_desk and desk.has_standing_desk:
            score += 20
        if user.dual_monitor_required and desk.has_dual_monitors:
            score += 20
        if user.accessible_desk_preferred and desk.is_accessible:
            score += 20

        # 3. Team Proximity (+30)
        if user.near_team_preferred and desk.section_id in team_desk_sections:
            score += 30

        # 4. Base Weighting (Not implemented)
        # The 'desks' table schema does not have a 'base_weight' field to
        # de-prioritize over-utilized desks. This could be added to the model.

        if score > 0:
            scored_desks.append({"desk": desk, "score": score})

    if not scored_desks:
        return None, 0.0

    best_match = sorted(scored_desks, key=lambda x: x["score"], reverse=True)[0]
    best_desk = best_match["desk"]
    top_score = best_match["score"]

    # Calculate percentage against the max possible score for this user's preferences
    match_percentage = (top_score / max_possible_score) * 100

    return best_desk.desk_email_address, round(match_percentage, 2)


def calculate_best_desk(
    user_preferences: dict[str, Any], available_desks: list[dict[str, Any]], db: Session, target_date_str: str
) -> dict[str, Any]:
    """
    Calculates the single best desk from a list of Graph-sourced desks based on weighted scoring.

    Weights:
    - Primary Match (+50): Zone matches preferredNeighbourhood.
    - Environmental Match (+20 per attribute): Match in tags like Window, Quiet, Collaboration.
    - Team Proximity (+30): Desk is in a zone where teammates have booked.

    Returns:
        A JSON-serialisable dictionary containing the email, match_score, and display_name.
    """
    if not available_desks:
        return {"email": None, "match_score": 0.0, "display_name": None}

    pref_zone = user_preferences.get("preferredNeighbourhood")
    pref_attributes = user_preferences.get("deskPreferences", [])
    team_id = user_preferences.get("teamID")

    # --- Team Proximity Setup ---
    team_desk_zones = set()
    if team_id:
        team_bookings = (
            db.query(Booking)
            .join(User)
            .options(joinedload(Booking.desk).joinedload(Desk.section))
            .filter(
                User.team == team_id,
                Booking.date == target_date_str,
                Booking.desk_id.isnot(None),
            )
            .all()
        )
        for booking in team_bookings:
            if booking.desk and booking.desk.section:
                team_desk_zones.add(booking.desk.section.name)

    scored_desks = []
    for desk in available_desks:
        score = 0
        desk_zone = desk.get("zone")
        desk_tags = desk.get("tags", [])

        if pref_zone and desk_zone == pref_zone:
            score += 50

        for attr in pref_attributes:
            if attr in desk_tags:
                score += 20

        if team_id and desk_zone in team_desk_zones:
            score += 30

        scored_desks.append({"desk": desk, "score": score})

    max_score = (50 if pref_zone else 0) + (len(pref_attributes) * 20) + (30 if team_id else 0)
    best_match = sorted(scored_desks, key=lambda x: x["score"], reverse=True)[0]
    
    match_percentage = (best_match["score"] / max_score) * 100 if max_score > 0 else 100.0

    return {
        "email": best_match["desk"].get("email"),
        "match_score": round(match_percentage, 2),
        "display_name": best_match["desk"].get("display_name"),
    }


if __name__ == "__main__":
    # Example of how to run the allocation service
    db = SessionLocal()
    try:
        # 1. Test the "agentic" helper
        query = "I need a quiet spot near the window in London"
        filters = translate_natural_language(query)
        print(f"Natural Language Query: '{query}'")
        print(f"Translated Filters: {filters}\n")

        # 2. Test the allocation algorithm for a sample user
        # User ID for 'Brandi Holloway' from users.json
        sample_user_id = "bc8c2dd5-9501-4961-bd84-639fc4422151"
        all_desks = db.query(Desk).options(joinedload(Desk.section)).all()

        print(f"Running allocation for user_id: {sample_user_id}...")
        desk_email, match_score = allocate_desk(sample_user_id, all_desks, db, date.today())

        if desk_email:
            print(f"  -> Best desk found: {desk_email} (Match Score: {match_score}%)")
        else:
            print("  -> No suitable desk found for the user's preferences.")
    finally:
        db.close()