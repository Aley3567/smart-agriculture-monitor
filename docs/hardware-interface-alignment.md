# 硬件接口对接清单

> 对照实验 5/6/7/8/9 真实源码 vs 项目现有契约，逐条标注差异和接真机时需改的点。
> 生成日期: 2026-06-29

---

## 一、全局结论

项目固件（`firmware/`）是基于实验 7 + 实验 9 改造的自研融合版，不是直接用任何实验原版代码。继承关系：

| 来源 | 继承内容 | 差异 |
|------|---------|------|
| 实验 7 | DHT11 驱动(P2.0)、ZigBee 点播、OSAL 事件框架 | 波特率从 9600 改为 115200；数据格式从 `"26  60"` 改为 `"t:25-h:60-l:800-s:45"` |
| 实验 9 | BLEGLED/BLEKLED 6 条命令字、strstr 解析、P1.0/P1.1/P1.6 GPIO 映射 | 从蓝牙(UART1)改为 ZigBee 无线接收；去掉蓝牙 AT 配置 |
| 实验 5/6 | LED 硬件接口知识(HAL_LED API / GPIO)、组播/点播概念 | 未直接复用代码，但 GPIO 映射一致 |
| 实验 8 | 串口透传概念 | 未使用 SerialApp 的 ACK/重发机制，改为简单 UART 回调转发 |

**接真机核心判断：项目固件已是可用的目标固件。bridge.py 解析器与固件输出格式完全匹配。验收按 C/ED 双板架构：C 板接串口和 bridge；ED 板接 DHT11、GL5516/P0.7、OLED、继电器/LED。课程设计按单板模拟收口，施肥、灭虫、土壤、CO2、EC/TDS、肥力、红外不再要求额外真实负载或新增传感器。需改动/验证的地方集中在 OLED 编译启用、流水灯报警烧录验证和现场串口链路。**

---

## 二、上行数据链路（传感器 → PC → 后端）

### 2.1 数据格式

**完整数据流（C/ED 双板链路）：**
```
DHT11(P2.0) + GL5516(P0.7, P1 待接入) → ED SampleApp_SendPeriodicMessage()
  → 拼 "t:25-h:60-l:800-s:45"
  → AF_DataRequest 点播到 C 板协调器(0x0000)
  → C 板 SampleApp_MessageMSGCB() 原样转发 + 追加 "\r\n"
  → C 板 UART0 输出 "t:25-h:60-l:800-s:45\r\n"
  → PC bridge.py parse_serial_line() 按 "-" 拆分, ":" 拆分
  → {"temp":25.0, "humi":60.0, "light":800.0, "soil":45.0}
  → WebSocket → FastAPI 入库
```

| 环节 | 格式 | 状态 |
|------|------|------|
| 终端节点 ZigBee payload | `t:25-h:60-l:800-s:45` (变长 ~15-20 字节) | 已实现 |
| 协调器 UART 输出 | `t:25-h:60-l:800-s:45\r\n` | 已实现 |
| bridge.py 解析 | FIELD_MAP {t→temp, h→humi, l→light, s→soil}, 要求 4 字段 | 已实现 |

**对接状态：完全匹配，无需改动。**

### 2.2 四个传感器的真实性

| 字段 | 传感器 | 接口 | 来源 | 真实性 |
|------|--------|------|------|--------|
| `t` 温度 | DHT11 | P2.0 单总线 | 实验 7 DHT11 驱动 | **真实硬件** |
| `h` 湿度 | DHT11 | P2.0 单总线 | 同上 | **真实硬件** |
| `l` 光照 | GL5516 | P0.7 ADC | `SampleApp_ReadLight()` | **待现场 smoke 的相对光照值** |
| `s` 土壤 | 无 | `SampleApp_SimulateSoil()` | 固件内软件模拟 | **模拟值** |

**接真机时的验收口径：**
- 光照：固件已直接走板载 GL5516/P0.7 ADC，字段是相对光照值，不再宣称 lux；未完成遮光/照光 smoke 前保持待验收。
- 土壤湿度：板上无传感器时仍为模拟值，不能作为真实低湿证据。
- CO2/红外：按课程模拟/模型字段接入，不能标成硬件实测。
- EC/TDS/肥力：按模型公式接入，保留 `source` 和 `formula_version`。

### 2.3 波特率

| 层 | 值 | 来源 |
|----|-----|------|
| 协调器固件 | 115200 | `coordinator/SampleApp.h:47` `HAL_UART_BR_115200` |
| bridge config.py | 115200 | `DEFAULT_BAUD = 115200` |
| 实验 7 原版 | **9600** | `MT_UART.h:75` `HAL_UART_BR_9600` |
| 实验 8 原版 | **9600** | `SerialApp.c:37` `HAL_UART_BR_9600` |
| 实验 9 原版 | 115200 | 裸机直接配寄存器 |

**对接状态：匹配。但千万不要误烧实验 7/8 的原版固件到协调器，否则波特率 9600 会导致 bridge 乱码。**

### 2.4 串口物理参数

| 参数 | 固件 | bridge | 匹配 |
|------|-----|--------|------|
| 端口 | UART0 (P0.2 RX, P0.3 TX) | 自动检测 USB 串口 | Y |
| 数据位 | 8 | 8 | Y |
| 停止位 | 1 | 1 | Y |
| 校验 | N | N | Y |
| 流控 | FALSE | 无 | Y |

---

## 三、下行控制链路（PC → 执行器）

### 3.1 命令字

| 命令 | backend config.py | 固件终端节点 | 实验 9 原版 | GPIO | 语义 |
|------|------------------|-------------|-------------|------|------|
| `BLEGLED1` | pump on | P0_6=1, P1_0=0 | P1_0=1 | P0.6 + P1.0 | 继电器吸合，LED1 指示亮 |
| `BLEKLED1` | pump off | P0_6=0, P1_0=1 | P1_0=0 | P0.6 + P1.0 | 继电器断开，LED1 指示灭 |
| `BLEGLED2` | fertilizer on | P1_1=0 | P1_1=1 | P1.1 | LED2 指示亮 |
| `BLEKLED2` | fertilizer off | P1_1=1 | P1_1=0 | P1.1 | LED2 指示灭 |
| `BLEGLED3` | pest_light on | P1_6=0 | P1_6=1 | P1.6 | 灭虫灯指示亮 |
| `BLEKLED3` | pest_light off | P1_6=1 | P1_6=0 | P1.6 | 灭虫灯指示灭 |

**对接状态：命令字和上层语义一致；GPIO/电平已按创思通信集成板改为继电器高电平吸合、LED 低电平点亮。**

### 3.2 命令传输路径

```
FastAPI control.py → {"type":"control","command":"BLEGLED1"}
  → WebSocket → bridge.py ws_to_serial()
  → C 板串口写入 "BLEGLED1\r\n"
  → C 板 SampleApp_UartCB() 读取串口数据
  → C 板 SampleApp_SendToEndDevice() 广播(0xFFFF) via SAMPLEAPP_CTRL_CLUSTERID
  → ED SampleApp_MessageMSGCB() 收到
  → strstr 匹配 "BLEGLED1" → P0_6 = 1, P1_0 = 0
```

**对接状态：链路完整。**

自动浇水验收边界：

- 后端规则触发必须能查到 `ControlLog`。
- bridge 日志必须出现对应 `BLEGLED1/BLEKLED1` 命令。
- ED 板必须有水泵/继电器动作证据。
- 临时调阈值 smoke 只证明控制链路，不证明真实低湿传感器已完成。

流水灯报警固件口径：

- 后端判断异常后下发 `BLEALARM1/BLEALARM0`。
- ED 已有本地流水灯表现代码。
- 流水灯实现不能覆盖或误改 `pump` 继电器状态，不能把施肥/灭虫指示状态当作报警状态。

### 3.3 命令解析机制

| 属性 | 项目固件 | 实验 9 | 说明 |
|------|---------|--------|------|
| 解析函数 | `SampleApp_ProcessCtrlCmd()` | `Wifi_Ctrl_ZGBLED()` | 函数名不同，逻辑一致 |
| 匹配方式 | `strstr()` 子字符串匹配 | `strstr()` 子字符串匹配 | 完全一致 |
| 互斥性 | 每对 LED 用 if-else | 所有 6 条独立 if | 项目固件更严谨 |
| 命令来源 | ZigBee 无线接收 | 蓝牙 UART1 接收 | 传输层不同，解析层一致 |

---

## 四、ZigBee 无线通信参数

### 4.1 项目固件 vs 实验代码

| 参数 | 项目固件 | 实验 7 | 实验 6 |
|------|---------|--------|--------|
| 上行通信模式 | 点播到 0x0000 | 点播到 0x0000 | 点播到 0x0000 |
| 上行 Cluster ID | SAMPLEAPP_PERIODIC_CLUSTERID | SAMPLEAPP_P2P_CLUSTERID (4) | SAMPLEAPP_P2P_CLUSTERID (4) |
| 下行通信模式 | 广播 0xFFFF | N/A | N/A |
| 下行 Cluster ID | SAMPLEAPP_CTRL_CLUSTERID | N/A | N/A |
| Endpoint | SAMPLEAPP_ENDPOINT | 20 | 20 |
| Profile ID | 项目自定义 | 0x0F08 | 0x0F08 |

### 4.2 发送周期

| 项目 | 值 |
|------|-----|
| 实验 7 | 3000ms + 随机 0-255ms 抖动 |
| 项目固件 | 需确认（查 SampleApp.h 中 TIMEOUT 定义） |

---

## 五、LED/GPIO 硬件映射总表

按创思通信集成板原理图：

| 原理图器件 | GPIO | 电气极性 | 项目用途 |
|-----------|------|------------|---------|
| 继电器 SRA-05VDC-AL | P0.6 | 高电平吸合 | **水泵** |
| LED D10 | P1.0 | 低电平亮 | **水泵指示** |
| LED D2 | P1.1 | 低电平亮 | **施肥指示** |
| LED D11 | P1.6 | 低电平亮 | **灭虫灯指示** |

**关键发现：P1.0/P1.1/P1.6 三路 LED 的物理连接是上拉到 3.3V 后由 GPIO 下拉点亮，所以固件必须用低电平表示 LED 开。** 继电器是 P0.6 经 S8050 三极管驱动，高电平吸合。

这意味着：
- `BLEGLED1` 不能再只写 P1.0；它必须写 P0.6，并可同步 P1.0 做指示灯
- `BLEGLED2/3` 对 LED 的开/关电平和实验 9 原版相反

---

## 六、接真机 Checklist

### 必须做（否则不工作）

- [ ] **烧写项目固件**：使用 `firmware/coordinator/` 和 `firmware/end_device/` 的代码，不要用实验原版代码
- [ ] **DHT11 接线**：数据线接 P2.0，加 4.7K 上拉电阻到 VCC
- [ ] **串口接线**：C 板 UART0 (P0.2 RX / P0.3 TX) 接 USB 转串口模块，注意 TX/RX 交叉
- [ ] **GPIO 方向寄存器**：确认终端节点固件中 P0.6 已设为输出 (`P0DIR |= 0x40`)，P1.0/P1.1/P1.6 已设为输出 (`P1DIR |= 0x43`)
- [ ] **先烧协调器再烧终端**：协调器先上电建网
- [ ] **bridge.py 串口设备名**：macOS 上修改 `--port` 参数为实际 USB 串口设备名（如 `/dev/tty.usbserial-xxxx`）

### 建议做（提升可靠性）

- [ ] **串口测试**：先用串口助手手动发 `BLEGLED1/2/3` 和 `BLEKLED1/2/3`，确认三路响应；施肥/灭虫按课程模拟指示验收
- [ ] **数据验证**：串口助手查看 C 板输出，确认格式为 `t:xx-h:xx-l:xxx-s:xx\r\n`
- [ ] **P1.6 硬件确认**：确认开发板 P1.6 引脚是否有外接设备，还是需要飞线
- [ ] **HAL_UART 宏**：协调器工程预编译宏必须包含 `HAL_UART=TRUE` 和 `HAL_UART_DMA=1`
- [ ] **OLED 驱动**：ED 节点需要 `HalOled.h` 驱动文件；P1 验收必须只显示温度、空气湿度、光照相对值

### 模拟/模型字段

- [ ] **施肥/灭虫模拟执行器**：P1.1/P1.6 按课程设计作为模拟指示验收
- [ ] **CO2/红外模型字段**：按 `simulated_backend` 或测试事件接入，不标硬件实测
- [ ] **土壤湿度模拟值**：继续使用 `SampleApp_SimulateSoil()` 支撑课程演示和自动浇水触发
- [ ] **EC/TDS/肥力**：按模型公式接入，保留 `source` 和 `formula_version`

---

## 七、实验代码关键路径索引

后续需要查阅细节时的快速入口：

| 实验 | 核心文件 | 关注点 |
|------|---------|--------|
| 实验 7 DHT11 | `实验3-8代码/实验7/.../SampleApp.c` | 温湿度采集+ZigBee发送 |
| 实验 7 驱动 | `实验3-8代码/实验7/.../DHT11.c` / `.h` | P2.0 单总线时序、全局变量 |
| 实验 8 透传 | `实验3-8代码/实验8/.../SerialApp.c` | 串口回调、ACK/重发、9600波特率 |
| 实验 9 控制 | `思考题源码打包/实验九_蓝牙温湿度控LED/main.c` | BLEGLED命令解析、DHT11格式、UART配置 |
| 实验 5 组播 | `实验3-8代码/实验5/.../SampleApp.c` | aps_AddGroup/RemoveGroup、LED toggle |
| 实验 6 点播 | `思考题源码打包/实验六_点播5秒流水灯/SampleApp.c` | 点播0x0000、流水灯、HalLedSet API |
| HAL LED 映射 | `实验3-8代码/实验5/.../hal_board_cfg.h:115-132` | P1.0=LED1, P1.1=LED2, P0.4=LED3 |
