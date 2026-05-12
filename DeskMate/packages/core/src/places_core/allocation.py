"""
Three-phase weighted allocation engine for desk assignment.

Phase 1 — Pre-filter (hard rules):
  - VIP/Exec protection: exec desks reserved for is_vip users only
  - Restricted working areas: users with restricted_section_ids are limited to
    those sections; restricted sections block all other users

Phase 2 — Weighted scoring (configurable via AllocationWeights):
  - People Prefs: same-team / lab / platform proximity, followed colleagues
    (VIPs excluded unless the user is their direct line report)
  - Environment: window seat, noise match, lift/exit/toilet proximity, AC avoidance
  - Equipment: monitor count, sit-stand, ultrawide, docking station, accessibility
  - Location: preferred neighbourhood match
  - Historical: favourites, recently used (recency decay), per-desk feedback history

Phase 3 — Post-override:
  - VIP users are processed before all others so they get first pick
  - Anchor-day bookings with no match are flagged for admin escalation
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session, joinedload

from .models import (
    Allocation,
    AllocationWeights,
    Booking,
    Desk,
    Feedback,
    User,
)

# Noise preference → target noise_level_rating (1–5 scale)
_NOISE_TARGETS: dict[str, float] = {
    "silent": 1.0,
    "quiet": 2.0,
    "moderate": 3.0,
}


def _noise_match_factor(preferred: str, desk_rating: float) -> float:
    """Return 0–1: how well desk noise matches user preference.

    Falls off linearly: ±1 away = 0.5, ±2 away = 0.0.
    """
    target = _NOISE_TARGETS.get(preferred)
    if target is None:
        return 0.0
    diff = abs(desk_rating - target)
    return max(0.0, 1.0 - diff / 2.0)


def _recency_factor(desk_id: int, recently_used: list[int]) -> float:
    """Return 0–1 based on position in recently_used list. Most recent = 1.0."""
    try:
        idx = recently_used.index(desk_id)
        return max(0.2, 1.0 - idx * 0.2)
    except ValueError:
        return 0.0


def _get_user_desk_feedback(user_id: int, desk_id: int, db: Session) -> float | None:
    """Return average feedback rating this user gave a specific desk, or None."""
    rows = (
        db.query(Feedback.rating)
        .join(Booking)
        .filter(
            Feedback.user_id == user_id,
            Booking.desk_id == desk_id,
        )
        .all()
    )
    if not rows:
        return None
    return sum(r[0] for r in rows) / len(rows)


def load_weights(db: Session) -> AllocationWeights:
    """Return the active AllocationWeights config, or defaults if none exists."""
    w = db.query(AllocationWeights).filter(AllocationWeights.is_active == True).first()  # noqa: E712
    return w if w is not None else AllocationWeights()


def get_team_sections_for_date(
    user: User,
    target_date_str: str,
    db: Session,
) -> dict[str, set[int]]:
    """Return section IDs where colleagues of each group type have bookings today.

    Keys: 'same_team', 'same_lab', 'same_platform', 'follow'
    """
    result: dict[str, set[int]] = {
        "same_team": set(),
        "same_lab": set(),
        "same_platform": set(),
        "follow": set(),
    }

    if user.team:
        team_bookings = (
            db.query(Booking)
            .join(User, User.id == Booking.user_id)
            .options(joinedload(Booking.desk))
            .filter(
                User.team == user.team,
                User.id != user.id,
                Booking.date == target_date_str,
                Booking.desk_id.isnot(None),
                Booking.status.in_(["queued", "confirmed", "allocated"]),
            )
            .all()
        )
        for bk in team_bookings:
            if not bk.desk:
                continue
            colleague: User = bk.user
            team_type = colleague.entra_team_type or "team"
            if team_type == "lab":
                result["same_lab"].add(bk.desk.section_id)
            elif team_type == "platform":
                result["same_platform"].add(bk.desk.section_id)
            else:
                result["same_team"].add(bk.desk.section_id)

    followed_ids: list[str] = user.follow_colleagues or []
    if followed_ids:
        follow_bookings = (
            db.query(Booking)
            .join(User, User.id == Booking.user_id)
            .options(joinedload(Booking.desk))
            .filter(
                User.entra_id.in_(followed_ids),
                Booking.date == target_date_str,
                Booking.desk_id.isnot(None),
                Booking.status.in_(["queued", "confirmed", "allocated"]),
            )
            .all()
        )
        for bk in follow_bookings:
            if not bk.desk:
                continue
            colleague = bk.user
            # Exclude VIPs from proximity scoring unless they are this user's line manager
            if colleague.is_vip and colleague.id != user.line_manager_id:
                continue
            result["follow"].add(bk.desk.section_id)

    return result


def pre_filter(user: User, desks: list[Desk]) -> list[Desk]:
    """Phase 1: Remove desks that hard rules forbid for this user."""
    user_restricted = set(user.restricted_section_ids or [])
    eligible: list[Desk] = []

    for desk in desks:
        section = desk.section

        # Rule: exec desks → VIP users only
        if desk.is_exec_desk and not user.is_vip:
            continue

        # Rule: restricted sections → only accessible to users with explicit permission
        if section.is_restricted and desk.section_id not in user_restricted:
            continue

        # Rule: user restricted to specific sections → enforce
        if user_restricted and desk.section_id not in user_restricted:
            continue

        eligible.append(desk)

    return eligible


def score_desk(
    desk: Desk,
    user: User,
    weights: AllocationWeights,
    team_sections: dict[str, set[int]],
    db: Session,
) -> tuple[float, float]:
    """Return (raw_score, max_possible_score) for a single desk/user pair."""
    score = 0.0
    max_possible = 0.0
    section_id = desk.section_id

    # ── People Prefs ──────────────────────────────────────────────────────────
    if user.near_team_preferred and user.team:
        max_possible += weights.w_same_team
        if section_id in team_sections["same_team"]:
            score += weights.w_same_team

    if user.entra_team_type == "lab" and team_sections["same_lab"]:
        max_possible += weights.w_same_lab
        if section_id in team_sections["same_lab"]:
            score += weights.w_same_lab

    if user.entra_team_type == "platform" and team_sections["same_platform"]:
        max_possible += weights.w_same_platform
        if section_id in team_sections["same_platform"]:
            score += weights.w_same_platform

    if user.follow_colleagues:
        max_possible += weights.w_follow_colleague
        if section_id in team_sections["follow"]:
            score += weights.w_follow_colleague

    # ── Environment ───────────────────────────────────────────────────────────
    if user.prefers_window_seat:
        max_possible += weights.w_window
        if desk.is_window_seat:
            score += weights.w_window

    if user.preferred_noise_level not in (None, "no_preference"):
        max_possible += weights.w_noise_match
        factor = _noise_match_factor(user.preferred_noise_level, desk.noise_level_rating)
        score += factor * weights.w_noise_match

    if user.prefers_near_lift:
        max_possible += weights.w_near_lift
        if desk.near_lift:
            score += weights.w_near_lift

    if user.prefers_near_exit:
        max_possible += weights.w_near_exit
        if desk.near_exit:
            score += weights.w_near_exit

    if user.prefers_near_toilets:
        max_possible += weights.w_near_toilets
        if desk.near_toilets:
            score += weights.w_near_toilets

    if user.avoids_ac:
        # Treat as recoverable value: user gets points when NOT near AC
        max_possible += weights.w_avoid_ac_penalty
        if not desk.near_ac_unit:
            score += weights.w_avoid_ac_penalty

    # ── Equipment ─────────────────────────────────────────────────────────────
    if user.preferred_monitors > 1:
        max_possible += weights.w_monitor_match
        if desk.num_monitors >= user.preferred_monitors:
            score += weights.w_monitor_match

    if user.requires_standing_desk:
        max_possible += weights.w_standing_desk
        if desk.has_standing_desk:
            score += weights.w_standing_desk

    if user.prefers_ultrawide:
        max_possible += weights.w_ultrawide
        if desk.has_ultrawide:
            score += weights.w_ultrawide

    if user.docking_station_required:
        max_possible += weights.w_docking_station
        if desk.has_docking_station:
            score += weights.w_docking_station

    if user.accessible_desk_preferred:
        max_possible += weights.w_accessible
        if desk.is_accessible:
            score += weights.w_accessible

    # ── Location / Neighbourhood ──────────────────────────────────────────────
    if user.preferred_neighbourhood:
        max_possible += weights.w_home_neighbourhood
        if desk.section and desk.section.name == user.preferred_neighbourhood:
            score += weights.w_home_neighbourhood

    # ── Historical / Other Prefs ──────────────────────────────────────────────
    favourite_ids: list[int] = user.favourite_desk_ids or []
    if favourite_ids:
        max_possible += weights.w_favourite_desk
        if desk.id in favourite_ids:
            score += weights.w_favourite_desk

    recently_used: list[int] = user.recently_used_desk_ids or []
    if recently_used:
        max_possible += weights.w_recently_used
        if desk.id in recently_used:
            factor = _recency_factor(desk.id, recently_used)
            score += factor * weights.w_recently_used

    avg_rating = _get_user_desk_feedback(user.id, desk.id, db)
    if avg_rating is not None:
        if avg_rating >= 4.0:
            max_possible += weights.w_positive_feedback
            score += weights.w_positive_feedback
        elif avg_rating <= 2.0:
            max_possible += weights.w_negative_feedback_penalty
            score -= weights.w_negative_feedback_penalty

    return score, max_possible


def allocate_desk(
    user_id: str,
    available_desks: list[Desk],
    db: Session,
    target_date: date,
) -> tuple[str | None, float]:
    """Find the best available desk for a user.

    Args:
        user_id: The entra_id of the user.
        available_desks: Desk objects with section pre-loaded.
        db: SQLAlchemy session.
        target_date: Booking date.

    Returns:
        (desk_email_address, match_percentage) or (None, 0.0).
    """
    user = db.query(User).filter(User.entra_id == user_id).first()
    if not user:
        return None, 0.0

    eligible = pre_filter(user, available_desks)
    if not eligible:
        return None, 0.0

    weights = load_weights(db)
    target_date_str = target_date.isoformat()
    team_sections = get_team_sections_for_date(user, target_date_str, db)

    best_desk: Desk | None = None
    best_score = -1.0
    best_max = 0.0

    for desk in eligible:
        raw, max_p = score_desk(desk, user, weights, team_sections, db)
        if raw > best_score:
            best_score = raw
            best_max = max_p
            best_desk = desk

    if best_desk is None:
        return None, 0.0

    if best_max <= 0:
        return best_desk.desk_email_address, 100.0

    match_pct = max(0.0, (best_score / best_max) * 100)
    return best_desk.desk_email_address, round(match_pct, 2)


def run_nightly_allocation(db: Session, target_date: date) -> dict[str, Any]:
    """Process all queued bookings for target_date.

    VIPs processed first. Anchor-day failures flagged for escalation.
    Returns {'allocated': n, 'failed': n, 'escalated': n}.
    """
    target_str = target_date.isoformat()

    queued = (
        db.query(Booking)
        .join(User, User.id == Booking.user_id)
        .options(joinedload(Booking.user))
        .filter(
            Booking.date == target_str,
            Booking.status == "queued",
            Booking.desk_id.is_(None),
        )
        .order_by(User.is_vip.desc(), Booking.booking_created_at.asc())
        .all()
    )

    if not queued:
        return {"allocated": 0, "failed": 0, "escalated": 0}

    all_desks = (
        db.query(Desk)
        .options(joinedload(Desk.section))
        .filter(Desk.is_active == True)  # noqa: E712
        .all()
    )

    weights = load_weights(db)
    allocated_ids: set[int] = set()
    stats: dict[str, int] = {"allocated": 0, "failed": 0, "escalated": 0}

    for booking in queued:
        user = booking.user
        available = [d for d in all_desks if d.id not in allocated_ids]
        eligible = pre_filter(user, available)

        if not eligible:
            _record_no_match(booking, user, target_date, db, stats)
            continue

        team_sections = get_team_sections_for_date(user, target_str, db)

        best_desk: Desk | None = None
        best_score = -1.0
        best_max = 0.0

        for desk in eligible:
            raw, max_p = score_desk(desk, user, weights, team_sections, db)
            if raw > best_score:
                best_score = raw
                best_max = max_p
                best_desk = desk

        if best_desk is None:
            _record_no_match(booking, user, target_date, db, stats)
            continue

        match_pct = max(0.0, (best_score / best_max) * 100) if best_max > 0 else 100.0

        booking.desk_id = best_desk.id
        booking.status = "allocated"
        allocated_ids.add(best_desk.id)

        db.add(Allocation(
            booking=booking,
            desk_id=best_desk.id,
            score=round(best_score, 4),
            match_percentage=round(match_pct, 2),
            allocation_run_date=target_str,
        ))
        stats["allocated"] += 1

    db.commit()

    # Update Outlook calendar events for all newly allocated bookings
    try:
        from .calendar_service import update_calendar_event
        allocated_bookings = (
            db.query(Booking)
            .filter(
                Booking.date == target_str,
                Booking.status == "allocated",
                Booking.desk_id.isnot(None),
            )
            .all()
        )
        for booking in allocated_bookings:
            update_calendar_event(booking, db)
    except Exception:
        pass
    return stats


def _record_no_match(
    booking: Booking,
    user: User,
    target_date: date,
    db: Session,
    stats: dict[str, int],
) -> None:
    anchor_days: list[str] = user.anchor_days or []
    day_name = target_date.strftime("%A").lower()
    notes = "anchor_day_unmet" if day_name in anchor_days else "no_eligible_desk"

    db.add(Allocation(
        booking=booking,
        desk_id=None,
        score=0.0,
        match_percentage=0.0,
        allocation_run_date=target_date.isoformat(),
        allocation_notes=notes,
    ))

    if notes == "anchor_day_unmet":
        stats["escalated"] += 1
    else:
        stats["failed"] += 1
