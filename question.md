# Question — 全链路衔接问题追踪

## Final Goal

1. 温度、湿度、光照能实时在 OLED 屏幕显示数据并向上位机发送数据
2. 数据异常时流水灯报警。当湿度不够，APP 自动开启水泵浇水
3. 手动开关普通浇水、手动开关施肥水泵、手动开关灭虫灯
4. 在上位机查看温湿度、二氧化碳、土壤湿度、土壤 TDS 电导率传感器、红外传感器的数据。配置土壤湿度、土壤肥力阈值信息。当数据不满足阈值时，有特别显示。可查看近期历史数据

---

## 1. 温湿度光照实时显示 + 上位机数据发送

### 存在的问题

#### 1.1 OLED 显示未激活

固件 `SampleApp_UpdateOLED()` 已写好显示逻辑（三行：Smart Agri / T:xxC H:xx% / L:xxx），
所有 OLED 代码被 `#ifdef HAL_OLED` 包裹。

驱动文件实际**已存在**（HalOled.c/h、HalOledFont.h 都在 `firmware/end_device/` 下），
引脚配置正确（P1.2 SCK、P1.3 MOSI、P1.7 RES、P0.0 DC），init 序列完整。
唯一缺的是 **IAR 工程未定义 `HAL_OLED` 预处理宏**。

结果：编译能过（OLED 代码全部跳过），但屏幕不亮。
启用只需：IAR Preprocessor Defined Symbols 加 `HAL_OLED` + 确认 HalOled.c 在编译列表中 + 重新烧写。

#### 1.2 固件帧格式包含虚假的土壤字段

固件发送 `t:XX-h:XX-l:XXX-s:XX`，其中 `s` 来自 `SampleApp_SimulateSoil()` 伪随机数。
板上没有土壤传感器，这个值是假的。但 OLED 显示代码只显示 T/H/L 三个值——
说明写固件的人清楚板上没有土壤传感器，却在帧里塞了假数据。

#### 1.3 上位机数据链路本身完整

从固件到前端的数据传输链路代码没有断裂：

```
ED 板 DHT11+ADC → 组帧 → ZigBee Cluster1 → 协调器 UART 115200 + \r\n
  → bridge.py 解析 → WS → FastAPI ingest → DB 存储
  → WS 广播 → Vue3 Dashboard 实时卡片+趋势图
```

每 2 秒一轮（`SAMPLEAPP_SEND_PERIODIC_MSG_TIMEOUT = 2000`），代码验证无误。

#### 1.4 云端跑的全是假数据且标记混乱

线上 `119.91.114.175:18082` 的实际状况：

- **84,978 条记录**全部来自 `mock_push.py`，但 `is_test: false`，被当成真实数据
- `bridge_mode: "unknown"` — 追踪代码写了但没部署（13 个文件未提交）
- `device_online: false`，`boards: {}` — 当前无任何设备连接

#### 1.5 mock 光照值单位与阈值严重错配

| 来源 | light 值范围 | 说明 |
|------|-------------|------|
| 真实固件 | 0-100 | ADC 归一化相对值 |
| mock_push.py | 200-2000 | 模拟的原始量级 |
| 阈值 max | 90 | 按 0-100 设计 |

mock 的光照值（如 1299.7）永远超阈值 90，产生了 **30,220 条 `light_high` 假报警**。

#### 1.6 固件层隐患

- **缓冲区越界**：`cmd_data[cmd_len] = '\0'` 无边界检查（`end_device/SampleApp.c` 命令解析处）
- **DHT11 超时偏小**：timeout=100us，噪声环境下可能不够
- **传感器失败静默降级**：DHT11 读取失败时用上次值，不上报错误

#### 1.7 去掉 s 字段的连锁阻塞点

固件去掉 `s:XX` 后，以下各层会**硬性阻塞**，必须逐层适配：

**阻塞点 A — bridge.py 严格要求 4 字段**
`parse_serial_payload()` 第 70 行 `if len(data) == 4` 是硬性检查。
只发 3 字段（t/h/l）时，bridge 会把每一条消息判定为解析失败，一条数据都到不了后端。
→ 需改为 `len(data) >= 3` 或按需灵活判断。

**阻塞点 B — 后端 ingest 直接取 `values["soil"]`**
`main.py` 第 123 行直接字典取值，无 `.get()` 兜底。
soil 字段不存在 → `KeyError` → 整个 ingest 函数崩溃，数据丢失。
→ 需改为 `.get("soil")` 并走模型推导。

**阻塞点 C — 数据库 soil 列不可为空**
`models.py` 第 19 行 `soil: Mapped[float] = mapped_column(Float)` 无 `nullable=True`。
即使代码传了 None，数据库插入也会失败。
→ 需要改为 nullable 或改为存模型推导值。

**阻塞点 D — 模型公式 soil 默认 0 的后果**
`compute_model_values()` 第 123 行 `soil = float(values.get("soil") or 0)`。
soil=0 代入后：soil_ec≈0.65（正常 1.0-1.5）、soil_fertility≈37%（正常 60-80%）。
→ 严重偏低，必然触发肥力报警 + 自动灌溉一直开。
→ soil 必须从"输入"变成"输出"：先由 temp/humi/light 推导 soil，再算 EC/TDS/fertility。

**阻塞点 E — 控制逻辑依赖 soil_moisture 参数**
`control.py` 第 108 行 `check_and_control()` 要求 `soil_moisture: float`。
当前从 `values["soil"]` 取值。改为云端推导后，调用顺序必须变成：
先 `compute_model_values()` 算出 soil → 再传给 `check_and_control()`。

### 讨论确认

- [x] 固件帧格式：**去掉 `s` 字段**，只发 `t:XX-h:XX-l:XXX`，土壤湿度完全由云端模型推导
- [x] 上位机数据链路代码本身无问题，问题出在数据源（mock）和标记（bridge_mode 未部署）
- [x] 固件可以烧写，后续改帧格式 + 修隐患 + 启用 OLED 一起做
- [x] 云端上线前需要清理 8.5 万条 mock 数据和 3 万条假报警，或加过滤隔离
- [x] mock_push.py 的光照单位需要修正为 0-100 以匹配阈值体系
- [x] 去掉 s 字段涉及 5 个连锁阻塞点（bridge 解析/后端 ingest/DB schema/模型公式/控制逻辑），必须全部适配
- [x] OLED 驱动文件已齐全，只需 IAR 加 `HAL_OLED` 宏 + 重编译烧写即可启用
- [x] OLED 显示内容（T/H/L 三行）满足需求，不需要修改
- [x] ZStack 完整协议栈已通过软链接接入项目：`firmware/ZStack` → `/Users/admin/Downloads/ZStack`

### 期望结果

- ED 板每 2 秒采集 DHT11 温湿度 + GL5516 光照，OLED 实时显示 T/H/L 三行数据
- 固件只发 `t:XX-h:XX-l:XXX` 三个真实测量值，不含虚假土壤字段
- bridge 解析 3 字段帧，标记 `bridge_mode:"hardware"`，转发到云端
- 后端收到 3 个实测值后，由 `compute_model_values()` 推导 soil/co2/ec/tds/fertility/infrared 共 6 个模型值，一并入库和广播
- 前端 Dashboard 分区展示：实测值标注"真实串口"，模型值标注"模型推算"，设备状态显示在线
- 每条数据来源透明可追溯，mock 数据与真实数据不再混淆

---

## 2. 数据异常流水灯报警 + 湿度不够自动开泵

### 存在的问题

#### 2.1 需求中的"湿度"指 soil_moisture（土壤湿度）

代码实现为 `soil_moisture < start_below(35%)` 连续 3 次触发开泵。
已确认符合需求意图——"湿度不够"指土壤湿度，不是空气湿度。

#### 2.2 自动灌溉不检查 is_test — mock 数据会触发真实水泵

`_apply_soil_moisture_pump_rule()` 只检查 `allow_control` 和 `mode=="auto"`，
**没有检查 `is_test`**。对比报警灯有三重保护（allow_control + is_test + alarm_source），
水泵控制少了 `is_test` 这一层。mock 模式下 soil 低于 35% 时继电器会真的吸合。

#### 2.3 报警灯闪烁时施肥/灭虫灯被占用（水泵不受影响）

`SampleApp_ApplyActuatorOutputs()` 的执行顺序是：先处理 pump（P0.6+P1.0），再判断 alarm。
所以 **水泵继电器在报警期间正常工作**。
但 alarm 的 `return` 提前退出会跳过 fert（P1.1）和 pest_light（P1.6）的正常控制，
报警期间这两路 LED 被报警流水灯占用，手动命令状态变量会更新但 GPIO 不生效，要等报警结束才恢复。

#### 2.4 LED 颜色——报警用绿灯不够醒目

需求中"报警"的直觉期望是红色，但 P1.1/P1.6 的 LED 物理颜色由板上焊接决定，
代码只能控制亮灭无法改颜色。需要实物确认 LED 颜色，如无法更换则记录为硬件限制。

#### 2.5 继电器动作噪声

继电器（SRA-05VDC-AL）吸合/释放时"咔嗒"声是正常物理现象。
但因为 2.2 的 bug（不检查 is_test），mock 数据可能导致继电器反复动作产生连续噪声。

#### 2.6 soil 变为模型推导值后自动灌溉参数需调整

模型推导值平滑无噪声，"连续 3 次 < 35%"这个条件几乎没有防抖效果——
一旦模型算出 <35% 就持续 <35%，3 次条件秒过。
需要增大 `consecutive_samples`（建议 5-8 次）来补偿模型平滑性。

#### 2.7 云端 mock 报警风暴

线上 mock_push.py 的 light 值 200-2000，阈值 max=90，每 2 秒产生一条 `light_high` 报警。
已累积 **30,220 条假报警**，几乎全是光照超阈值。
如果 bridge 以非 mock 模式连着，会持续向硬件发 `BLEALARM1`，报警灯永远在闪。

### 讨论确认

- [x] "湿度不够"指土壤湿度（soil_moisture），代码实现正确
- [x] 报警灯用 P1.1/P1.6 交替闪烁（需求"流水灯报警"），报警优先于施肥/灭虫灯状态，行为合理
- [x] 水泵继电器 P0.6 在报警期间正常工作（代码里 pump 控制在 alarm 判断之前），无需修复
- [x] 施肥/灭虫灯在报警期间被占用是合理的（报警优先），报警结束后自动恢复
- [x] 自动灌溉需加 `is_test` 检查 → 防止 mock 数据触发真实继电器
- [x] soil 改为模型推导后，`consecutive_samples` 需增大（5-8 次）补偿平滑性
- [x] LED 颜色需实物确认，可能是硬件限制无法软件改

### 期望结果

- 任一传感器参数越界时，后端发 `BLEALARM1`，ED 板 P1.1/P1.6 交替闪烁（300ms 间隔）指示报警
- 报警期间水泵继电器 P0.6 不受影响（已实现），施肥/灭虫灯被报警流水灯占用（报警优先）
- 土壤湿度（模型推导值）连续 5-8 次低于 start_below 阈值时，自动发 `BLEGLED1` 开泵
- 泵运行最长 20 秒自动关闭，30 秒冷却期内不再启动
- 土壤湿度恢复到 stop_at_or_above 阈值以上时自动关泵
- mock/test 数据不触发任何硬件控制动作（报警灯和水泵都不动）

---

## 3. 手动开关浇水/施肥/灭虫灯

### 存在的问题

#### 3.1 手动控制链路完整，端到端可用

三个设备的控制命令和 GPIO 映射均已实现：

| 设备 | 开命令 | 关命令 | GPIO |
|------|--------|--------|------|
| 水泵 pump | BLEGLED1 | BLEKLED1 | P0.6 继电器 + P1.0 LED |
| 施肥 fertilizer | BLEGLED2 | BLEKLED2 | P1.1 LED |
| 灭虫灯 pest_light | BLEGLED3 | BLEKLED3 | P1.6 LED |

前端按钮 → API → WebSocket → bridge → 串口 → 协调器 → ZigBee → ED 板 GPIO，全通。

#### 3.2 没有模式保护——auto 模式下手动操作和自动规则冲突

后端 `_handle_manual_control()` 不检查 `app_state.mode`。
auto 模式下手动关泵后，下一轮传感器数据到达时自动灌溉规则可能又把泵打开。
用户会困惑"明明关了怎么又开了"。

#### 3.3 没有硬件确认反馈（原方案）

当前链路是单向的：命令发出后前端乐观更新状态，不等硬件确认。
如果 bridge 断线、串口异常、ZigBee 丢包，前端显示的状态和硬件不一致。

#### 3.4 bridge.py 作为桥接层的体验问题

答辩演示时，队友需要在 Windows 上单独运行 `python3 bridge.py --port COM3 ...`。
需要装 Python、知道 COM 口名字、手动输命令——不够直观。

#### 3.5 报警期间施肥/灭虫灯手动控制延迟生效

alarm_state=1 时固件 `SampleApp_ApplyActuatorOutputs()` 跳过 fert 和 pest_light 的 GPIO 控制。
手动命令的状态变量会更新，但 LED 要等报警结束才实际切换。
水泵不受影响（pump 控制在 alarm 判断之前执行）。

### 讨论确认

- [x] 手动控制加模式保护：**不限制模式**，auto 和 manual 都可以手动操作，但手动操作后对该设备设一个 **60 秒抑制期**，期间自动规则不覆盖手动状态
- [x] ~~Web Serial API 替代 bridge.py~~ → **评审后降级**：Web Serial 有 5 个 BLOCKER（HTTPS 需域名但无域名、代码 0%、双重身份架构空白、控制回传未设计、soil 公式不存在），演示沿用 bridge.py，Web Serial 作为后续加分项
- [x] **演示方案确定为 bridge.py**：队友 Windows 上运行 `python3 bridge.py --port COM3 --server ws://云端/ws/bridge`，链路已全通
- [x] 硬件反馈：bridge 断线时后端返回错误阻断控制命令，前端提示"设备离线"即可
- [x] 报警期间施肥/灭虫灯延迟生效是已知行为，报警结束后自动恢复最新状态

### 期望结果

- 队友 Windows 插上协调器 USB，运行 bridge.py 连接云端 WebSocket
- 连接成功后，Dashboard 显示"在线"，传感器数据每 2 秒实时更新
- 三个设备的手动开关通过前端按钮 → API → bridge → 串口 → 硬件，bridge 在线时可用
- 手动操作后 60 秒内自动规则不覆盖该设备状态
- bridge 断线时手动控制按钮显示"设备离线"，阻断命令发送

---

## 4. 上位机查看全部传感器数据 + 阈值配置 + 异常显示 + 历史数据

### 存在的问题

#### 4.1 数据展示——需求要求的字段全部可见

Dashboard 分两区展示 9 个字段：

| 区域 | 字段 | 展示 | 趋势图 |
|------|------|------|--------|
| 板端实测 | temp, humi, light, soil | 有 | 有 |
| 模型推算 | co2, soil_ec, soil_tds, soil_fertility, infrared | 有 | 有 |

需求中提到的温湿度/CO2/土壤湿度/TDS EC/红外全部覆盖。

#### 4.2 阈值配置——soil_moisture 和 soil_fertility 可编辑

Settings.vue 有阈值配置页面，`PUT /api/thresholds` 保存到数据库。
soil_moisture 和 soil_fertility 标记为 `editable: true`，用户可修改 min/max。
CO2/EC/TDS/红外为只读阈值，不可编辑——符合需求（需求只要求前两个可配置）。

#### 4.3 阈值异常特别显示——三层实现

1. Dashboard 卡片变红（红色渐变背景 + 红色边框 CSS）
2. 侧边栏"最近告警"面板，显示参数名 + 越界方向 + 实际值
3. AlarmLog 完整报警历史，支持时间/来源/级别/关键字筛选

#### 4.4 历史数据——完整可用

History.vue 支持 1h/24h/7d/自定义时间范围，分页每页 10 条，CSV 导出含模型值。
图表展示所有字段趋势。

#### 4.5 模型值不存数据库，查询时重新计算

`SensorData` 表只存 temp/humi/light/soil 四个原始值。
co2/ec/tds/fertility/infrared 在 API 响应时由 `build_sensor_facts()` 临时计算。
大量历史查询时每条都跑一遍公式，可能影响性能。

#### 4.6 soil 的分区和数据源标签需更新

当前 soil 在 sensor_facts.py 标记为 `source: "simulated_firmware"`，归在"板端实测"区域。
按之前的决策（soil 改为云端推导），需要改为 `source: "computed_backend"`，
并在 Dashboard 上移到"模型推算"区域。

#### 4.7 历史数据被 mock 污染

同需求1——84,978 条 mock 数据混在历史里，bridge_mode 全是 "unknown"。
上线前需清理或加过滤。

### 讨论确认

- [x] 需求要求的所有传感器数据（温湿度/CO2/土壤湿度/TDS EC/红外）已全部在 Dashboard 可见
- [x] soil_moisture 和 soil_fertility 的阈值配置已实现，符合需求
- [x] CO2/EC/TDS/红外不需要加阈值报警，需求只要求前两个
- [x] 阈值异常的"特别显示"已有三层实现（卡片变红/告警面板/报警历史）
- [x] 历史数据查询功能完整（时间范围/分页/导出/图表）
- [x] soil 的分区标签需从"板端实测"移到"模型推算"
- [x] 模型值临时计算的方式暂时可接受，课程设计数据量不大

### 期望结果

- Dashboard 分区展示：3 个实测值（temp/humi/light）标"真实串口"，6 个模型值（soil/co2/ec/tds/fertility/infrared）标"模型推算"
- Settings 页面可编辑 soil_moisture 和 soil_fertility 的 min/max 阈值，保存后立即生效
- 任何有阈值的参数越界时，对应 Dashboard 卡片变红 + 侧边栏告警提示 + AlarmLog 记录
- History 页面可查 1h/24h/7d 及自定义时间范围的历史数据，含全部 9 个字段，支持 CSV 导出
- 历史数据干净，不含 mock 污染数据

---

## 5. Tracer Bullet 评审发现（跨需求遗漏）

两个独立视角（硬件向上追踪 + 用户向下追踪）的评审结果，以下为方案中未覆盖的关键风险。

### 5.1 BLOCKER 级

#### 土壤推导公式不存在

`compute_model_values()` 里 soil 是输入不是输出。`soil = f(temp, humi, light)` 公式还没设计。
没有这个公式，去掉固件 `s` 字段后 soil 值消失，EC/TDS/fertility 全部失真，自动灌溉无法工作。
→ **这是最优先要补的东西，所有需求都依赖它。**

#### 线上 SQLite 的 NOT NULL 约束无法 ALTER

SQLite 不支持 `ALTER COLUMN`。线上 `agriculture.db` 的 `soil` 列 NOT NULL 是建表时焊死的。
→ **不走 nullable 路线**：ingest 时先算出 soil 模型值再存（永远非空），绕开约束问题。

### 5.2 HIGH 级

#### 60 秒手动抑制期被现有代码架空

`_cooldown_elapsed()` 只看 `source=="auto"` 的 ControlLog，不看手动操作时间戳。
手动关泵后 2 秒自动规则就会重新开泵，根本不是 60 秒抑制。
→ 后端需在 app_state 里给每个 board_id+device 记 `manual_until` 时间戳。

#### mock 数据污染 consecutive samples 判定

`_has_consecutive_low_soil_samples()` 查最近 N 条 SensorData，**不过滤 is_test**。
真实设备刚连上时，窗口里混着 mock 低值记录，防抖窗口被提前攒满。
→ 查询加 `SensorData.is_test.is_(False)` 过滤 + 清理脚本删除旧 mock 数据。

#### soil 和 ec/tds/fertility 完全共线

soil = f(temp, humi, light) 后，soil_ec = g(soil, temp, humi)，soil_fertility = h(soil, soil_ec)。
四个指标全由 temp/humi/light 确定性派生，趋势图会呈现肉眼可见的同步变化。
→ 考虑给 soil 公式加少量随机噪声/滞后项，避免被问"为什么曲线形状一样"。

#### 自动灌溉能否在演示中可靠触发

soil 改为模型推导值后，学生需要通过改变环境（捂传感器等）间接影响 soil 值。
如果公式设计不当（比如正常教室环境下 soil 永远 >35%），自动灌溉在演示中无法触发。
→ 公式设计时要确保演示可控性，或保留测试注入接口 `/api/test/sensor-sample` 作为兜底。

### 5.3 MEDIUM 级

#### 报警期间 UI 和硬件状态不一致

用户点"施肥灯开"时如果报警正在闪烁，前端显示"已开启"但物理 LED 仍在闪报警模式。
→ 前端可加提示"报警期间手动操作将在报警解除后生效"。

#### 控制/阈值 API 无鉴权

`/api/control`、`/api/mode`、`PUT /api/thresholds`、`/ws/bridge` 全部无需登录。
→ 课程设计风险可控，但至少给控制类接口加登录态校验。

#### 控制状态纯内存态，重启即丢

`_pump_timeout_tasks`、`_alarm_light_state`、连续采样计数都是内存变量。
后端重启后状态清零，排练和正式演示可能表现不一致。

### 5.4 策略调整

- [x] **演示沿用 bridge.py**，Web Serial 降级为后续工作（BLOCKER 过多）
- [x] **SQLite 不走 nullable**：ingest 时先算 soil 模型值再存，绕开 ALTER 限制
- [x] soil 推导公式是最高优先级待设计项
- [x] 手动抑制期需在后端用 `manual_until` 时间戳实现，不能放前端
- [x] mock 清理需要脚本 + consecutive samples 查询加 is_test 过滤
