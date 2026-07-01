# OLED 驱动资料召回与移植说明

> 给后续 Claude / Codex 继续处理 OLED 驱动用。本文记录本机资料路径、已确认事实、可复用例程、以及建议移植路线。

## 结论

- 当前仓库 `firmware/` 里没有 `HalOled.h` / `HalOled.c`，所以默认不定义 `HAL_OLED` 时可以编译，但 OLED 不会亮。
- `firmware/end_device/SampleApp.c` 里 OLED 显示逻辑已经写好，并且都包在 `#ifdef HAL_OLED` 内。
- 本机实验资料里已经找到可移植的 **C51 SPI OLED 例程**，最适合改造成本项目的 `HalOled.h` / `HalOled.c`。
- 资料判断这块 0.96 寸 OLED 的主控优先按 **SSD1306** 处理，分辨率 **128x64**。
- 本项目原理图读到的 OLED 接线是 **SPI**：`SCK=P1.2`、`MOSI/SDA=P1.3`、`RES=P1.7`、`DC=P0.0`、`CS=GND`。

## 关键资料路径

原始资料根目录：

```text
/Users/admin/Downloads/实验课/12.0.96寸OLED模块资料/
```

最重要的 C51 SPI 例程压缩包：

```text
/Users/admin/Downloads/实验课/12.0.96寸OLED模块资料/0.96OLED显示屏测试程序/0.96OLED显示屏_C51系列_SPI_例程.rar
```

已解压到临时目录的例程源码（临时目录可能被清理，必要时重新解压）：

```text
/tmp/oled-c51-spi/中景园电子0.96OLED显示屏_C51系列_SPI_例程/SRC/oled.c
/tmp/oled-c51-spi/中景园电子0.96OLED显示屏_C51系列_SPI_例程/SRC/oled.h
/tmp/oled-c51-spi/中景园电子0.96OLED显示屏_C51系列_SPI_例程/SRC/oledfont.h
```

重新解压命令：

```bash
rm -rf /tmp/oled-c51-spi
mkdir -p /tmp/oled-c51-spi
unar -quiet -o /tmp/oled-c51-spi \
  '/Users/admin/Downloads/实验课/12.0.96寸OLED模块资料/0.96OLED显示屏测试程序/0.96OLED显示屏_C51系列_SPI_例程.rar'
```

OLED 文档：

```text
/Users/admin/Downloads/实验课/12.0.96寸OLED模块资料/0.96寸OLED使用文档新手必看V2.0.pdf
```

相关芯片资料：

```text
/Users/admin/Downloads/实验课/12.0.96寸OLED模块资料/显示屏数据手册/经典款0.96OLED驱动芯片手册SSD1306规格书.pdf
/Users/admin/Downloads/实验课/12.0.96寸OLED模块资料/显示屏数据手册/新款0.96寸OLED控制芯片SSD1315规格书.pdf
/Users/admin/Downloads/实验课/12.0.96寸OLED模块资料/新款0.96寸OLED控制芯片SSD1315规格书.pdf
```

## 已确认的资料事实

从 `0.96寸OLED使用文档新手必看V2.0.pdf` 里检索到的关键内容：

- 分辨率为 `128*64`。
- 七针模块管脚顺序是 `GND, VCC, D0, D1, RES, DC, CS`。
- 文档说明本模块默认是 SPI 接口。
- 文档说明本屏所用驱动 IC 为 `SSD1306`。
- 文档还提醒 0.96 寸 SSD1306 与 1.3 寸 SSD1106 不同：SSD1306 每页 128 字节，共 8 页；SSD1106 每页 132 字节。

这意味着本项目先按 `SSD1306 128x64 page addressing` 移植是合理的。

## 原例程引脚与本项目引脚

 C51 SPI 例程 `oled.h` 原始引脚：

```c
sbit OLED_CS   = P1^4;
sbit OLED_RST  = P1^2;
sbit OLED_DC   = P1^3;
sbit OLED_SCL  = P1^0;
sbit OLED_SDIN = P1^1;
```

本项目创思通信 CC2530 集成板原理图读到的引脚：

| OLED 信号 | 本项目 CC2530 引脚 | 说明 |
|---|---|---|
| `SCK / D0` | `P1.2` | SPI 时钟 |
| `MOSI / SDA / D1` | `P1.3` | SPI 数据 |
| `RES` | `P1.7` | 低电平复位 |
| `DC` | `P0.0` | 命令/数据选择 |
| `CS` | `GND` | 片选固定使能，不占 IO |
| `VCC` | `3.3V` | 电源 |
| `GND` | `GND` | 地 |

移植时不要照搬原例程的 `P1^0/P1^1/P1^2/P1^3/P1^4`，必须改成上表。

## 当前固件期望的 OLED 接口

`firmware/end_device/SampleApp.c` 只需要三个接口：

```c
HalOledInit();
HalOledClear();
HalOledShowStr(x, y, str);
```

现有调用点显示三行：

- `HalOledShowStr(0, 0, "Smart Agri")`
- `HalOledShowStr(0, 2, ...)` 显示温度和空气湿度
- `HalOledShowStr(0, 4, ...)` 显示光照相对值

坐标语义建议沿用 C51 例程：`x` 是像素列，`y` 是 page 行。16 像素高字模占 2 个 page，所以当前 `0/2/4` 正好是三行 8x16 ASCII。

## 建议移植路线

1. 从 C51 SPI 例程提取 `oled.c`、`oled.h`、`oledfont.h`。
2. 在本仓库 `firmware/end_device/` 下新增：

```text
firmware/end_device/HalOled.c
firmware/end_device/HalOled.h
firmware/end_device/HalOledFont.h
```

3. 把原例程 API 包装成当前固件期望的接口：

```c
void HalOledInit(void);
void HalOledClear(void);
void HalOledShowStr(uint8 x, uint8 y, char *str);
```

4. 内部可复用原例程函数：

```c
OLED_Init();
OLED_Clear();
OLED_ShowString(x, y, str);
```

5. 改 GPIO 宏：

```c
#define OLED_RST      P1_7
#define OLED_DC       P0_0
#define OLED_SCL      P1_2
#define OLED_SDIN     P1_3
```

`CS` 固定接 GND，建议这样处理：

```c
#define OLED_CS_Clr()  do {} while (0)
#define OLED_CS_Set()  do {} while (0)
```

或者在写字节函数里完全删除 CS 拉低/拉高逻辑。不要新增一个不存在的 CS IO。

6. 初始化 GPIO 时要确保 OLED 引脚是普通 GPIO 输出：

```c
P0SEL &= ~0x01;  /* P0.0 DC */
P0DIR |= 0x01;

P1SEL &= ~(0x8C); /* P1.2 SCK, P1.3 MOSI, P1.7 RES */
P1DIR |= 0x8C;
```

7. IAR 工程里要把新增的 `HalOled.c` 加入编译，并把 `HalOled.h` / `HalOledFont.h` 放到 include path 能找到的位置。
8. 最后再定义 `HAL_OLED`。不要在驱动文件未加入工程前定义，否则会回到 `HalOled.h` 找不到的编译错误。

## 注意点

- 不要使用 IIC 例程。本项目原理图是 SPI，`CS/DC/RES` 都存在。
- 不要使用 U8glib。U8glib 太重，不适合直接塞进当前 Z-Stack / IAR 8051 项目。
- 不要按 SH1106/SSD1106 的 132 列偏移去写，当前资料和例程都指向 SSD1306 128 列。
- 资料包里也有 SSD1315 规格书，但当前可用 C51 SPI 例程和新手文档都是 SSD1306 口径。若实物背面丝印明确 SSD1315，再复核初始化命令；多数 SSD1315 模块兼容 SSD1306 命令集，但不要在文档里无证据宣称。
- `SampleApp.c` 的 OLED 文案已控制为温度、空气湿度、光照相对值，不显示土壤 `s`。这符合当前验收口径。

## Claude 继续探索建议

优先读：

```text
/tmp/oled-c51-spi/中景园电子0.96OLED显示屏_C51系列_SPI_例程/SRC/oled.h
/tmp/oled-c51-spi/中景园电子0.96OLED显示屏_C51系列_SPI_例程/SRC/oled.c
/tmp/oled-c51-spi/中景园电子0.96OLED显示屏_C51系列_SPI_例程/SRC/oledfont.h
/Users/admin/Desktop/smart-agriculture-monitor/firmware/end_device/SampleApp.c
/Users/admin/Desktop/smart-agriculture-monitor/firmware/end_device/SampleApp.h
```

优先改：

```text
/Users/admin/Desktop/smart-agriculture-monitor/firmware/end_device/HalOled.h
/Users/admin/Desktop/smart-agriculture-monitor/firmware/end_device/HalOled.c
/Users/admin/Desktop/smart-agriculture-monitor/firmware/end_device/HalOledFont.h
```

如果需要同步文档，再改：

```text
/Users/admin/Desktop/smart-agriculture-monitor/docs/hardcoding-checklist.md
/Users/admin/Desktop/smart-agriculture-monitor/firmware/README.md
/Users/admin/Desktop/smart-agriculture-monitor/docs/hardware-quick-debug.md
```

## 完成标准

- 不定义 `HAL_OLED` 时，固件仍能按现状跳过 OLED。
- 定义 `HAL_OLED` 且 IAR 工程加入 `HalOled.c` 后，不再报 `HalOled.h` 缺失。
- 烧录后 OLED 三行显示：
  - 系统名或标题
  - 温度 / 空气湿度
  - 光照相对值
- 串口上报 `t/h/l/s` 不受 OLED 是否启用影响。
