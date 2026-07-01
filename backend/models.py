from datetime import datetime

from sqlalchemy import Boolean, Integer, Float, Text, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from time_utils import utc_now


class SensorData(Base):
    __tablename__ = "sensor_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    board_id: Mapped[str] = mapped_column(String, default="A")
    temp: Mapped[float] = mapped_column(Float)
    humi: Mapped[float] = mapped_column(Float)
    light: Mapped[float] = mapped_column(Float)
    soil: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(Text, default="bridge", server_default="bridge")
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))


class Threshold(Base):
    __tablename__ = "thresholds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    param_name: Mapped[str] = mapped_column(String, unique=True)
    min_value: Mapped[float] = mapped_column(Float)
    max_value: Mapped[float] = mapped_column(Float)


class AlarmLog(Base):
    __tablename__ = "alarm_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    board_id: Mapped[str] = mapped_column(String, default="A")
    param_name: Mapped[str] = mapped_column(Text)
    value: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    action: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, default="bridge", server_default="bridge")
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    sensor_data_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ControlLog(Base):
    __tablename__ = "control_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    board_id: Mapped[str] = mapped_column(String, default="A")
    device: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text, default="", server_default="")


class ControlRule(Base):
    __tablename__ = "control_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_key: Mapped[str] = mapped_column(String, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"))
    start_below: Mapped[float] = mapped_column(Float)
    stop_at_or_above: Mapped[float] = mapped_column(Float)
    consecutive_samples: Mapped[int] = mapped_column(Integer)
    max_run_sec: Mapped[int] = mapped_column(Integer)
    cooldown_sec: Mapped[int] = mapped_column(Integer)


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    board_id: Mapped[str] = mapped_column(String, unique=True)
    board_name: Mapped[str] = mapped_column(String, default="")
    location: Mapped[str] = mapped_column(String, default="")
    role: Mapped[str] = mapped_column(String, default="end_device")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, default="")
    role: Mapped[str] = mapped_column(String, default="管理员")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
