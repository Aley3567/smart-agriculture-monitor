# Trace Bullet 总要求追踪矩阵

最后核对日期：2026-06-30

本文只记录当前仓库能证明的事实、缺口和下一步工作包。它不是最终验收报告；云端和现场串口链路还需要按本文的验证清单补证据。

## 0. 总体结论

当前系统不是四条 Trace Bullet 全部完成，但 P0 软件闭环已完成：测试注入追溯、土壤湿度自动浇水规则、安全关泵/冷却、前端测试模式、历史/告警真实与测试过滤都已有本地接口和前端入口。

当前项目按单板课程设计收口：只有一套 C/ED 板链路；施肥泵、灭虫灯、CO2、土壤 EC/TDS/肥力、红外按课程演示的模拟/模型字段处理，不再追问真实负载或新增硬件条件。

硬件验收按 C/ED 双板架构执行：

- C 板（Coordinator）只负责接 PC 串口和 `serial_bridge`，把 ED 的 ZigBee 上行转成 UART，并把 bridge 下发命令转回 ED。
- ED 板（End Device）负责 DHT11、GL5516/P0.7 光照 ADC、OLED 和执行器/指示灯；所有传感器、OLED、继电器/LED 的现场证据都必须来自 ED。

可以较稳证明的部分：

- 上行链路已成型：终端固件发送 `t/h/l/s`，协调器转 UART，`serial_bridge` 转 `/ws/bridge`，后端入库并通过 `/ws/data`/`/api/history` 给前端。
- 温度、空气湿度是真实 DHT11 采集；光照固件已改为 GL5516/P0.7 ADC 相对光照值，未现场验收前仍标为待 smoke；土壤湿度目前是固件模拟值。
- 后端已有 `/api/sensor-fields`、`/api/history` 的 `fields/facts` 来源合同；前端已能展示字段来源，CO2/EC/TDS/土壤肥力/红外已按模型字段返回。
- 后端已有 `/api/history?source=all|real|test`、`/api/alarms?source=all|real|test`，items 带 `source/is_test`；前端 History/AlarmLog 可按真实/测试过滤，并对测试注入记录打标。
- `POST /api/test/sensor-sample` 可写入测试历史和测试告警，测试记录不会伪装成真实板卡在线或真实采样。
- 土壤湿度低于自动浇水规则时，auto 模式会触发水泵；manual 模式只告警不自动控制；规则包含关泵阈值、最长运行和冷却约束。
- 三路手动控制已对齐为 `pump`、`fertilizer`、`pest_light`，底层命令仍是 `BLEGLED1/2/3` 和 `BLEKLED1/2/3`。
- 后端已有控制合法性校验、`ControlLog` 查询、多板 `board_id` 控制路由、基础告警和历史查询。

仍要完成或现场验证的部分：

- OLED 显示代码已嵌入 ED 固件，但受 `HAL_OLED` 编译开关控制；P1 必做是编译启用并现场显示温度、空气湿度、光照相对值。
- “数据异常时流水灯报警”已按 `BLEALARM1/BLEALARM0` 进入后端和 ED 固件代码；还缺编译烧录和现场视频/照片验证。
- CO2、土壤 EC、土壤 TDS、土壤肥力、红外已按课程设计口径实现为后端模拟/计算字段，不能标成硬件实测。
- 土壤肥力阈值已进入后端默认阈值，前端 Settings 已开放配置。
- 云端部署脚本和 bridge 命令存在，但当前没有本轮真实公网、现场串口、OLED、流水灯验收记录。

## 1. Trace Bullet 逐条状态

| Trace Bullet | 当前状态 | 已实现 | 不对/风险 | 未完成 | 关键证据 | 当前测试 | 下一步切片 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1. 温度、湿度、光照能实时在 OLED 屏幕显示数据并向上位机发送数据 | 部分完成 | 固件周期发送 `t/h/l/s`；C 板转 UART；bridge 可推云端；前端 WS 实时更新；OLED 刷新函数存在 | 温湿度真实；光照应走 ED 板 GL5516/P0.7 ADC 相对值，未 smoke 前不能宣称 lux；OLED 受 `HAL_OLED` 控制，缺现场实测 | 启用/适配 OLED 驱动；光照 ADC 接入并现场遮光/照光；补硬件验收记录 | `firmware/end_device/SampleApp.c` 的 `SampleApp_SendPeriodicMessage()`、`SampleApp_UpdateOLED()`；`serial_bridge/bridge.py`；`backend/main.py /ws/bridge`；`frontend/src/utils/websocket.js` | 后端合同测试覆盖 history/facts；未覆盖固件编译/OLED/真实串口 | P1 第一条 smoke：C 串口输出 `t/h/l/s` -> bridge `sensor` 日志 -> 云端上位机实时/历史；P1 必做 OLED 只显示温度、空气湿度、光照相对值 |
| 2. 数据异常时流水灯报警。当湿度不够，APP 自动开启水泵浇水 | 部分完成 | 后端阈值检测会写 `AlarmLog` 并广播 alarm；异常恢复会向 ED 下发 `BLEALARM1/BLEALARM0`；前端 Dashboard 有异常特别显示；auto 模式下土壤湿度低会按规则触发 `pump on`；规则包含安全关泵、最长运行和冷却 | 土壤湿度按课程模拟值处理；流水灯和自动浇水还缺烧录后的板端验证 | 编译烧录后验证 ED 流水灯表现；补自动浇水现场控制验收 | `backend/control.py evaluate_thresholds()`；`backend/config.py ALARM_LIGHT_COMMAND_MAP`；`firmware/end_device/SampleApp.c` 的 `BLEALARM1/BLEALARM0`；`backend/main.py /api/control-rules/soil-moisture-pump`；`frontend/src/views/Dashboard.vue` breach class | 后端测试覆盖告警 trace、异常开/关 `BLEALARM1/BLEALARM0`、manual mode 不自动控制、土壤低自动泵、安全关泵/冷却 | 自动浇水 smoke 必须同时有 `ControlLog`、bridge 命令、ED 水泵/继电器响应；土壤湿度按模拟演示口径说明 |
| 3. 手动开关普通浇水、手动开关施肥水泵、手动开关灭虫灯 | 基本完成 | 前端 Dashboard/Settings 调 `/api/control`；后端校验 `device/action` 并记录 `ControlLog`；bridge 按 `board_id` 下发命令；固件支持 `BLEGLED1/2/3`、`BLEKLED1/2/3` | 课程设计按单板模拟执行器验收，施肥和灭虫以板端 LED/指示表现为准 | 三路都必须做 smoke，记录前端点击、bridge 命令和板端指示响应 | `backend/main.py /api/control`；`backend/config.py DEVICE_COMMAND_MAP`；`backend/ws_manager.py`；`serial_bridge/bridge.py`；`firmware/end_device/SampleApp.c` 控制解析 | 后端测试覆盖非法参数 400、合法控制写日志、`pest_light` 命令、`skylight` 兼容、多板不 fallback | P0/P1 smoke：三路各自 on/off 都有 `ControlLog`、bridge 命令和 ED 端响应 |
| 4. 上位机查看温湿度、CO2、土壤湿度、TDS/电导率、红外数据；配置土壤湿度、土壤肥力阈值；不满足阈值特别显示；查看近期历史数据 | 基本完成 | 上位机可看温度、空气湿度、光照、土壤湿度；CO2/EC/TDS/土壤肥力/红外由后端模型 facts 动态生成；土壤湿度和土壤肥力阈值可配置；Dashboard/History/CSV 可查看模型字段；异常可特别显示并写 AlarmLog | 模型字段按课程模拟/计算口径，未做真实传感器；仍需本地页面 smoke 和答辩口径确认公式 | 启动前后端做页面 smoke；记录模型公式和来源说明 | `backend/sensor_facts.py` `compute_model_values()`；`backend/config.py DEFAULT_THRESHOLDS`；`backend/control.py check_and_control()`；`frontend/src/utils/sources.js`；`frontend/src/views/Dashboard.vue`；`frontend/src/views/History.vue`；`frontend/src/views/Settings.vue` | 后端测试已覆盖模型字段从 pending 改为 simulated/computed、肥力阈值参与告警、自动浇水不受肥力阈值影响；前端构建通过 | 第 4 点不再等硬件，剩页面联调和验收截图 |

## 2. 当前接口合同

### 后端 REST

- `GET /api/sensor-fields`：返回字段目录，标明 `source/available/pending/unit` 等。
- `GET /api/history?board_id=&source=all|real|test&start=&end=&page=&page_size=`：返回历史 items，并带 `fields`；每条 item 带 `facts/source/is_test`。
- `GET /api/thresholds` / `PUT /api/thresholds`：读取/更新阈值。当前默认有 `temperature/humidity/light/soil_moisture`。
- `GET /api/alarms?board_id=&source=all|real|test&start=&end=&page=&page_size=` / `GET /api/alarms/summary`：读取告警和统计；告警输出层可派生 `param_label/unit/source/is_test/sensor_data_id/direction`。
- `GET /api/control-log`：读取控制日志，支持分页和时间/板卡过滤。
- `POST /api/control`：手动控制，当前合同是未知 `device/action` 返回 400；合法控制写 `ControlLog(source="manual")`。
- `GET/PUT /api/control-rules/soil-moisture-pump`：读取/更新土壤湿度自动浇水规则，包含启动阈值、停止阈值、连续样本、最长运行和冷却时间。
- `POST /api/test/sensor-sample`：注入测试采样，写入 `SensorData(source="demo_injection", is_test=true)`，必要时写入测试告警并关联 `sensor_data_id`。
- `GET /api/boards` / `GET /api/boards/{board_id}` / `GET /api/status`：板卡和系统状态。

### WebSocket

- `/ws/bridge`：bridge 注册和上报数据。典型 payload：

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

- `/ws/data`：前端实时通道，接收 `sensor_data/status/alarm/control_status` 等。

### 当前设备语义

| 上层 device | 产品语义 | 底层 on | 底层 off | 备注 |
| --- | --- | --- | --- | --- |
| `pump` | 普通浇水/水泵 | `BLEGLED1` | `BLEKLED1` | ED 板 P0.6 继电器 + P1.0 指示；报警流水灯不能覆盖继电器状态 |
| `fertilizer` | 施肥水泵/施肥指示 | `BLEGLED2` | `BLEKLED2` | 当前硬件证据主要是 LED2 指示 |
| `pest_light` | 灭虫灯 | `BLEGLED3` | `BLEKLED3` | `skylight` 仅作为后端兼容 alias |

## 3. 土壤计算口径

尚未完成的关键点：

- 按课程设计确定模型字段的模拟公式和版本。
- 土壤湿度、土壤 EC、TDS、肥力、CO2、红外要输出模拟/模型值，并保留 `source` 和 `formula_version`。
- 土壤肥力阈值应作用在模型输出后的 `soil_fertility`。
- 计算结果需要持久化，保证近期历史和导出可解释。

验收边界：

- CO2、红外、EC/TDS/土壤肥力按课程模拟/模型字段处理，不能标成硬件实测。
- 模拟/模型值必须明确 `source="simulated_backend"` 或 `source="computed_backend"`，不能混成真实传感器。
- 光照直接走 GL5516/P0.7 ADC 时，口径是“相对光照值”，不再宣称 lux；未现场 smoke 前仍标待验收。

建议的最小合同：

- 串口/bridge 不把模型计算结果伪装成硬件直出；板端只上报 `t/h/l/s`，后端补模型字段。
- 后端 facts 同时保留来源：
  - `soil_moisture`: `source="simulated_firmware"`。
  - `co2`、`soil_ec`、`soil_tds`、`soil_fertility`、`infrared`: 使用 `source="simulated_backend"` 或 `source="computed_backend"`。
- 每个 computed fact 带 `derived_from` 和 `formula_version`，避免历史数据无法解释。
- 阈值只对可解释的最终指标生效，例如 `soil_moisture` 和 `soil_fertility`，不直接对未命名 raw 字段报警。

## 4. Smoke 验收边界

P1 第一条 smoke 是硬件链路基准：

1. C 板串口持续输出 `t/h/l/s`。
2. `serial_bridge` 日志出现对应 `sensor` 数据。
3. 云端上位机实时 Dashboard 和历史接口都能看到同一板卡的新记录。

各 Trace Bullet 的现场证据边界：

- TB1：温度、空气湿度、光照相对值必须在 OLED 显示；上位机实时/历史同步。土壤 `s` 继续上报给上位机，不放进 OLED。
- TB2：自动浇水控制链路必须有 `ControlLog`、bridge 下发命令、ED 板水泵/继电器响应证据。土壤湿度按课程模拟值触发。流水灯报警由后端下发 `BLEALARM1/BLEALARM0`，ED 本地执行，且不改变水泵继电器状态。
- TB3：`pump`、`fertilizer`、`pest_light` 三路手动 on/off 都必须 smoke；课程设计以单板继电器/LED/指示响应为验收对象。
- TB4：CO2、红外、EC/TDS/肥力按模拟/模型字段补齐，不能标成硬件实测。

## 5. 验证与证据缺口

已能跑的本地验证：

```bash
python3 -m unittest discover -s backend/tests -p 'test*.py'
cd frontend && npm run build
```

本轮验证结果：

- `python3 -m unittest discover -s backend/tests -p 'test*.py'`：通过，35 tests OK。
- `cd frontend && npm run build`：通过，Vite 仍提示产物 chunk 超过 500 kB。
- 未启动本地服务，未访问 Chrome，未做真实硬件/OLED/串口/公网 smoke。

当前已知测试覆盖：

- `/api/history` 返回 `fields/facts`。
- `/api/history?source=real|test` 和 `/api/alarms?source=real|test` 可分离真实记录与测试注入记录。
- `/api/test/sensor-sample` 写测试历史/测试告警，并通过 `source/is_test/sensor_data_id` 追溯。
- `/api/sensor-fields` 对模型字段标记 `simulated_backend` 或 `computed_backend`。
- `/api/status` 返回 `server_time`。
- `/api/control` 对非法设备/动作返回 400。
- 合法手动控制写 `ControlLog`。
- `pest_light` 命令和 `skylight` 兼容 alias。
- `/api/control-log` 分页/时间/板卡筛选。
- 多板 bridge 注册、替换、控制不 fallback。
- 告警输出派生 trace 字段。

仍缺测试/验收：

- 固件 IAR/编译通过记录。
- OLED 显示温度、空气湿度、光照相对值的现场照片或日志。
- C 板串口和 bridge 持续接收 `t/h/l/s` 的日志。
- 云端 `/api/status`、`/api/boards`、`/api/history?board_id=A` 的当前公网 smoke。
- 土壤低湿自动水泵已有后端接口测试；仍缺单板现场 smoke。
- 流水灯报警的 `BLEALARM1/BLEALARM0` 协议和固件代码已有；仍缺烧录后的现场视频，并证明不破坏水泵继电器状态。
- CO2/EC/TDS/土壤肥力/红外已由后端 facts 动态计算；土壤肥力阈值已联动告警。
- `GET/PUT /api/thresholds` 的非法字段、更新、范围校验测试。
- 前端 WebSocket 生产环境变量缺失时的 fallback 验证。

## 6. 链接与运行入口

云端入口来自当前部署脚本：

- Web：`http://119.91.114.175:18082`
- API 健康：`http://119.91.114.175:18082/api/status`
- 板卡状态：`http://119.91.114.175:18082/api/boards`
- 历史查询：`http://119.91.114.175:18082/api/history?board_id=A`

现场 bridge 示例：

```bash
python3 serial_bridge/bridge.py \
  --port /dev/tty.usbserial-xxxx \
  --baud 115200 \
  --server ws://119.91.114.175:18082/ws/bridge \
  --board-id A \
  --board-name greenhouse-a
```

无串口 mock 示例：

```bash
python3 serial_bridge/mock_push.py \
  --server ws://119.91.114.175:18082/ws/bridge \
  --interval 1
```

## 7. 工作包分派

### P0-A：事实追踪与验收证据（已完成软件追踪）

目标：让演示前能清楚说明哪些是真实、哪些是模拟、哪些 pending。

- 输出本文档并保持更新。
- 跑后端 unittest、前端 build。
- History/AlarmLog 对测试注入记录显示 `测试注入`，CSV 导出包含 `source/is_test`，告警保留 `sensor_data_id`。
- 现场补 bridge 日志、云端 smoke、OLED/控制视频或照片。

验收：

- 本文档每条 Trace Bullet 都有状态、证据、测试和下一步。
- 证据不再只存在聊天记录里。

### P0-B：土壤自动浇水合同（已完成后端合同）

目标：把“湿度不够自动开水泵”落到后端公开行为。

- 字段已按 `soil_moisture` 低于阈值触发 `pump on` 处理。
- 已有公开接口/WS ingest 测试，验证低土壤湿度在 auto 模式下写 `AlarmLog` 和 `ControlLog(source="auto")`，并向目标 `board_id` 下发 `BLEGLED1`。
- 已实现 `soil_moisture -> pump`。
- 已保留 manual 模式只告警不控制的测试。

### P0-C：土壤计算与模型字段

目标：让上位机能看到可解释的课程模拟/模型结果。

- 已实现：`/api/history` 与 `/ws/data` facts 中 `co2/soil_ec/soil_tds/soil_fertility/infrared` 有值、有来源、有 `formula_version`。
- 需要历史回放时，优先持久化计算输出或存 raw + formula_version。
- 已实现：前端解除 `soil_fertility` 阈值禁用，模型字段在 Dashboard/History 中显示。

### P0-D：云端/板卡链路验收

目标：证明电脑可实时接收板子数据，并让云端/前端同步波动。

- 运行真实 bridge，确认日志持续出现 `sensor >> board=A {...}`。
- `curl /api/history?board_id=A` 能看到最新记录。
- 前端 Dashboard 能看到实时变化。
- 控制按钮点击后，bridge 日志出现对应命令，板端实际响应。

### P1-A：OLED 与流水灯

目标：补齐板端显示和异常本地报警。

- OLED：P1 必做。代码已嵌入 ED 固件；确认 `HAL_OLED`、驱动头文件和引脚，编译通过后现场验证温度、空气湿度、光照相对值。
- 流水灯：后端已发送 `BLEALARM1/BLEALARM0`，ED 固件已有本地流水灯表现；剩余是烧录和现场验证，且不能覆盖 `pump` 继电器状态。

### P1-B：模拟/模型字段扩展

目标：课程要求里的 CO2、EC/TDS、肥力、红外已从 pending 变成可解释的模拟/模型字段。

- 明确每个模型字段的单位、范围、公式版本和来源。
- 后端补 facts/history/alarms/thresholds，不要求新增真实硬件协议。
- 后端 schema/facts/history/alarms 一起补测试。

## 8. 当前开放问题

1. “湿度不够自动开启水泵”是否正式解释为土壤湿度 `soil_moisture`，而不是空气湿度 `humidity`？
2. CO2、土壤 EC/TDS、土壤肥力、红外已采用 `compute_model_values()` v1 公式；答辩时按后端模型字段说明。
3. 土壤肥力阈值已开放配置，单位按百分比处理。
4. OLED 与流水灯用当前 ED 固件实现烧录后，现场视频/照片路径记录在哪里？
