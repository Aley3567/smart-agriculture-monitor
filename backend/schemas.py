from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SensorDataIn(BaseModel):
    temp: float
    humi: float
    light: float
    soil: float


class SensorDataOut(BaseModel):
    id: int
    timestamp: datetime
    temperature: float
    humidity: float
    light: float
    soil_moisture: float

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
