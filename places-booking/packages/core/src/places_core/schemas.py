from datetime import datetime

from pydantic import BaseModel


class UserBase(BaseModel):
    email: str
    display_name: str
    is_admin: bool = False


class UserCreate(UserBase):
    entra_id: str | None = None
    employee_id: int | None = None
    department: str | None = None
    team: str | None = None
    role: str | None = None
    employment_type: str = "permanent"
    home_building_id: int | None = None
    home_floor_id: int | None = None
    home_section_id: int | None = None
    preferred_neighbourhood: str | None = None
    default_working_pattern: dict | None = None
    anchor_days: list | None = None
    booking_window_days: int = 14
    line_manager_email: str | None = None
    preferred_noise_level: str = "no_preference"
    requires_standing_desk: bool = False
    prefers_window_seat: bool = False
    dual_monitor_required: bool = False
    docking_station_required: bool = False
    ergonomic_chair_required: bool = False
    accessible_desk_preferred: bool = False
    near_team_preferred: bool = False
    ai_autonomy_level: str = "book_with_confirm"
    primary_team_id: str | None = None
    workplan_visibility: str = "team"


class UserRead(UserBase):
    id: int
    entra_id: str | None = None
    employee_id: int | None = None
    department: str | None = None
    team: str | None = None
    role: str | None = None
    employment_type: str
    home_building_id: int | None = None
    home_section_id: int | None = None
    preferred_neighbourhood: str | None = None
    anchor_days: list | None = None
    booking_window_days: int
    line_manager_email: str | None = None
    requires_standing_desk: bool
    prefers_window_seat: bool
    dual_monitor_required: bool
    ergonomic_chair_required: bool
    near_team_preferred: bool
    ai_autonomy_level: str
    primary_team_id: str | None = None
    model_config = {"from_attributes": True}


class BuildingBase(BaseModel):
    name: str
    address: str | None = None
    building_lat: str | None = None
    building_lng: str | None = None


class BuildingRead(BuildingBase):
    id: int
    model_config = {"from_attributes": True}


class FloorBase(BaseModel):
    building_id: int
    number: int
    name: str | None = None


class FloorRead(FloorBase):
    id: int
    model_config = {"from_attributes": True}


class SectionBase(BaseModel):
    floor_id: int
    name: str
    zone_label: str | None = None


class SectionRead(SectionBase):
    id: int
    model_config = {"from_attributes": True}


class DeskBase(BaseModel):
    section_id: int
    label: str
    is_active: bool = True
    desk_mode: str = "reservable"
    has_dual_monitors: bool = False
    has_docking_station: bool = False
    has_standing_desk: bool = False
    is_accessible: bool = False
    is_window_seat: bool = False


class DeskRead(DeskBase):
    id: int
    model_config = {"from_attributes": True}


class RoomBase(BaseModel):
    floor_id: int
    name: str
    capacity: int
    is_active: bool = True
    ms_resource_email: str | None = None


class RoomRead(RoomBase):
    id: int
    model_config = {"from_attributes": True}


class BookingCreate(BaseModel):
    user_id: int
    desk_id: int | None = None
    room_id: int | None = None
    date: str
    start_time: str | None = None
    end_time: str | None = None
    booking_source: str = "web_app"
    agent_intent_tier: int | None = None
    agent_session_id: int | None = None


class BookingRead(BaseModel):
    id: int
    user_id: int
    desk_id: int | None = None
    room_id: int | None = None
    date: str
    start_time: str | None = None
    end_time: str | None = None
    status: str
    booking_source: str
    no_show_flag: bool
    approval_status: str
    booking_created_at: datetime | None = None
    model_config = {"from_attributes": True}


class AvailabilityQuery(BaseModel):
    date: str
    building_id: int | None = None
    floor_id: int | None = None
    section_id: int | None = None


class AgentSessionCreate(BaseModel):
    user_id: int
    session_id: str
    utterance_raw: str | None = None
    intent_classified: str | None = None
    slots_extracted: dict | None = None
    slots_inferred: dict | None = None
    slots_missing: list | None = None
    agent_proposed_desks: list | None = None
    confidence_score: int | None = None
    model_version: str | None = None


class AgentSessionRead(AgentSessionCreate):
    id: int
    clarification_turns: int
    fallback_triggered: bool
    user_accepted_rank: int | None = None
    feedback_rating: int | None = None
    created_at: datetime | None = None
    model_config = {"from_attributes": True}
