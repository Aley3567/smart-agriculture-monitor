# 基于单片机的智慧农业环境监测系统 -- 产品需求文档

## 1. 项目概述

课程：物联网通信技术（重庆科技大学 计算机学院 I623 实验室）

系统功能：实时采集大棚环境数据（温度、湿度、光照、土壤湿度等），通过 ZigBee 无线传感器网络汇聚到协调器，经串口上传至上位机，由 FastAPI 后端进行阈值判断和自动控制决策，Vue3 Web 前端提供远程监控和手动操作界面。

交付标准：课题方案全部实现 + 答辩演示。

## 2. 系统架构

```
[终端节点 CC2530]                    [协调器 CC2530]              [本地 PC]                [云服务器]
┌─────────────────┐                ┌──────────────┐          ┌──────────────┐         ┌──────────────────┐
│ DHT11 温湿度     │                │              │          │ Python 串口   │         │ FastAPI 后端      │
│ 其他传感器/模拟   │──ZigBee点播──→│ 接收转发      │──UART──→│ 读取脚本      │──WS──→ │ + SQLite 数据库   │
│ OLED 显示        │                │              │          │              │         │ + Vue3 前端       │
│ LED执行器        │←─ZigBee点播──│ 转发控制命令   │←─UART──│              │←─WS── │                  │
│ MX-01蓝牙(备用)  │                └──────────────┘          └──────────────┘         └──────────────────┘
└─────────────────┘
```

### 2.1 数据流

上行（传感器 → Web）：
终端CC2530采集 → ZigBee点播(Addr16Bit)到协调器0x0000 → 协调器UART0输出 → Python pyserial读取解析 → WebSocket推送至云端FastAPI → 存入SQLite + WebSocket推送到所有Vue3客户端

下行（控制命令）：
Web操作/自动控制触发 → FastAPI → WebSocket → Python串口脚本 → UART发送 → 协调器ZigBee点播转发 → 终端CC2530 GPIO控制LED/执行器

### 2.2 部署架构

- 本地PC：仅运行 Python 串口脚本（读写 USB 串口，WebSocket 连接云端）
- 云服务器：FastAPI + Vue3 + SQLite，通过公网 IP:端口 对外服务
- 代码同步：git push 部署

## 3. 硬件设计

### 3.1 硬件清单

| 模块 | 型号 | 数量 | 用途 |
|------|------|------|------|
| 主控芯片 | CC2530（8051内核，内置IEEE 802.15.4） | 2 | 终端节点 + 协调器 |
| 温湿度传感器 | DHT11（单总线，P2.0） | 1 | 温度和湿度采集 |
| 显示屏 | OLED 128x64 | 1 | 本地数据显示 |
| 蓝牙模块 | MX-01 BLE（UART1，P0.4/P0.5） | 1 | 备用近场控制通道 |
| LED | LED1(P1.0) LED2(P1.1) LED3(P1.6) | 3 | 模拟执行器 |
| 其他传感器 | 待定（光照/土壤/红外模块，实验室确认） | - | 如无则固件模拟数据 |

### 3.2 执行器映射

| GPIO | LED | 模拟执行器 | 开启命令 | 关闭命令 |
|------|-----|-----------|---------|---------|
| P1.0 | LED1 | 水泵 | BLEGLED1 | BLEKLED1 |
| P1.1 | LED2 | 施肥泵 | BLEGLED2 | BLEKLED2 |
| P1.6 | LED3 | 天窗 | BLEGLED3 | BLEKLED3 |

### 3.3 OLED 显示设计

128x64 分辨率，翻页显示多页信息：

页面1（主要数据）：
- 第1行：智慧农业监控
- 第2行：T:25°C  H:60%
- 第3行：L:800lux S:45%
- 第4行：水泵:ON 施肥:OFF

页面2（状态信息）：
- ZigBee 组网状态
- 蓝牙连接状态
- 报警提示（超阈值时显示）

## 4. 通信协议

### 4.1 ZigBee 通信

- 协议栈：Z-Stack
- 通信方式：点播（Addr16Bit），终端 → 协调器 0x0000
- 开发环境：IAR Embedded Workbench
- 复用基础：实验6（点播数据通信）、实验7（温度传输通信）

### 4.2 串口协议

UART0，波特率 115200，数据格式沿用实验既有格式：

上行数据：`t:25-h:60-l:800-s:45\r\n`
- t: 温度（°C）
- h: 湿度（%）
- l: 光照（lux）
- s: 土壤湿度（%）

下行命令：固定字符串，CC2530 用 strstr() 匹配
- `BLEGLED1` / `BLEKLED1` — 水泵 开/关
- `BLEGLED2` / `BLEKLED2` — 施肥 开/关
- `BLEGLED3` / `BLEKLED3` — 天窗 开/关

### 4.3 蓝牙通信（备用通道）

- 模块：MX-01 BLE，UART1（P0.4/P0.5，115200）
- 设备名：NB-2023442188
- 上行格式：t:xx-h:xx\r\n
- 下行命令：与串口相同（BLEGLED/BLEKLED系列）
- 连接检测：+C 连接 / +D 断开

## 5. 软件设计

### 5.1 技术栈

| 层次 | 技术 | 说明 |
|------|------|------|
| 固件 | C + Z-Stack + IAR | CC2530 传感器采集、ZigBee通信、GPIO控制 |
| 串口脚本 | Python + pyserial + websockets | 串口读写 + WebSocket桥接 |
| 后端 | FastAPI + SQLite + WebSocket | REST API + 实时推送 + 自动控制逻辑 |
| 前端 | Vue3 + Element Plus + ECharts | 响应式 Web 界面 |

### 5.2 项目目录结构

```
smart-agriculture-monitor/
├── PRD.md                      # 本文档
├── firmware/                   # CC2530 固件代码
│   ├── end_device/             # 终端节点固件
│   └── coordinator/            # 协调器固件
├── serial_bridge/              # 本地串口桥接脚本
│   ├── bridge.py               # 串口 ↔ WebSocket 桥接
│   └── requirements.txt        # pyserial, websockets
├── backend/                    # FastAPI 后端
│   ├── main.py                 # FastAPI 应用入口
│   ├── models.py               # SQLAlchemy 模型
│   ├── schemas.py              # Pydantic 数据模型
│   ├── control.py              # 自动控制逻辑
│   ├── database.py             # SQLite 连接配置
│   └── requirements.txt        # fastapi, uvicorn, aiosqlite...
└── frontend/                   # Vue3 前端
    ├── src/
    │   ├── views/
    │   │   ├── Dashboard.vue   # 实时监控看板
    │   │   ├── History.vue     # 历史数据查询
    │   │   ├── Settings.vue    # 系统设置
    │   │   └── AlarmLog.vue    # 报警日志
    │   ├── components/         # 公共组件
    │   ├── stores/             # Pinia 状态管理
    │   └── utils/
    │       └── websocket.js    # WebSocket 连接管理
    └── package.json
```

### 5.3 数据库设计

**sensor_data 表** -- 传感器历史数据
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| timestamp | DATETIME | 采集时间 |
| temperature | FLOAT | 温度 °C |
| humidity | FLOAT | 湿度 % |
| light | FLOAT | 光照 lux |
| soil_moisture | FLOAT | 土壤湿度 % |

**thresholds 表** -- 阈值配置
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | - |
| param_name | TEXT | 参数名（temperature/humidity/light） |
| min_value | FLOAT | 下限阈值 |
| max_value | FLOAT | 上限阈值 |

**alarm_log 表** -- 报警日志
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | - |
| timestamp | DATETIME | 报警时间 |
| param_name | TEXT | 触发参数 |
| value | FLOAT | 触发时的值 |
| threshold | FLOAT | 对应阈值 |
| action | TEXT | 执行的控制动作 |

**control_log 表** -- 控制操作记录
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | - |
| timestamp | DATETIME | 操作时间 |
| device | TEXT | 执行器（pump/fertilizer/skylight） |
| action | TEXT | 操作（ON/OFF） |
| source | TEXT | 来源（auto/manual） |

### 5.4 后端 API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| WebSocket | /ws/data | 实时数据推送 + 控制命令双向通信 |
| WebSocket | /ws/bridge | 串口桥接脚本专用连接 |
| GET | /api/history | 历史数据查询（支持时间范围筛选） |
| GET | /api/thresholds | 获取当前阈值配置 |
| PUT | /api/thresholds | 更新阈值配置 |
| GET | /api/alarms | 报警日志查询 |
| GET | /api/status | 系统状态（设备在线、执行器状态、当前模式） |
| POST | /api/control | 手动控制命令 |
| PUT | /api/mode | 切换手动/自动模式 |

### 5.5 自动控制逻辑

控制决策在 FastAPI 后端执行：

```
每次收到传感器数据时：
  if 当前模式 == 自动:
    if 温度 < 温度下限阈值:
      发送 BLEGLED1（开水泵）
      记录报警日志 + 推送Web报警
    elif 温度 > 温度上限阈值:
      发送 BLEKLED1（关水泵）

    if 湿度 < 湿度下限阈值:
      发送 BLEGLED2（开施肥）
    elif 湿度 > 湿度上限阈值:
      发送 BLEKLED2（关施肥）

    if 光照 < 光照下限阈值:
      发送 BLEGLED3（关天窗/遮光）
    elif 光照 > 光照上限阈值:
      发送 BLEKLED3（开天窗）
```

手动模式下，自动控制不介入，仅记录超阈值报警。

### 5.6 Web 前端页面

**页面1 -- 实时监控看板 (Dashboard)**
- 顶部：系统状态栏（设备在线状态、当前模式、连接指示）
- 中部：ECharts 仪表盘（温度、湿度、光照、土壤湿度各一个表盘）
- 下部：ECharts 实时曲线图（最近 N 分钟的数据趋势）
- 右侧：执行器控制面板（水泵/施肥/天窗的开关按钮 + 当前状态）

**页面2 -- 历史数据查询 (History)**
- 时间范围选择器（开始时间 - 结束时间）
- ECharts 折线图（多参数叠加显示）
- Element Plus 数据表格（分页显示详细记录）
- 导出功能（可选）

**页面3 -- 系统设置 (Settings)**
- 阈值配置表单（温度/湿度/光照的上下限）
- 控制模式切换（手动/自动）
- 数据采集频率配置
- 保存按钮

**页面4 -- 报警日志 (AlarmLog)**
- 报警记录表格（时间、参数、触发值、阈值、执行动作）
- 筛选条件（时间范围、参数类型）
- 报警统计摘要

## 6. 默认配置

| 参数 | 下限 | 上限 |
|------|------|------|
| 温度 | 18°C | 35°C |
| 湿度 | 30% | 80% |
| 光照 | 200 lux | 2000 lux |
| 土壤湿度 | 25% | 75% |

数据采集周期：2 秒

## 7. 答辩要点

系统涉及的核心原理（可能被提问的方向）：

1. **ZigBee 协议栈**：IEEE 802.15.4 物理层、Z-Stack 网络层、协调器/终端节点角色、点播寻址模式（Addr16Bit）
2. **传感器原理**：DHT11 单总线时序、数据帧格式（5字节：湿高+湿低+温高+温低+校验）
3. **串口通信**：UART 异步通信原理、波特率配置、数据帧格式
4. **WebSocket**：全双工通信原理、与 HTTP 的区别、心跳保活机制
5. **自动控制逻辑**：阈值判断、执行器联动、手动/自动模式切换
6. **系统分层架构**：感知层（传感器+MCU）→ 网络层（ZigBee+串口+WebSocket）→ 应用层（FastAPI+Vue3）
