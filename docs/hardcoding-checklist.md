# 硬编码对齐核对表（创思通信集成板）

> 背景：实物从"双板 CC2530（协调器+终端）"变成一块创思通信单板集成板（板载 CC2530 + DHT11 + 光敏 + 继电器 + LED D1/D2/D3 + OLED + ESP8266 + 蓝牙）。
> 本表用于在拿到板子引脚资料后，逐条核对软件里写死的硬件假设，确定改哪里。

## 核心原则

硬编码分两类，只有 B 类需要对齐实物：

- **A 类 = 软件内部自洽的协议**（字段名 t/h/l/s、命令字 BLEGLED*、ZigBee 簇 ID、波特率 115200/8N1）。只要烧我们自己的 `firmware/`，固件↔bridge↔后端↔前端四方天生对齐，**与实物板无关，不用改**。
- **B 类 = 绑死在物理板上的**（引脚映射、器件是否存在）。**这才是要对齐的部分。**

对齐动作的铁律：**只改最底层 `firmware/end_device/SampleApp.h` 的引脚宏去适配这块板，上层 bridge/后端/前端一行都不动。**

---

## A 类：软件内部协议（无需对齐，仅备查）

| 项 | 值 | 位置 |
|---|---|---|
| 上行字段 | `t / h / l / s` | firmware end_device `SampleApp.c:482`、bridge.py:28-33、backend models/schemas |
| 下行命令字 | `BLEGLED1/2/3`、`BLEKLED1/2/3` | backend/config.py:20-24、firmware `SampleApp.c:597-630` |
| ZigBee 簇 ID | 数据=1、控制=2 | firmware `SampleApp.h:39-40` |
| 串口参数 | 115200 / 8N1 | coordinator `SampleApp.h:46-47`、serial_bridge/config.py:7-9 |
| 采集周期 | 2000 ms | firmware `SampleApp.h:46` |

---

## B 类：必须对齐物理板（核对重点）

### B1. 引脚映射 —— 原理图实物值

| 器件 | 软件假设引脚 | 定义位置 | 实物板实际引脚 | 对齐动作 |
|---|---|---|---|---|
| DHT11 数据线 | **P2.0** | `SampleApp.h:54-56` | **P2.0**（原理图网络 `P20`） | 已一致 |
| 执行器1 pump | **P1.0** | `SampleApp.h:69` | **继电器=P0.6**（网络 `P06`），P1.0 是 LED 指示 | 已改为 P0.6 + P1.0 指示 |
| 执行器2 fertilizer | **P1.1** | `SampleApp.h:70` | **LED D2=P1.1**（网络 `P11`，低电平亮） | 已改极性 |
| 执行器3 skylight | **P1.6** | `SampleApp.h:71-73` | **LED D11=P1.6**（网络 `P16`，低电平亮） | 已改极性 |
| 三路 LED | P1.0/P1.1/P1.6 | `SampleApp.h` / `SampleApp.c` | D10=P1.0、D2=P1.1、D11=P1.6，均为低电平亮 | 已配置输出并按低电平点亮 |
| OLED SPI (SCK/SDA/RES/DC/CS) | 见 `HalOled.h` | HalOled.h（未核） | SCK=P1.2、SDA/MOSI=P1.3、RES=P1.7、DC=P0.0、CS=GND | 需要匹配 SPI OLED 驱动，或继续禁用 |
| 光敏电阻 ADC | **无**（固件是模拟值） | `SampleApp.c:253-265` | **P0.7**（网络 `P07`） | 见 B3 |
| UART TX/RX | P0.3 / P0.2 | coordinator | USB-CH340：CC2530 RX0=P0.2、TX0=P0.3；WiFi/蓝牙走 UART1 RX1=P0.5、TX1=P0.4 并由拨码开关选择 | 单板直连 PC 走 UART0 |

### B2. 器件存在性 / 数量

| 我们假设 | 实物（照片初判） | 决策 |
|---|---|---|
| 温度 t（DHT11） | ✓ 有 DHT11 | 真实采集 |
| 湿度 h（DHT11） | ✓ DHT11 自带 | 真实采集 |
| 光照 l | ✓ 有光敏电阻（但固件当前是模拟，见 B3） | 待定：接 ADC 还是继续模拟 |
| **土壤 s** | **照片未见土壤传感器** | **降级**：固件继续填模拟值，或前端隐藏土壤卡片 |
| 3 路执行器 | 1 路继电器 + 3 路 LED | 现固件映射为：pump=继电器 P0.6 + LED P1.0 指示，fertilizer=LED P1.1，skylight=LED P1.6 |

### B3. 重要：光照/土壤当前是"假"数据

固件里 `SampleApp_SimulateLight()` / `SampleApp_SimulateSoil()`（`SampleApp.c:253-283`）是**软件模拟**，不是读真实传感器。原理图确认板上光敏 GL5516 的分压输出接 CC2530 **P0.7**，但固件当前还没加 ADC 读取。

- **光照 l**：想要真实值，需在固件加 CC2530 ADC 采集 P0.7。否则维持模拟。
- **土壤 s**：板上无传感器，维持模拟。

---

## C. 路线决策：已定为【双板 ZigBee】

用第二块同款集成板组成双板：

- **板1（这块，已改引脚）** 烧 `end_device`：采集 DHT11+ 控制继电器/LED，ZigBee 点播给协调器 `0x0000`（簇1），收命令（簇2）。
- **板2（第二块）** 烧 `coordinator`：`UART` 口（CH340=P0.2/P0.3）接 PC，收 ZigBee 簇1 → UART 转 PC 加 `\r\n`；收 UART 命令 → ZigBee 广播 `0xFFFF`（簇2）。

代码层面已 100% 就绪，端点 20 / Profile `0x0F08` / 簇 1·2 / 地址全部两板对齐。**coordinator 只用 UART0，不碰继电器/LED/DHT11，第二块板不用改任何引脚。**

剩余的是 Z-Stack 工程层面（不在 SampleApp 代码里，yh 在 IAR 操作）：

- [ ] 两个工程编译配置：板1 选 `EndDeviceEB-Pro`，板2 选 `CoordinatorEB-Pro`
- [ ] **组网参数一致**：两工程 `f8wConfig.cfg` 的 `ZDAPP_CONFIG_PAN_ID` 与 `DEFAULT_CHANLIST`（信道）必须相同；多组同场要错开 PAN ID 避免串数据
- [ ] 供电/接线：板1（终端）DHT11 已板载，USB 供电即可，UART 口不接 PC；板2（协调器）UART 口接 PC 跑 bridge
- [ ] OLED 可选：当前 `HAL_OLED` 未定义=禁用；要点亮需配 SPI 驱动（SCK=P1.2/MOSI=P1.3/RES=P1.7/DC=P0.0），不阻塞验收

---

## 执行清单

1. [x] 把 B1 实物引脚填齐（原理图已确认）
2. [x] 改 `firmware/end_device/SampleApp.h` 引脚宏（继电器 P0.6 + LED 极性）
3. [x] 定 B2 土壤/光照降级策略（均维持模拟，光敏 P0.7 待后续加 ADC）
4. [x] 定 C 路线（双板 ZigBee）
5. [ ] 板1·板2 编译烧录 → 协调器 UART 口连 PC → bridge 直读 → 验证上下行
6. [ ] 确认 `f8wConfig.cfg` 两板 PAN ID / 信道一致
