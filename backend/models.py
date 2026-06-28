from datetime import datetime

from sqlalchemy import Integer, Float, Text, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class SensorData(Base):
    __tablename__ = "sensor_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    temp: Mapped[float] = mapped_column(Float)
    humi: Mapped[float] = mapped_column(Float)
    light: Mapped[float] = mapped_column(Float)
    soil: Mapped[float] = mapped_column(Float)


class Threshold(Base):
    __tablename__ = "thresholds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    param_name: Mapped[str] = mapped_column(String, unique=True)
    min_value: Mapped[float] = mapped_column(Float)
    max_value: Mapped[float] = mapped_column(Float)


class AlarmLog(Base):
    __tablename__ = "alarm_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    param_name: Mapped[str] = mapped_column(Text)
    value: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    action: Mapped[str] = mapped_column(Text)


class ControlLog(Base):
    __tablename__ = "control_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    device: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
