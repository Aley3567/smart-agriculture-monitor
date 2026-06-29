# 智慧农业监测系统 - CC2530 固件

## 概述

本目录包含智慧农业监测系统的 CC2530 单片机固件核心应用层代码，基于 TI Z-Stack 2.5.1a 协议栈的 SampleApp 例程修改。

系统包含两块 CC2530 开发板：
- **终端节点 (End Device)**: 采集 DHT11 温湿度、模拟光照/土壤湿度，通过 ZigBee 发送到协调器；接收控制命令驱动执行器
- **协调器 (Coordinator)**: 接收终端节点数据通过 UART0 转发到 PC；接收 PC 串口命令转发到终端节点

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

- IAR Embedded Workbench for 8051 (v10.20 或以上)
- TI Z-Stack 2.5.1a 协议栈 (安装路径通常为 `C:\Texas Instruments\ZStack-CC2530-2.5.1a`)
- CC Debugger 烧写器
- 两块 CC2530 开发板

### 步骤 1: 打开 Z-Stack 工程

Z-Stack 安装目录下找到 SampleApp 工程：

```
ZStack-CC2530-2.5.1a\Projects\zstack\Samples\SampleApp\CC2530DB\
```

分别打开 `SampleApp.eww`，IAR 中会看到多个编译配置。

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

选择方法：IAR 菜单 `Project` → `Edit Configurations` 或工具栏下拉框。

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
| 天窗指示灯 | P1.6 | 板载 LED D11，低电平亮 |
| 光敏电阻 | P0.7 | GL5516 分压输出，当前固件仍模拟光照 |
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
| l | 光照 (lux) | 500-1500 |
| s | 土壤湿度 (%) | 40-60 |

### 控制命令格式（PC→协调器→终端）

| 命令 | 功能 |
|------|------|
| `BLEGLED1` | 开启水泵：P0.6 继电器吸合，P1.0 指示灯点亮 |
| `BLEKLED1` | 关闭水泵：P0.6 继电器断开，P1.0 指示灯熄灭 |
| `BLEGLED2` | 开启施肥：P1.1 指示灯点亮 |
| `BLEKLED2` | 关闭施肥：P1.1 指示灯熄灭 |
| `BLEGLED3` | 开启天窗：P1.6 指示灯点亮 |
| `BLEKLED3` | 关闭天窗：P1.6 指示灯熄灭 |

## 常见问题

**Q: 编译报错找不到 HalOled.h？**
A: 需要将 OLED 驱动文件添加到工程中，并确保头文件路径已加入 IAR 的 Include Paths 设置。

**Q: 终端节点无法入网？**
A: 确认协调器已先上电建网；检查两块板子的 PANID 和信道设置是否一致（默认使用 Z-Stack 的自动配置）。

**Q: 串口收不到数据？**
A: 确认协调器工程定义了 `HAL_UART=TRUE` 和 `HAL_UART_DMA=1`；检查 TX/RX 接线是否交叉连接；串口助手波特率设为 115200。

**Q: DHT11 读取一直失败？**
A: 检查 P2.0 接线是否正确；DHT11 需要 4.7K 上拉电阻；上电后至少等待 1 秒再读取。
