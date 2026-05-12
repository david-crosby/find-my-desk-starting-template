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
    entra_team_type: str = "team"
    is_vip: bool = False
    home_building_id: int | None = None
    home_floor_id: int | None = None
    home_section_id: int | None = None
    preferred_neighbourhood: str | None = None
    default_working_pattern: dict | None = None
    anchor_days: list | None = None
    booking_window_days: int = 14
    line_manager_email: str | None = None
    preferred_noise_level: str = "no_preference"
    prefers_window_seat: bool = False
    prefers_near_lift: bool = False
    prefers_near_exit: bool = False
    prefers_near_toilets: bool = False
    avoids_ac: bool = False
    preferred_monitors: int = 1
    prefers_ultrawide: bool = False
    requires_standing_desk: bool = False
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
    entra_team_type: str
    is_vip: bool
    home_building_id: int | None = None
    home_section_id: int | None = None
    preferred_neighbourhood: str | None = None
    anchor_days: list | None = None
    booking_window_days: int
    line_manager_email: str | None = None
    preferred_noise_level: str
    prefers_window_seat: bool
    prefers_near_lift: bool
    prefers_near_exit: bool
    prefers_near_toilets: bool
    avoids_ac: bool
    preferred_monitors: int
    prefers_ultrawide: bool
    requires_standing_desk: bool
    ergonomic_chair_required: bool
    accessible_desk_preferred: bool
    near_team_preferred: bool
    ai_autonomy_level: str
    primary_team_id: str | None = None
    follow_colleagues: list | None = None
    model_config = {"from_attributes": True}


class BuildingBase(BaseModel):
    name: str
    address: str | None = None
    building_lat: str | None = None
    building_lng: str | None = None


BuildingCreate = BuildingBase


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
    is_restricted: bool = False


class SectionRead(SectionBase):
    id: int
    model_config = {"from_attributes": True}


class DeskBase(BaseModel):
    section_id: int
    label: str
    is_active: bool = True
    desk_mode: str = "reservable"
    num_monitors: int = 1
    has_ultrawide: bool = False
    has_docking_station: bool = False
    has_standing_desk: bool = False
    is_accessible: bool = False
    is_window_seat: bool = False
    noise_level_rating: float = 3.0
    near_lift: bool = False
    near_exit: bool = False
    near_toilets: bool = False
    near_ac_unit: bool = False
    is_exec_desk: bool = False


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
    booking_created_at: datetime
    model_config = {"from_attributes": True}


class AllocationWeightsRead(BaseModel):
    id: int
    name: str
    is_active: bool
    w_same_team: float
    w_same_lab: float
    w_same_platform: float
    w_follow_colleague: float
    w_window: float
    w_noise_match: float
    w_near_lift: float
    w_near_exit: float
    w_near_toilets: float
    w_avoid_ac_penalty: float
    w_monitor_match: float
    w_standing_desk: float
    w_ultrawide: float
    w_docking_station: float
    w_accessible: float


class FeedbackCreate(BaseModel):
    booking_id: int
    user_id: int
    rating: int
    comments: str | None = None
    desk_comfort: int | None = None
    noise_rating: int | None = None
    equipment_rating: int | None = None


class FeedbackRead(FeedbackCreate):
    id: int
    submitted_at: datetime
    model_config = {"from_attributes": True}
    w_home_neighbourhood: float
    w_favourite_desk: float
    w_recently_used: float
    w_positive_feedback: float
    w_negative_feedback_penalty: float
    model_config = {"from_attributes": True}
