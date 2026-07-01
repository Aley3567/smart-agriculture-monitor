# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Smart Agriculture Monitor

基于 CC2530 的智慧农业环境监测系统（课程设计）。

## 架构

```
CC2530终端节点(ED) ──ZigBee点播──→ CC2530协调器(C) ──UART──→ 本地PC bridge.py ──WS──→ 云端FastAPI ──WS──→ Vue3 前端
     ↑ GPIO控制继电器/LED          (115200 8N1透传)         (ws/bridge)          (ws/data)        ↕ SQLite
```

数据沿这条链路双向流动，下行控制命令走同一链路反向回到 ED 板的 GPIO。

- **感知层**：ED 板采 DHT11 温湿度(P2.0) + GL5516 光敏(P0.7 ADC) + 软件模拟土壤，ZigBee 点播 `t:XX-h:XX-l:XXX-s:XX` 帧给协调器
- **传输层**：协调器 UART 透传到 PC，`bridge.py` 解析帧并桥接到云端 WebSocket
- **决策层**：FastAPI 接收 → 存库 → 阈值判断 → 自动控制
- **展示层**：Vue3 多页面（看板/历史/设置/报警 + 模型管理/测试模式）

## 核心设计约定（修改前必读）

**语义名 vs 硬件命令的单点翻译**：前端、API、数据库一律只用语义名（`pump`/`fertilizer`/`pest_light`，动作 `on`/`off`）。硬件命令字（`BLEGLED1`/`BLEKLED1`/`BLEALARM1` 等）**只在 `backend/config.py` 的 `DEVICE_COMMAND_MAP` / `ALARM_LIGHT_COMMAND_MAP` 翻译一次**，bridge 和固件之外的任何层都不应出现 `BLE*` 字面量。新增执行器时改这张表，不要在前端散布命令字。

**纯函数 + executor 分离**：控制决策逻辑在 `backend/control.py`，`evaluate_thresholds(values, thresholds) -> list[ThresholdDecision]` 是无副作用纯函数；`execute_decisions()` 负责写库 + WebSocket 广播；`check_and_control()` 串起整个流程并叠加自动灌溉规则（连续 N 次采样 + 冷却时间）。改阈值判断逻辑只动纯函数，改 I/O 只动 executor。

**传感器字段是单一事实源**：`backend/sensor_facts.py` 的 `SENSOR_FIELDS` (frozen dataclass) 定义全部 10 个字段及元数据；`compute_model_values()` 是纯函数，由 4 个基础测量值（temp/humi/light/soil）推导 5 个计算值。前端对应 `frontend/src/utils/sources.js` 的 `SOURCE_META`（measured/computed_backend/simulated_*/demo_injection 等 8 类数据源标签）。改字段定义两端都要同步。

**硬编码契约**：物理引脚、波特率、ZigBee 簇 ID、数据帧格式属于"B 类硬编码"，集中记录在 `docs/hardcoding-checklist.md`。改物理板对齐时**只改 `firmware/end_device/SampleApp.h`**，不要散改。引脚速查：P0.6 继电器(高电平吸合)、P1.0/P1.1/P1.6 三路 LED(低电平亮)、P0.7 光敏 ADC、P2.0 DHT11。

## 线上地址

- 前端：http://119.91.114.175:18082
- API：http://119.91.114.175:18082/api/status
- WebSocket：ws://119.91.114.175:18082/ws/data
- 服务器：ubuntu@119.91.114.175，systemd 服务名 `smart-agri`（uvicorn 监听 127.0.0.1:8001，Nginx 代理到 18082）

## 部署

```bash
bash scripts/deploy.sh   # build 前端 → rsync 后端/前端/桥接 → 重启 systemd
```

push 到 `main` 会触发 `.github/workflows/deploy.yml` 做同样的部署（SSH + rsync + `systemctl restart smart-agri`）。

## 本地开发

```bash
# 后端（FastAPI，端口惯例 8001）
cd backend && python3 -m uvicorn main:app --port 8001 --reload
pip install -r backend/requirements.txt

# 串口桥接：真实串口用 --port，无硬件用 --mock
cd serial_bridge && python3 bridge.py --mock --server ws://localhost:8001/ws/bridge
# pyserial 装不上时用纯 Python 模拟推送器：
cd serial_bridge && python3 mock_push.py --server ws://localhost:8001/ws/bridge

# 前端（地址走环境变量，无 vite proxy）
cd frontend && npm install && npm run dev   # .env 指向 localhost:8000，本地需改成 8001
```

注意：前端 `frontend/.env` 默认 `VITE_API_BASE=http://localhost:8000`，本地后端跑 8001 时要改 `.env` 或用 8000 起后端。生产地址在 `.env.production`。

## 测试与演示数据

```bash
# 测试用 unittest（非 pytest），无 conftest/pytest.ini
cd backend && python3 -m unittest discover tests
# 单个测试
python3 -m unittest tests.test_sensor_facts_contract.SensorFactsContractTest.test_<name>

# 灌入演示数据（6小时180条采样+报警，须在后端停止时跑，避免 SQLite 锁）
cd backend && python3 seed_demo.py
```

## 关键约定速记

- **认证**：JWT (HS256, 7天有效)，bcrypt 存密码，`backend/auth.py`。前端 `utils/api.js` 请求拦截器自动附 `Bearer`，401 自动登出跳登录。
- **时间**：后端统一 `time_utils.utc_now()`（无 tzinfo 的 UTC）存库；前端 `utils/format.js` 统一按 `Asia/Shanghai` 显示。
- **WebSocket**：`/ws/bridge` 收设备数据(`sensor_data`/`bridge_hello`/`bridge_debug`)，`/ws/data` 收客户端控制。前端 `utils/websocket.js` 3秒自动重连。`backend/ws_manager.py` 的 `WSManager` 同时管 bridge 连接和客户端连接。
- **多板**：以 `board_id` 区分，默认 `"A"`，启动时自动建默认 board / 阈值 / 控制规则（`main.py` lifespan）。

## 技术栈

- 固件：CC2530 + Z-Stack (IAR)，双板（ED 采集 + C 纯 UART 桥接）
- 串口桥接：Python + pyserial + websockets
- 后端：FastAPI + SQLAlchemy(async) + aiosqlite + python-jose + passlib
- 前端：Vue3 + Vite + Pinia + Element Plus + ECharts（无 ESLint/Prettier/测试工具）

## 文档导航

- `docs/hardcoding-checklist.md` — B 类硬编码对齐表（引脚/波特率/簇ID/帧格式）
- `docs/hardware-interface-alignment.md` — 上下行链路与命令字对应表
- `docs/hardware-quick-debug.md` — 现场排错速查（IAR编译/烧写/串口/bridge 四阶段）
- `docs/team-task-assignment.md` — 人员分工
- `lessons/`、`reference/` — 答辩学习材料与防守词汇表（HTML）
