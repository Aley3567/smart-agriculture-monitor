import os

try:
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except Exception:
    pass

# 高德 Web 服务 Key:本地放 backend/.env,部署走环境变量,代码中不留明文
AMAP_WEB_SERVICE_KEY = os.environ.get("AMAP_WEB_SERVICE_KEY", "")

DEFAULT_THRESHOLDS = {
    "temperature": {"min_value": 18.0, "max_value": 35.0},
    "humidity": {"min_value": 30.0, "max_value": 80.0},
    "light": {"min_value": 10.0, "max_value": 90.0},
    "soil_moisture": {"min_value": 25.0, "max_value": 75.0},
    "soil_fertility": {"min_value": 60.0, "max_value": 100.0},
}

DEVICE_COMMAND_MAP = {
    "pump": {"on": "BLEGLED1", "off": "BLEKLED1"},
    "fertilizer": {"on": "BLEGLED2", "off": "BLEKLED2"},
    "pest_light": {"on": "BLEGLED3", "off": "BLEKLED3"},
}

ALARM_LIGHT_COMMAND_MAP = {
    "on": "BLEALARM1",
    "off": "BLEALARM0",
}

DEVICE_ALIASES = {
    "skylight": "pest_light",
}

PARAM_DEVICE_MAP = {
    "temperature": None,
    "humidity": None,
    "light": None,
    "soil_moisture": None,
    "soil_fertility": None,
}

CONTROL_RULE_SOIL_MOISTURE_PUMP = "soil-moisture-pump"

DEFAULT_CONTROL_RULES = {
    CONTROL_RULE_SOIL_MOISTURE_PUMP: {
        "enabled": True,
        "start_below": 35.0,
        "stop_at_or_above": 45.0,
        "consecutive_samples": 3,
        "max_run_sec": 20,
        "cooldown_sec": 30,
    },
}


def normalize_device(device: str) -> str:
    return DEVICE_ALIASES.get(device, device)

DATABASE_URL = "sqlite+aiosqlite:///./agriculture.db"

SECRET_KEY = "smart-agriculture-secret-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080
