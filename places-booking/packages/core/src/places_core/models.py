from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str | None] = mapped_column(String)
    building_lat: Mapped[str | None] = mapped_column(String)
    building_lng: Mapped[str | None] = mapped_column(String)
    places_building_id: Mapped[str | None] = mapped_column(String)

    floors: Mapped[list["Floor"]] = relationship(back_populates="building")


class Floor(Base):
    __tablename__ = "floors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"))
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    places_floor_id: Mapped[str | None] = mapped_column(String)

    building: Mapped["Building"] = relationship(back_populates="floors")
    sections: Mapped[list["Section"]] = relationship(back_populates="floor")
    rooms: Mapped[list["Room"]] = relationship(back_populates="floor")


class Section(Base):
    """Neighbourhood / zone within a floor — mandatory level in the Places hierarchy."""

    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    floor_id: Mapped[int] = mapped_column(ForeignKey("floors.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    zone_label: Mapped[str | None] = mapped_column(String)
    places_section_id: Mapped[str | None] = mapped_column(String)

    floor: Mapped["Floor"] = relationship(back_populates="sections")
    desks: Mapped[list["Desk"]] = relationship(back_populates="section")


class BookingPolicy(Base):
    __tablename__ = "booking_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    max_advance_days: Mapped[int] = mapped_column(Integer, default=14)
    max_booking_duration_hours: Mapped[int] = mapped_column(Integer, default=9)
    auto_release_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_release_threshold_mins: Mapped[int] = mapped_column(Integer, default=30)
    check_in_required: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    gdpr_data_retention_days: Mapped[int] = mapped_column(Integer, default=365)


class Desk(Base):
    __tablename__ = "desks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"))
    label: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # MS Places integration
    places_desk_id: Mapped[str | None] = mapped_column(String)
    desk_email_address: Mapped[str | None] = mapped_column(String)
    # drop_in | reservable | managed | assigned
    desk_mode: Mapped[str] = mapped_column(String, default="reservable")

    # Amenities
    has_dual_monitors: Mapped[bool] = mapped_column(Boolean, default=False)
    has_docking_station: Mapped[bool] = mapped_column(Boolean, default=False)
    has_standing_desk: Mapped[bool] = mapped_column(Boolean, default=False)
    is_accessible: Mapped[bool] = mapped_column(Boolean, default=False)
    is_window_seat: Mapped[bool] = mapped_column(Boolean, default=False)

    # Spatial
    coord_x: Mapped[int | None] = mapped_column(Integer)
    coord_y: Mapped[int | None] = mapped_column(Integer)
    imdf_unit_id: Mapped[str | None] = mapped_column(String)

    # Policy
    booking_policy_id: Mapped[int | None] = mapped_column(ForeignKey("booking_policies.id"))
    auto_release_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_release_threshold_mins: Mapped[int] = mapped_column(Integer, default=30)
    check_in_required: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)

    # Sensor
    sensor_device_id: Mapped[str | None] = mapped_column(String)

    section: Mapped["Section"] = relationship(back_populates="desks")
    booking_policy: Mapped["BookingPolicy | None"] = relationship()
    bookings: Mapped[list["Booking"]] = relationship(back_populates="desk")
    occupancy_events: Mapped[list["OccupancyEvent"]] = relationship(back_populates="desk")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    floor_id: Mapped[int] = mapped_column(ForeignKey("floors.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    ms_resource_email: Mapped[str | None] = mapped_column(String)

    floor: Mapped["Floor"] = relationship(back_populates="rooms")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="room")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identity
    entra_id: Mapped[str | None] = mapped_column(String, unique=True)
    employee_id: Mapped[int | None] = mapped_column(Integer)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Profile
    department: Mapped[str | None] = mapped_column(String)
    team: Mapped[str | None] = mapped_column(String)
    role: Mapped[str | None] = mapped_column(String)
    # permanent | contractor | visitor | intern
    employment_type: Mapped[str] = mapped_column(String, default="permanent")

    # Home location preferences
    home_building_id: Mapped[int | None] = mapped_column(ForeignKey("buildings.id"))
    home_floor_id: Mapped[int | None] = mapped_column(ForeignKey("floors.id"))
    home_section_id: Mapped[int | None] = mapped_column(ForeignKey("sections.id"))
    preferred_neighbourhood: Mapped[str | None] = mapped_column(String)

    # Working pattern
    default_working_pattern: Mapped[dict | None] = mapped_column(JSON)
    anchor_days: Mapped[list | None] = mapped_column(JSON)
    booking_window_days: Mapped[int] = mapped_column(Integer, default=14)

    # Line manager
    line_manager_email: Mapped[str | None] = mapped_column(String)
    line_manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    # Environmental preferences
    # silent | quiet | moderate | no_preference
    preferred_noise_level: Mapped[str] = mapped_column(String, default="no_preference")
    requires_standing_desk: Mapped[bool] = mapped_column(Boolean, default=False)
    prefers_window_seat: Mapped[bool] = mapped_column(Boolean, default=False)
    dual_monitor_required: Mapped[bool] = mapped_column(Boolean, default=False)
    docking_station_required: Mapped[bool] = mapped_column(Boolean, default=False)
    ergonomic_chair_required: Mapped[bool] = mapped_column(Boolean, default=False)
    accessible_desk_preferred: Mapped[bool] = mapped_column(Boolean, default=False)
    near_team_preferred: Mapped[bool] = mapped_column(Boolean, default=False)

    # Individual preferences
    # half_day_am | half_day_pm | full_day | custom
    default_booking_duration: Mapped[str] = mapped_column(String, default="full_day")
    default_arrival_time: Mapped[str] = mapped_column(String, default="09:00")
    default_departure_time: Mapped[str] = mapped_column(String, default="18:00")
    notify_on_create: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_reminder: Mapped[bool] = mapped_column(Boolean, default=True)
    calendar_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # suggest_only | book_with_confirm | book_automatically
    ai_autonomy_level: Mapped[str] = mapped_column(String, default="book_with_confirm")
    favourite_desk_ids: Mapped[list | None] = mapped_column(JSON)
    recently_used_desk_ids: Mapped[list | None] = mapped_column(JSON)

    # Team associations
    primary_team_id: Mapped[str | None] = mapped_column(String)
    team_anchor_days: Mapped[list | None] = mapped_column(JSON)
    follow_colleagues: Mapped[list | None] = mapped_column(JSON)
    delegate_booking_ids: Mapped[list | None] = mapped_column(JSON)
    # team | org | private
    workplan_visibility: Mapped[str] = mapped_column(String, default="team")
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    preference_last_updated: Mapped[datetime | None] = mapped_column(DateTime)

    home_building: Mapped["Building | None"] = relationship(foreign_keys=[home_building_id])
    home_floor: Mapped["Floor | None"] = relationship(foreign_keys=[home_floor_id])
    home_section: Mapped["Section | None"] = relationship(foreign_keys=[home_section_id])
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="user", foreign_keys="Booking.user_id"
    )
    agent_sessions: Mapped[list["AgentSession"]] = relationship(back_populates="user")


class AgentSession(Base):
    """One conversation turn / session with the AI booking agent."""

    __tablename__ = "agent_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    utterance_raw: Mapped[str | None] = mapped_column(String)
    # book | amend | cancel | query | recurring | advisory
    intent_classified: Mapped[str | None] = mapped_column(String)
    slots_extracted: Mapped[dict | None] = mapped_column(JSON)
    slots_inferred: Mapped[dict | None] = mapped_column(JSON)
    slots_missing: Mapped[list | None] = mapped_column(JSON)
    clarification_turns: Mapped[int] = mapped_column(Integer, default=0)
    agent_proposed_desks: Mapped[list | None] = mapped_column(JSON)
    user_accepted_rank: Mapped[int | None] = mapped_column(Integer)
    confidence_score: Mapped[int | None] = mapped_column(Integer)
    fallback_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    feedback_rating: Mapped[int | None] = mapped_column(Integer)
    feedback_comment: Mapped[str | None] = mapped_column(String)
    model_version: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="agent_sessions")
    booking: Mapped["Booking | None"] = relationship(back_populates="agent_session")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    desk_id: Mapped[int | None] = mapped_column(ForeignKey("desks.id"), nullable=True)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)
    date: Mapped[str] = mapped_column(String, nullable=False)
    start_time: Mapped[str | None] = mapped_column(String)
    end_time: Mapped[str | None] = mapped_column(String)
    # confirmed | cancelled | completed | no_show
    status: Mapped[str] = mapped_column(String, default="confirmed")
    # agent_ai | web_app | teams_tab | api | admin_portal
    booking_source: Mapped[str] = mapped_column(String, default="web_app")
    agent_intent_tier: Mapped[int | None] = mapped_column(Integer)

    # Audit
    booking_created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    booking_updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    booking_cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    # user_cancelled | admin_released | no_show | auto_release
    cancellation_reason: Mapped[str | None] = mapped_column(String)
    check_in_time: Mapped[datetime | None] = mapped_column(DateTime)
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime)
    no_show_flag: Mapped[bool] = mapped_column(Boolean, default=False)

    # Approvals
    # pending | approved | rejected | not_required
    approval_status: Mapped[str] = mapped_column(String, default="not_required")
    approver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    booking_made_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    audit_log: Mapped[list | None] = mapped_column(JSON)

    # Agent link
    agent_session_id: Mapped[int | None] = mapped_column(ForeignKey("agent_sessions.id"))

    user: Mapped["User"] = relationship(back_populates="bookings", foreign_keys=[user_id])
    desk: Mapped["Desk | None"] = relationship(back_populates="bookings")
    room: Mapped["Room | None"] = relationship(back_populates="bookings")
    agent_session: Mapped["AgentSession | None"] = relationship(back_populates="booking")


class OccupancyEvent(Base):
    """Raw sensor telemetry for a desk — time-series, append-only."""

    __tablename__ = "occupancy_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    desk_id: Mapped[int] = mapped_column(ForeignKey("desks.id"))
    # motion | badge | button | camera_ai | wifi_probe
    sensor_type: Mapped[str] = mapped_column(String, nullable=False)
    signal_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # occupied | vacant | unknown
    state: Mapped[str] = mapped_column(String, nullable=False)
    raw_payload: Mapped[dict | None] = mapped_column(JSON)

    desk: Mapped["Desk"] = relationship(back_populates="occupancy_events")
