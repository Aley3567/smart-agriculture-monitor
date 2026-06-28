# Smart Agriculture Monitor

基于 CC2530 的智慧农业环境监测系统（课程设计）。

## 架构

```
CC2530终端节点 ──ZigBee点播──→ CC2530协调器 ──UART──→ 本地PC Python脚本 ──WebSocket──→ 云端FastAPI ──WebSocket──→ Vue3 Web前端
     ↑ GPIO控制LED                                                                        ↕ SQLite
```

- **感知层**：终端节点采集 DHT11 温湿度 + 模拟光照/土壤，ZigBee 发给协调器
- **传输层**：协调器串口转 PC，Python 脚本桥接到云端 WebSocket
- **决策层**：FastAPI 接收数据 → 存库 → 阈值判断 → 自动控制（纯函数 evaluate_thresholds + I/O executor）
- **展示层**：Vue3 四页面（监控看板 / 历史数据 / 系统设置 / 报警日志）

控制命令反向走同一链路。硬件命令（BLEGLED1 等）仅在 backend/config.py 翻译，前端只接触语义名。

## 线上地址

- 前端：http://119.91.114.175:18082
- API：http://119.91.114.175:18082/api/status
- WebSocket：ws://119.91.114.175:18082/ws/data
- 服务器：ubuntu@119.91.114.175，systemd 服务名 `smart-agri`

## 部署

```bash
bash scripts/deploy.sh
```

一键 build 前端 → rsync 后端/前端/串口桥接 → 重启 systemd 服务。

## 本地开发

```bash
# 后端
cd backend && python3 -m uvicorn main:app --port 8001

# 串口桥接（模拟数据）
cd serial_bridge && python3 bridge.py --mock --server ws://localhost:8001/ws/bridge

# 前端
cd frontend && npm run dev
```

## 技术栈

- 固件：CC2530 + Z-Stack (IAR)
- 串口桥接：Python + pyserial + websockets
- 后端：FastAPI + SQLite + WebSocket
- 前端：Vue3 + Element Plus + ECharts
