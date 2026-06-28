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
    "light": {"min_value": 200.0, "max_value": 2000.0},
    "soil_moisture": {"min_value": 25.0, "max_value": 75.0},
}

DEVICE_COMMAND_MAP = {
    "pump": {"on": "BLEGLED1", "off": "BLEKLED1"},
    "fertilizer": {"on": "BLEGLED2", "off": "BLEKLED2"},
    "skylight": {"on": "BLEGLED3", "off": "BLEKLED3"},
}

PARAM_DEVICE_MAP = {
    "temperature": "pump",
    "humidity": "fertilizer",
    "light": "skylight",
    "soil_moisture": None,
}

DATABASE_URL = "sqlite+aiosqlite:///./agriculture.db"

SECRET_KEY = "smart-agriculture-secret-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440
