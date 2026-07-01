import math
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class SensorField:
    key: str
    param: str
    label: str
    unit: str
    source: str
    detail: str
    category: str
    available: bool


SENSOR_FIELDS: dict[str, SensorField] = {
    "temp": SensorField(
        key="temp",
        param="temperature",
        label="温度",
        unit="°C",
        source="measured",
        detail="DHT11 P2.0",
        category="measured",
        available=True,
    ),
    "humi": SensorField(
        key="humi",
        param="humidity",
        label="空气湿度",
        unit="%",
        source="measured",
        detail="DHT11 P2.0",
        category="measured",
        available=True,
    ),
    "light": SensorField(
        key="light",
        param="light",
        label="相对光照",
        unit="相对值",
        source="measured",
        detail="GL5516 P0.7 ADC 相对光照值",
        category="measured",
        available=True,
    ),
    "soil": SensorField(
        key="soil",
        param="soil_moisture",
        label="土壤湿度",
        unit="%",
        source="computed_backend",
        detail="后端模型推导：由温度、空气湿度、光照推导",
        category="model",
        available=True,
    ),
    "co2": SensorField(
        key="co2",
        param="co2",
        label="CO2",
        unit="ppm",
        source="simulated_backend",
        detail="后端模型模拟：由温度、空气湿度、光照推导",
        category="model",
        available=True,
    ),
    "soil_ec": SensorField(
        key="soil_ec",
        param="soil_ec",
        label="土壤EC",
        unit="dS/m",
        source="computed_backend",
        detail="后端模型计算：由土壤湿度、温度、空气湿度推导",
        category="model",
        available=True,
    ),
    "soil_tds": SensorField(
        key="soil_tds",
        param="soil_tds",
        label="土壤TDS",
        unit="ppm",
        source="computed_backend",
        detail="由土壤EC换算，TDS = EC * 640",
        category="model",
        available=True,
    ),
    "soil_fertility": SensorField(
        key="soil_fertility",
        param="soil_fertility",
        label="土壤肥力",
        unit="%",
        source="computed_backend",
        detail="由土壤湿度与土壤EC归一化推导",
        category="model",
        available=True,
    ),
    "infrared": SensorField(
        key="infrared",
        param="infrared",
        label="红外状态",
        unit="",
        source="simulated_backend",
        detail="后端模拟红外触发状态，用于课程演示",
        category="model",
        available=True,
    ),
}


def sensor_field_catalog() -> dict[str, dict[str, Any]]:
    return {key: asdict(field) for key, field in SENSOR_FIELDS.items()}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _jitter(temp: float, humi: float, light: float, freq: float) -> float:
    return math.sin((temp * 0.131 + humi * 0.257 + light * 0.413) * freq)


def compute_model_values(values: dict[str, Any]) -> dict[str, float]:
    temp = float(values.get("temp") or 0)
    humi = float(values.get("humi") or 0)
    light = float(values.get("light") or 0)

    soil_raw = 56 + (humi - 50) * 0.35 - max(temp - 20, 0) * 1.0 + (light - 50) * 0.7
    soil = _clamp(soil_raw + _jitter(temp, humi, light, 7.3) * 0.5, 15, 75)

    ec_raw = 0.65 + soil * 0.016 + max(temp - 25, 0) * 0.015 - max(humi - 70, 0) * 0.004
    soil_ec = _clamp(ec_raw + _jitter(temp, humi, light, 13.1) * 0.015, 0.3, 2.6)

    soil_tds = soil_ec * 640
    soil_fertility = _clamp(100 - abs(soil - 45) * 1.4 - abs(soil_ec - 1.25) * 22, 0, 100)

    co2_raw = 420 + max(100 - light, 0) * 2.8 + max(temp - 25, 0) * 7 + max(humi - 70, 0) * 2
    co2 = _clamp(co2_raw + _jitter(temp, humi, light, 3.7) * 8, 400, 1200)

    infrared = 1.0 if light < 18 else 0.0

    return {
        "soil": round(soil, 1),
        "co2": round(co2, 1),
        "soil_ec": round(soil_ec, 2),
        "soil_tds": round(soil_tds, 0),
        "soil_fertility": round(soil_fertility, 1),
        "infrared": infrared,
    }


def build_sensor_facts(values: dict[str, Any]) -> dict[str, dict[str, Any]]:
    model_values = compute_model_values(values)
    facts = {}
    for key, field in SENSOR_FIELDS.items():
        value = values.get(key)
        if key in model_values:
            value = model_values[key]
        facts[key] = {
            **asdict(field),
            "value": value,
            "formula_version": "v1" if key in model_values else None,
        }
    return facts
