from datetime import datetime

from pydantic import BaseModel, Field, field_serializer


def utc_iso(value: datetime) -> str:
    return f"{value.isoformat()}Z" if value.tzinfo is None else value.isoformat()


class SensorDataIn(BaseModel):
    temp: float
    humi: float
    light: float
    soil: float


class TestSensorSampleIn(BaseModel):
    board_id: str
    temperature: float
    humidity: float
    light: float
    soil_moisture: float
    allow_control: bool = False


class SensorDataOut(BaseModel):
    id: int
    timestamp: datetime
    board_id: str = "A"
    temp: float
    humi: float
    light: float
    soil: float
    source: str = "bridge"
    is_test: bool = False
    facts: dict[str, dict] = Field(default_factory=dict)

    model_config = {"from_attributes": True}

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime):
        return utc_iso(value)


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
    board_id: str = "A"
    param_name: str
    param_label: str = ""
    unit: str = ""
    source: str = ""
    is_test: bool = False
    sensor_data_id: int | None = None
    direction: str = ""
    value: float
    threshold: float
    action: str

    model_config = {"from_attributes": True}

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime):
        return utc_iso(value)


class ControlLogOut(BaseModel):
    id: int
    timestamp: datetime
    board_id: str = "A"
    device: str
    action: str
    source: str
    reason: str = ""

    model_config = {"from_attributes": True}

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime):
        return utc_iso(value)


class ControlRequest(BaseModel):
    board_id: str = "A"
    device: str
    action: str


class ControlRuleIn(BaseModel):
    enabled: bool = True
    start_below: float
    stop_at_or_above: float
    consecutive_samples: int = Field(ge=1)
    max_run_sec: int = Field(ge=1)
    cooldown_sec: int = Field(ge=0)


class ControlRuleOut(ControlRuleIn):
    id: int
    rule_key: str

    model_config = {"from_attributes": True}


class ModeRequest(BaseModel):
    mode: str


class PaginatedSensorData(BaseModel):
    total: int
    page: int
    page_size: int
    fields: dict[str, dict]
    items: list[SensorDataOut]


class PaginatedAlarmLog(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AlarmLogOut]


class PaginatedControlLog(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ControlLogOut]


class BoardOut(BaseModel):
    id: int
    board_id: str
    board_name: str
    location: str = ""
    role: str = "end_device"
    enabled: bool = True
    online: bool = False
    last_seen: datetime | None = None
    note: str = ""

    model_config = {"from_attributes": True}

    @field_serializer("last_seen")
    def serialize_last_seen(self, value: datetime | None):
        return utc_iso(value) if value else None


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
