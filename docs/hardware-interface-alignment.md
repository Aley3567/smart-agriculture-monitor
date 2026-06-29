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

**接真机核心判断：项目固件已是可用的目标固件。bridge.py 解析器与固件输出格式完全匹配。需改动的地方集中在"光照/土壤"两个模拟传感器和一些边界细节。**

---

## 二、上行数据链路（传感器 → PC → 后端）

### 2.1 数据格式

**完整数据流：**
```
DHT11(P2.0) → 终端节点 SampleApp_SendPeriodicMessage()
  → 拼 "t:25-h:60-l:800-s:45"
  → AF_DataRequest 点播到协调器(0x0000)
  → 协调器 SampleApp_MessageMSGCB() 原样转发 + 追加 "\r\n"
  → UART0 输出 "t:25-h:60-l:800-s:45\r\n"
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
| `l` 光照 | 无 | `SampleApp_SimulateLight()` | 固件内软件模拟 | **模拟值** |
| `s` 土壤 | 无 | `SampleApp_SimulateSoil()` | 固件内软件模拟 | **模拟值** |

**接真机时的选择：**
- 方案 A（最小改动）：保持光照/土壤为固件模拟值，演示说明即可
- 方案 B（加传感器）：接 BH1750 光照传感器(I2C) + 土壤湿度传感器(ADC)，修改固件采集逻辑
- 方案 C（去掉 l/s）：固件只发 `t:25-h:60`，同时改 bridge.py 的 `len(data)==4` 为 `len(data)>=2`

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
| `BLEGLED1` | pump on | P1_0=1 | P1_0=1 | P1.0 | 开启水泵/LED1 |
| `BLEKLED1` | pump off | P1_0=0 | P1_0=0 | P1.0 | 关闭水泵/LED1 |
| `BLEGLED2` | fertilizer on | P1_1=1 | P1_1=1 | P1.1 | 开启施肥/LED2 |
| `BLEKLED2` | fertilizer off | P1_1=0 | P1_1=0 | P1.1 | 关闭施肥/LED2 |
| `BLEGLED3` | skylight on | P1_6=1 | P1_6=1 | P1.6 | 开启天窗/LED3 |
| `BLEKLED3` | skylight off | P1_6=0 | P1_6=0 | P1.6 | 关闭天窗/LED3 |

**对接状态：三方完全一致。命令字、GPIO、电平含义全部匹配。**

### 3.2 命令传输路径

```
FastAPI control.py → {"type":"control","command":"BLEGLED1"}
  → WebSocket → bridge.py ws_to_serial()
  → 串口写入 "BLEGLED1\r\n"
  → 协调器 SampleApp_UartCB() 读取串口数据
  → SampleApp_SendToEndDevice() 广播(0xFFFF) via SAMPLEAPP_CTRL_CLUSTERID
  → 终端节点 SampleApp_MessageMSGCB() 收到
  → strstr 匹配 "BLEGLED1" → P1_0 = 1
```

**对接状态：链路完整。**

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

综合实验 5/6 的 HAL 层定义和实验 9 的直接 GPIO 操作：

| 开发板丝印 | GPIO | HAL LED ID | 实验 5/6 用途 | 实验 9 用途 | 项目用途 |
|-----------|------|------------|--------------|-------------|---------|
| D1 (Green) | P1.0 | HAL_LED_1 / HAL_LED_4 | 流水灯步骤3 | LED1 控制 | **水泵** |
| D2 (Red) | P1.1 | HAL_LED_2 | 组播 LED 控制 | LED2 控制 | **施肥** |
| D3 (Yellow) | P0.4 | HAL_LED_3 | 流水灯步骤2/4 | 不使用 | 不使用 |
| - | P1.6 | 无 HAL 映射 | 不使用 | LED3 控制 | **天窗** |

**关键发现：P1.6 (LED3/天窗) 在 HAL_LED 中没有映射！** 实验 9 通过 `P1DIR |= 0x43` 手动将 P1.0/P1.1/P1.6 设为输出，绕过了 HAL_LED API。项目固件继承了这种直接 GPIO 操作方式。

这意味着：
- 如果开发板上 P1.6 确实连了 LED/继电器，没问题
- 如果开发板只有 P1.0/P1.1/P0.4 三个板载 LED，则"天窗"需要外接继电器到 P1.6

---

## 六、接真机 Checklist

### 必须做（否则不工作）

- [ ] **烧写项目固件**：使用 `firmware/coordinator/` 和 `firmware/end_device/` 的代码，不要用实验原版代码
- [ ] **DHT11 接线**：数据线接 P2.0，加 4.7K 上拉电阻到 VCC
- [ ] **串口接线**：协调器 UART0 (P0.2 RX / P0.3 TX) 接 USB 转串口模块，注意 TX/RX 交叉
- [ ] **GPIO 方向寄存器**：确认终端节点固件中 P1.0/P1.1/P1.6 已设为输出 (`P1DIR |= 0x43`)
- [ ] **先烧协调器再烧终端**：协调器先上电建网
- [ ] **bridge.py 串口设备名**：macOS 上修改 `--port` 参数为实际 USB 串口设备名（如 `/dev/tty.usbserial-xxxx`）

### 建议做（提升可靠性）

- [ ] **串口测试**：先用串口助手手动发 `BLEGLED1`，确认终端节点 P1.0 亮灯
- [ ] **数据验证**：串口助手查看协调器输出，确认格式为 `t:xx-h:xx-l:xxx-s:xx\r\n`
- [ ] **P1.6 硬件确认**：确认开发板 P1.6 引脚是否有外接设备，还是需要飞线
- [ ] **HAL_UART 宏**：协调器工程预编译宏必须包含 `HAL_UART=TRUE` 和 `HAL_UART_DMA=1`
- [ ] **OLED 驱动**：终端节点需要 `HalOled.h` 驱动文件，如果没有可注释掉 OLED 相关代码

### 可选做（演示加分）

- [ ] **继电器接入**：P1.0/P1.1/P1.6 接继电器模块，驱动水泵/电磁阀/电机（GPIO 输出高电平即触发）
- [ ] **真实光照传感器**：加 BH1750 (I2C)，替换 `SampleApp_SimulateLight()`
- [ ] **真实土壤传感器**：加电容式土壤湿度传感器 (ADC)，替换 `SampleApp_SimulateSoil()`

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
