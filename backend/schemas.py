from datetime import datetime

from pydantic import BaseModel


class SensorDataIn(BaseModel):
    temp: float
    humi: float
    light: float
    soil: float


class SensorDataOut(BaseModel):
    id: int
    timestamp: datetime
    temp: float
    humi: float
    light: float
    soil: float

    model_config = {"from_attributes": True}


class ThresholdItem(BaseModel):
    param_name: str
    min_value: float
    max_value: float


class ThresholdOut(ThresholdItem):
    id: int

    model_config = {"from_attributes": True}


class AlarmLogOut(BaseModel):
    id: int
    timestamp: datetime
    param_name: str
    value: float
    threshold: float
    action: str

    model_config = {"from_attributes": True}


class ControlRequest(BaseModel):
    device: str
    action: str


class ModeRequest(BaseModel):
    mode: str


class PaginatedSensorData(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[SensorDataOut]


class PaginatedAlarmLog(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AlarmLogOut]


class AlarmSummary(BaseModel):
    total: int
    today: int
    last_24h: int
    by_param: dict[str, int]
    latest: AlarmLogOut | None = None


class UserRegister(BaseModel):
    username: str
    password: str
    display_name: str = ""


class UserLogin(BaseModel):
    username: str
    password: str


class ChangePassword(BaseModel):
    old_password: str
    new_password: str


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
