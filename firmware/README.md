# 智慧农业监测系统 - CC2530 固件

## 概述

本目录包含智慧农业监测系统的 CC2530 单片机固件核心应用层代码，基于 TI Z-Stack 2.5.1a 协议栈的 SampleApp 例程修改。

系统包含两块 CC2530 开发板：
- **ED 板 / 终端节点 (End Device)**: 采集 DHT11 温湿度，读取 GL5516/P0.7 ADC 相对光照值，驱动 OLED、继电器和 LED 指示；通过 ZigBee 发送到 C 板；接收控制命令驱动执行器
- **C 板 / 协调器 (Coordinator)**: 接收 ED 数据并通过 UART0 转发到 PC/`serial_bridge`；接收 PC 串口命令转发到 ED

## 目录结构

```
firmware/
├── README.md
├── end_device/
│   ├── SampleApp.c          # 终端节点主应用
│   └── SampleApp.h          # 终端节点头文件
└── coordinator/
    ├── SampleApp.c          # 协调器主应用
    └── SampleApp.h          # 协调器头文件
```

## 集成到 Z-Stack 工程

### 前置条件

均可在课程资料 `实验课/5.开发工具/` 里找到安装包：

- **IAR Embedded Workbench for 8051**（资料里是 `1.IAR EW8051 V8.1`，必须是 8051 版，不是 ARM 版）
- **TI Z-Stack 2.3.0-1.4.0** 协议栈（资料 `ZStack-CC2530-2.3.0-1.4.0协议栈安装文件.rar`，解压后跑 exe，默认装到 `C:\Texas Instruments\`）
- **SmartRF Flash Programmer** + CC Debugger 烧写器（资料 `SmartRF Flash Programmer 1.9.0.rar`）
- 两块 CC2530 集成板

> 固件源码注释写的是 Z-Stack 2.5.1a，但 SampleApp 是经典例程，2.3.0-1.4.0 框架一致、可正常编译。

### 步骤 1: 打开 Z-Stack 工程

装好协议栈后，在**安装目录**下找到标准 SampleApp 工程：

```
C:\Texas Instruments\ZStack-CC2530-2.3.0-1.4.0\Projects\zstack\Samples\SampleApp\CC2530DB\SampleApp.eww
```

双击 `SampleApp.eww` 打开（`.eww` = IAR 工作区文件，是双击打开的顶层文件；同目录的 `.ewp` 工程文件、`.ewd` 调试配置会自动跟随，不用单独打开）。打开后左侧 Workspace 栏出现工程树，顶部下拉框可选编译配置。

> ⚠️ **别用课程资料里现成的那个 `SampleApp.eww`**：`14.CC2531...抓包资料/.../Z-Stack透传/Projects/zstack/SE/SampleApp/` 那个是 **Smart Energy 版**，Source 目录里是 ESP/IPD/SimpleMeter 等，**没有我们要替换的 `SampleApp.c`**，会无从下手。必须用协议栈安装后的 **`Samples/SampleApp`** 标准工程。

> ⚠️ **路径坑**：IAR EW8051 对中文、空格路径敏感，容易莫名编译报错。若工程放在中文路径下编不过，先把整个工程目录复制到纯英文短路径（如 `C:\zstack\`）再打开。

### 步骤 2: 替换源文件

**终端节点：**
1. 将 `end_device/SampleApp.c` 和 `end_device/SampleApp.h` 复制到 Z-Stack 工程的 `Source` 目录
2. 替换原有的 `SampleApp.c` 和 `SampleApp.h`

**协调器：**
1. 将 `coordinator/SampleApp.c` 和 `coordinator/SampleApp.h` 复制到另一份 Z-Stack 工程的 `Source` 目录
2. 替换原有的 `SampleApp.c` 和 `SampleApp.h`

> 建议将 Z-Stack 工程目录复制两份，分别用于终端节点和协调器。

### 步骤 3: 添加驱动文件

终端节点工程需要额外添加以下驱动文件（需自行准备或从开发板配套资料获取）：

| 驱动 | 头文件 | 说明 |
|------|--------|------|
| OLED 显示驱动 | `HalOled.h` | 提供 `HalOledInit()`, `HalOledShowStr()`, `HalOledClear()` |

将驱动源文件（`.c` 和 `.h`）添加到 IAR 工程的 `HAL` 或 `Source` 分组中。

### 步骤 4: 选择编译配置

在 IAR 工程中选择正确的编译配置：

| 开发板 | 编译配置 |
|--------|----------|
| 协调器 | `CoordinatorEB` |
| 终端节点 | `EndDeviceEB` |

选择方法：IAR 工具栏下拉框，或菜单 `Project` → `Edit Configurations`。

> 上表是普通 CC2530 的 `CoordinatorEB / EndDeviceEB`。若射频模块带 **CC2591 功放**，改选对应的 `-Pro`（`CoordinatorEB-Pro / EndDeviceEB-Pro`）。**不确定就先用不带 `-Pro` 的**，能组网即可；下拉框实际有哪些以打开的工程为准。

### 步骤 5: 编译设置

确认工程设置中以下预编译宏已定义：

**协调器工程：**
```
ZDO_COORDINATOR
RTR_NWK
HAL_UART=TRUE
HAL_UART_DMA=1
```

**终端节点工程：**
```
(默认 EndDevice 配置即可，无需额外宏)
```

### 步骤 6: 编译烧写

1. 在 IAR 中按 `F7` 编译工程，确认无错误
2. 用 USB 线连接 CC Debugger 到开发板的调试接口
3. 确认 CC Debugger 指示灯为绿色（表示已识别目标芯片）
4. 按 `Ctrl+D` 进入调试模式（自动烧写）
5. 烧写完成后按 `Ctrl+Shift+D` 退出调试模式
6. **先烧写协调器，再烧写终端节点**

## 硬件接线

### 终端节点

| 功能 | CC2530 引脚 | 外设 |
|------|-------------|------|
| DHT11 数据线 | P2.0 | DHT11 DATA 引脚 |
| 水泵 | P0.6 | 板载继电器，高电平吸合 |
| 水泵指示灯 | P1.0 | 板载 LED D10，低电平亮 |
| 施肥指示灯 | P1.1 | 板载 LED D2，低电平亮 |
| 灭虫灯指示 | P1.6 | 板载 LED D11，低电平亮 |
| 光敏电阻 | P0.7 | GL5516 分压输出，固件读取 ADC 后映射为 0-100 相对光照值 |
| OLED SCK | P1.2 | SPI OLED |
| OLED SDA/MOSI | P1.3 | SPI OLED |
| OLED RES | P1.7 | SPI OLED |
| OLED DC | P0.0 | SPI OLED |
| OLED CS | GND | SPI OLED 片选固定使能 |

### 协调器

| 功能 | CC2530 引脚 | 外设 |
|------|-------------|------|
| UART0 TX | P0.3 | USB 转串口模块 RX |
| UART0 RX | P0.2 | USB 转串口模块 TX |

## 通信协议

### 传感器数据格式（终端→协调器→PC）

```
t:25-h:60-l:800-s:45\r\n
```

| 字段 | 含义 | 范围 |
|------|------|------|
| t | 温度 (°C) | 0-50 |
| h | 湿度 (%) | 20-90 |
| l | 光照相对值 | 0-100；来自 GL5516/P0.7 ADC，不宣称精确 lux |
| s | 土壤湿度模拟值 (%) | 25-60 |

### 控制命令格式（PC→协调器→终端）

| 命令 | 功能 |
|------|------|
| `BLEGLED1` | 开启水泵：P0.6 继电器吸合，P1.0 指示灯点亮 |
| `BLEKLED1` | 关闭水泵：P0.6 继电器断开，P1.0 指示灯熄灭 |
| `BLEGLED2` | 开启施肥：P1.1 指示灯点亮 |
| `BLEKLED2` | 关闭施肥：P1.1 指示灯熄灭 |
| `BLEGLED3` | 开启灭虫灯：P1.6 指示灯点亮 |
| `BLEKLED3` | 关闭灭虫灯：P1.6 指示灯熄灭 |

三路手动控制都必须做现场 smoke：后端 `ControlLog`、bridge 命令日志、ED 端响应需要对应起来。施肥/灭虫按课程设计用板端 LED/指示模拟验收。

## P1 验收边界

1. 第一条 smoke：C 板串口持续输出 `t/h/l/s`，`serial_bridge` 出现 `sensor` 日志，云端上位机实时和历史都能看到同一板卡新记录。
2. OLED 纳入 P1 必做：ED 固件已嵌入 OLED 刷新代码；启用 `HAL_OLED` 后只显示温度、空气湿度、光照相对值；土壤 `s` 只上报给上位机。
3. 自动浇水：后端规则触发后，必须同时保留 `ControlLog`、bridge 下发 `BLEGLED1/BLEKLED1` 日志、ED 水泵/继电器动作证据。临时调阈值 smoke 只证明控制链路。
4. 流水灯报警：后端下发 `BLEALARM1/BLEALARM0`，ED 本地做流水灯表现；实现时不能覆盖或误改水泵继电器状态。
5. CO2/红外、EC/TDS/肥力按课程模拟/模型字段在后端接入，不能标成硬件实测；板端继续只上报 `t/h/l/s`。

## 常见问题

**Q: 编译报错找不到 HalOled.h？**
A: 需要将 OLED 驱动文件添加到工程中，并确保头文件路径已加入 IAR 的 Include Paths 设置。

**Q: 终端节点无法入网？**
A: 确认协调器已先上电建网；检查两块板子的 PANID 和信道设置是否一致（默认使用 Z-Stack 的自动配置）。

**Q: 串口收不到数据？**
A: 确认协调器工程定义了 `HAL_UART=TRUE` 和 `HAL_UART_DMA=1`；检查 TX/RX 接线是否交叉连接；串口助手波特率设为 115200。

**Q: DHT11 读取一直失败？**
A: 检查 P2.0 接线是否正确；DHT11 需要 4.7K 上拉电阻；上电后至少等待 1 秒再读取。
