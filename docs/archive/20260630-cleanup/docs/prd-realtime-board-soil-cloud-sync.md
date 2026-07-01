# 本地到云端实时板卡接入与土壤计算 PRD

## 1. 背景

当前项目已经从早期单板、四字段演示，推进到后端多板 `board_id`、控制日志、传感器来源合同和前端来源展示的阶段。旧 `PRD.md` 仍描述 `t/h/l/s` 串口字段直接代表温度、湿度、光照、土壤湿度，其中 `s` 被当成土壤湿度。这与最新口径不一致。

新的产品口径是：

- 本地仓库是当前真实开发源头，先在本地修复、验证，再上传云端更新版本。
- 现场电脑或边缘机通过 `serial_bridge` 接协调器串口，电脑实时接收板端数据并推送到云端后端，不再依赖串口助手作为展示入口。
- 板端真实采集优先只承载硬件可信字段；土壤湿度、EC、TDS、肥力等由后端模型或后端计算链路统一生成，并通过 `fields/facts` 标明来源。
- 多板接入必须通过 `board_id` 区分，历史、告警、控制日志、控制下发不能混板。

## 2. 当前事实

### 2.1 已落地能力

- `serial_bridge/bridge.py` 可读取串口行，解析 `t/h/l/s`，注入 `board_id` 和 `board_name` 后推送 `/ws/bridge`。
- `backend/main.py` 已支持 `/ws/bridge`、`/ws/data`、`GET /api/history`、`GET /api/alarms`、`GET /api/control-log`、`GET /api/boards`、`GET /api/status`。
- 后端 `SensorData`、`AlarmLog`、`ControlLog`、`Board` 已有 `board_id` 字段或板卡表。
- 后端 `GET /api/sensor-fields`、`GET /api/history`、WebSocket `sensor_data` 已返回 `fields/facts`。
- 前端 WebSocket 已能消费 `sensor_data.fields` 和 `sensor_data.facts`；store 已开始按 facts 归一动态字段，但部分页面图表和请求参数仍以单板、四字段为核心。
- 部署脚本 `scripts/deploy.sh` 会从本地构建前端并上传 `backend/`、`serial_bridge/`、`frontend/dist/` 到腾讯云服务器。

### 2.2 仍不一致的地方

- 固件和 bridge 仍把 `s` 当单个土壤湿度值；设计交接已要求后端生成土壤模型字段，短期可保留 `s` 兼容但后端不应把它当真实土壤传感器。
- 后端 `sensor_facts.py` 中 `soil_ec`、`soil_tds`、`soil_fertility` 仍是 `pending`，没有实时计算值。
- `/ws/data` 的控制消息已有 `board_id` schema，但前端控制请求仍未显式传板号。
- 前端页面层仍有固定 `temp/humi/light/soil` 的图表和文案，模型字段的完整趋势展示还未完成。
- `device_online` 仍是全局状态，不能完全表达 A/B/C 多板在线。
- 云端 systemd 只启动 FastAPI；真实串口 bridge 应在连着协调器的现场电脑或边缘机运行。

## 3. 产品目标

1. 现场板子接入后，Web 页面能看到对应板卡在线、最近上报时间、实时数据波动和控制状态。
2. 电脑通过 `serial_bridge` 自动接收协调器串口数据并上传云端，串口助手只作为排障工具。
3. 土壤湿度、EC、TDS、肥力等不由串口最终显示值冒充，统一由后端模型或后端计算输出。
4. 后端输出每个字段的来源、可用性和值，前端按合同动态展示，不硬猜字段来源。
5. 多板历史、告警、控制日志和控制下发都必须带 `board_id`，控制 B 板不能误落到 A 板。
6. 本地测试和构建通过后，再用部署脚本上传云端；不从旧云端版本反向覆盖本地大改。

## 4. 非目标

- 本 PRD 不一次性重写前端视觉稿。
- 本 PRD 不在未确认硬件字段名、单位和公式前硬造“两路土壤原始量”的生产串口协议。
- 本 PRD 不把串口助手作为业务展示入口。
- 本 PRD 不把室外天气土壤含水量当作棚内土壤模型主输入。

## 5. 数据合同

### 5.1 板卡身份

默认板卡：

| board_id | board_name | 用途 |
| --- | --- | --- |
| A | greenhouse-a | 默认演示板 |
| B | greenhouse-b | 第二块板或备用板 |
| C | greenhouse-c | 扩展板 |

bridge 注入模式：

```bash
python3 serial_bridge/bridge.py \
  --port /dev/tty.usbserial-xxxx \
  --baud 115200 \
  --server ws://119.91.114.175:18082/ws/bridge \
  --board-id A \
  --board-name greenhouse-a
```

bridge 连接后先发：

```json
{
  "type": "bridge_hello",
  "board_id": "A",
  "board_name": "greenhouse-a"
}
```

传感器上报：

```json
{
  "type": "sensor_data",
  "board_id": "A",
  "board_name": "greenhouse-a",
  "data": {
    "temp": 25.0,
    "humi": 60.0,
    "light": 50.0,
    "soil": 45.0
  }
}
```

### 5.2 串口协议阶段

阶段 1：兼容当前固件。

```text
t:25-h:60-l:50-s:45
```

解释：

- `t`、`h` 来自 DHT11。
- `l` 当前可来自固件模拟，完成 P0.7 ADC 后改为实测来源。
- `s` 仅作为旧协议兼容值；业务口径不能把它说成真实土壤传感器。

阶段 2：固件携带板卡身份。

```text
id:B-t:25-h:60-l:50-s:45
```

解释：

- 用于一个协调器接收多个终端节点时区分来源板。
- bridge 优先使用串口行里的 `id`，否则使用启动参数 `--board-id`。
- 当前阶段 `id` 只声明数据来源；控制链路仍以 bridge 启动参数里的 `--board-id` 作为可控目标。一个协调器多终端定向控制需要后续增加 `board_id -> ZigBee shortAddr` 或板端命令过滤协议。

阶段 3：后端土壤模型稳定后，逐步弱化或去掉 `s`。

```text
t:25-h:60-l:50
```

解释：

- 后端根据温度、空气湿度、光照、执行器状态、时间步长和确认后的模型状态生成土壤字段。
- 进入该阶段前，后端必须先支持缺失 `soil` 的 ingest 合同和模型恢复逻辑。

### 5.3 土壤计算合同

后端最终输出字段：

| key | param | 来源 | 单位 | 说明 |
| --- | --- | --- | --- | --- |
| soil | soil_moisture | simulated_backend 或 computed_backend | % | 土壤湿度模型值 |
| soil_ec | soil_ec | simulated_backend 或 computed_backend | dS/m | 后端维护的 EC 主状态 |
| soil_tds | soil_tds | simulated_backend 或 computed_backend | ppm | 由 EC 换算，约 `soil_ec * 640` |
| soil_fertility | soil_fertility | simulated_backend 或 computed_backend | % | 由 EC 归一化得到 |

待确认项：

- 如果硬件确实提供两个土壤原始量，需要确认字段名、单位、量程和含义。
- 需要确认两个原始量到 `soil/soil_ec/soil_tds/soil_fertility` 的正式公式。
- 在确认前，代码只能保留扩展点或使用明确标记为模型仿真的值，不能把猜测公式写成硬件事实。

### 5.4 后端实时消息

WebSocket `sensor_data` 必须包含：

```json
{
  "type": "sensor_data",
  "board_id": "A",
  "board_name": "greenhouse-a",
  "data": {
    "temp": 25.0,
    "humi": 60.0,
    "light": 50.0,
    "soil": 45.0
  },
  "fields": {
    "temp": {
      "key": "temp",
      "param": "temperature",
      "label": "温度",
      "unit": "°C",
      "source": "measured",
      "category": "measured",
      "available": true
    }
  },
  "facts": {
    "temp": {
      "key": "temp",
      "value": 25.0,
      "source": "measured",
      "available": true
    }
  },
  "timestamp": "2026-06-30T12:00:00Z"
}
```

前端必须优先消费后端 `fields/facts`，本地字段表只做 fallback。

## 6. 功能切片

### P0-A：多板控制路由收口

行为：

- `POST /api/control` 接收 `board_id/device/action`。
- 如果目标 `board_id` 没有对应 bridge 连接，后端仍可记录控制意图，但返回 `bridge_connected: false`。
- 后端不得把明确发给 B 板的控制命令 fallback 到 A 板 bridge。

验收：

- 只连接 A bridge，调用 `POST /api/control { board_id: "B", device: "pump", action: "on" }`，A bridge 不收到命令。
- `ControlLog.board_id` 记录为 B。

### P0-B：bridge 解析固件携带的 board_id

行为：

- `serial_bridge` 继续支持旧行 `t:25-h:60-l:50-s:45`。
- `serial_bridge` 新增支持 `id:B-t:25-h:60-l:50-s:45`。
- 串口行有 `id` 时，WebSocket payload 使用该 id；没有时使用启动参数。

验收：

- `parse_serial_payload("id:B-t:25-h:60-l:50-s:45")` 返回 `board_id=B` 和四个传感器值。
- 旧格式仍返回默认启动参数中的 `board_id`。

### P0-C：前端 store 动态消费 facts

行为：

- `sensor` store 从 `facts[key].value` 归一到 `current[key]`，不限于四个固定字段。
- `history` 按可用字段动态维护序列。
- Dashboard 和 History 后续只按 `fields` 分组渲染。

验收：

- 后端一旦返回 `soil_ec/soil_tds/soil_fertility` facts，前端 store 中能读到这些 key 的当前值。
- 前端 build 通过。

状态：

- 数据层已完成最小修复；页面图表和 board 选择透传仍待下一切片。

### P1-A：后端土壤模型

行为：

- 新增集中模型模块，输入 `temp/humi/light/actuators/delta_time` 和确认后的土壤原始量。
- 输出 `soil/soil_ec/soil_tds/soil_fertility`。
- `sensor_field_catalog()` 将可用模型字段标为 `simulated_backend` 或 `computed_backend`。

验收：

- `/api/history` 行内 `facts.soil_ec.value` 不为空且来源不是 `pending`。
- WebSocket 实时消息包含相同 facts。

### P1-B：持久化模型字段

行为：

- 数据库持久化模型输出和来源。
- 历史查询、导出、告警都能按模型字段追溯。

验收：

- 后端重启后能从最新采样恢复模型状态。
- `GET /api/history?board_id=A` 返回模型字段历史。

### P1-C：现场 bridge 运行与云端更新

行为：

- 云端部署 FastAPI/nginx/frontend。
- 现场电脑运行 bridge，连接本地串口和云端 `/ws/bridge`。
- 补充 bridge 鉴权或可信网络边界。

验收：

- 本地 `python3 -m unittest discover -s backend/tests -p 'test*.py'` 通过。
- 本地 `npm run build` 通过。
- 运行 `scripts/deploy.sh` 后，云端 `/api/status` 返回 200。
- 现场 bridge 日志持续出现 `sensor >> board=A ...`。

## 7. 实施顺序

1. PRD 固化当前合同和未知项。
2. TDD 修复 P0-A：目标板 bridge 缺失时不 fallback 到其他板。
3. TDD 实现 P0-B：bridge 支持 `id:` 板号前缀。
4. 最小前端数据层修复 P0-C，不改视觉稿。
5. 等硬件或用户确认两个土壤原始量的字段名/单位/公式后，实现 P1-A。
6. 本地全量验证后运行部署脚本上传云端。

## 8. 风险

- 两个土壤原始量没有正式字段和公式时，过早实现会把猜测写进云端合同。
- 多板控制如果 fallback 到默认 bridge，会造成远程误控。
- 前端如果继续单板四字段 store，会导致后端模型字段已经出来但页面不波动。
- 云端部署不等于现场串口接入，bridge 必须跑在连接协调器串口的机器上。
- `/ws/bridge` 当前缺少鉴权，公网部署需要增加令牌或限制网络入口。

## 9. 当前可立即实现的范围

本轮可以立即实现：

- P0-A：多板控制路由不 fallback。
- P0-B：bridge 解析 `id:` 板号前缀。

本轮暂不实现：

- 两个土壤原始量到模型字段的正式公式。
- 数据库大迁移。
- 前端视觉结构重排。
- 云端部署执行。
