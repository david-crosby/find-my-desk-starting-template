from pydantic import BaseModel


class UserBase(BaseModel):
    email: str
    display_name: str
    is_admin: bool = False


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    id: int
    model_config = {"from_attributes": True}


class LocationBase(BaseModel):
    name: str
    address: str | None = None


class LocationRead(LocationBase):
    id: int
    model_config = {"from_attributes": True}


class FloorBase(BaseModel):
    location_id: int
    number: int
    name: str | None = None


class FloorRead(FloorBase):
    id: int
    model_config = {"from_attributes": True}


class DeskBase(BaseModel):
    floor_id: int
    label: str
    is_active: bool = True


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


class BookingRead(BookingCreate):
    id: int
    status: str
    model_config = {"from_attributes": True}


class AvailabilityQuery(BaseModel):
    date: str
    location_id: int | None = None
    floor_id: int | None = None
