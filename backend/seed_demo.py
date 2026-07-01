"""灌入演示数据 —— 过去 6 小时、平滑变化、含越界报警,用于本地验收。

让 History 曲线/表格、AlarmLog 报警、报警统计摘要一打开就有真实内容。
注意:直接写 agriculture.db,请在后端停止时运行,避免数据库锁。

用法:
    cd backend && python3 seed_demo.py
"""
import math
import random
import sqlite3
from datetime import timedelta

from time_utils import utc_now

BOARD_ID = "A"
DB = "agriculture.db"
THRESHOLDS = {
    "temperature": (18.0, 35.0),
    "humidity": (30.0, 80.0),
    "light": (10.0, 90.0),
    "soil_moisture": (25.0, 75.0),
}
DEVICE = {"temperature": "pump", "humidity": "fertilizer", "light": None, "soil_moisture": None}

conn = sqlite3.connect(DB)
for table in ("sensor_data", "alarm_log", "control_log"):
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if columns and "board_id" not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN board_id VARCHAR DEFAULT 'A'")

now = utc_now()
count = 180  # 6 小时 / 2 分钟

sensor_rows = []
alarm_rows = []
for i in range(count):
    ts = now - timedelta(minutes=2 * (count - i))
    temp = round(26 + 6 * math.sin(i / 12) + random.uniform(-1.5, 1.5), 1)
    humi = round(60 + 15 * math.sin(i / 18 + 1) + random.uniform(-3, 3), 1)
    light = round(50 + 30 * math.sin(i / 20) + random.uniform(-4, 4))
    soil = round(45 + 13 * math.sin(i / 25 + 2) + random.uniform(-3, 3), 1)
    if i % 47 == 10:
        temp = 39.5
    if i % 53 == 20:
        soil = 17.0

    stamp = ts.strftime("%Y-%m-%d %H:%M:%S.%f")
    sensor_rows.append((stamp, BOARD_ID, temp, humi, light, soil))

    values = {"temperature": temp, "humidity": humi, "light": light, "soil_moisture": soil}
    for param, (lo, hi) in THRESHOLDS.items():
        v = values[param]
        dev = DEVICE[param]
        if v < lo:
            action = f"{dev}_on" if dev else f"{param}_low"
            alarm_rows.append((stamp, BOARD_ID, param, v, lo, action))
        elif v > hi:
            action = f"{dev}_off" if dev else f"{param}_high"
            alarm_rows.append((stamp, BOARD_ID, param, v, hi, action))

conn.executemany(
    "INSERT INTO sensor_data(timestamp, board_id, temp, humi, light, soil) VALUES(?,?,?,?,?,?)", sensor_rows
)
conn.executemany(
    "INSERT INTO alarm_log(timestamp, board_id, param_name, value, threshold, action) VALUES(?,?,?,?,?,?)", alarm_rows
)
conn.commit()
print(f"已灌入 {len(sensor_rows)} 条采样 + {len(alarm_rows)} 条报警")
conn.close()
