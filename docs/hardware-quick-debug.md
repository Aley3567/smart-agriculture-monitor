# 接硬件现场排错速查表

> 下午拿到板子后，按现象直接查对应解法。

---

## 阶段一：IAR 编译

| 现象 | 原因 | 解法 |
|------|------|------|
| `Fatal Error: Could not open file "HalOled.h"` | OLED 驱动文件缺失 | 已用条件编译处理，**不需要**在 IAR 预编译宏中加 `HAL_OLED`，直接编译即可跳过 OLED |
| `Fatal Error: Could not open file "SampleApp.h"` | 没把 .h 文件一起替换 | SampleApp.c 和 SampleApp.h 必须成对替换 |
| `Error: Undefined external "SampleApp_Init"` | 选错了编译配置 | 协调器选 `CoordinatorEB`，终端节点选 `EndDeviceEB`（带 CC2591 功放才用 `-Pro`） |
| `Warning: variable declared but not used` | 正常，不影响 | 忽略，只要 0 Errors 即可 |
| 大量 `Error` 来自 `Components/` 目录 | Z-Stack 版本不匹配 | 确认 Z-Stack 版本为 2.3.0-1.4.0 或 2.5.1a |

## 阶段二：烧写

| 现象 | 原因 | 解法 |
|------|------|------|
| CC Debugger 红灯 | 没识别到芯片 | 检查排线方向、板子是否上电 |
| CC Debugger 绿灯但下载失败 | 驱动问题 | 设备管理器里确认驱动已安装（TI CC Debugger） |
| 下载成功但板子无反应 | 板子没复位 | 断电重新上电 |
| 没有 CC Debugger | 板子自带 USB 口 | 用板子上的 USB 口连电脑，IAR 里应该也能识别 |

## 阶段三：串口验证

| 现象 | 原因 | 解法 |
|------|------|------|
| 串口助手打开失败 | COM 口被占用或选错 | 设备管理器确认 COM 编号，关掉其他占用程序 |
| 串口有数据但全是乱码 | 波特率不对 | 确认串口助手设 **115200**，不是 9600 |
| 串口完全没数据 | TX/RX 接反或终端节点没入网 | (1) 交换 TX/RX 线 (2) 先上电协调器等 3 秒再上电终端节点 |
| 数据格式不对，有中文 | 烧的是实验原版固件 | 必须烧 `firmware/` 里的项目固件 |
| `t:25-h:60` 但没有 `l:` 和 `s:` | 光照 ADC 或土壤模拟路径没有参与组包 | 检查 `SampleApp_ReadLight()`、`SampleApp_SimulateSoil()` 和 `SampleApp_SendPeriodicMessage()` |
| 发 `BLEGLED1` 但 LED 不亮 | (1) 命令没到终端节点 (2) P1.0 没接 LED | (1) 确认协调器的 UartCB 在工作 (2) 用万用表测 P1.0 电平 |

## 阶段四：bridge.py

云端辅助调试入口：

- Dashboard 右侧“现场调试”面板会显示最近 bridge 调试事件。
- API 可直接查：`GET http://119.91.114.175:18082/api/debug-events?board_id=A&limit=20`
- 关键事件含义：

| 事件 | 说明 | 判断 |
|------|------|------|
| `bridge_connected` | 现场电脑的 bridge 已连上腾讯云 | 云端链路 OK |
| `serial_raw_line` | bridge 从 C 板串口读到了原始行 | C 板 UART 有输出 |
| `serial_parse_failed` | 串口有数据但不是 `t/h/l/s` 格式 | 可能烧错固件、波特率错或输出格式不对 |
| `sensor_parsed` | `t/h/l/s` 解析成功并准备上云 | 上行数据格式 OK |
| `control_received` | bridge 收到云端控制命令 | 云端到现场电脑 OK |
| `control_written_serial` | bridge 已把控制命令写入串口 | 现场电脑到 C 板 UART 写入 OK |

如果云端只有 `bridge_connected`，没有 `serial_raw_line`，优先查 C 板串口、ED 入网和波特率。

如果有 `serial_raw_line` 但没有 `sensor_parsed`，优先查固件输出格式。

如果有 `control_written_serial` 但板端没反应，优先查 C 板到 ED 的 ZigBee 转发和 ED 命令解析。

| 现象 | 原因 | 解法 |
|------|------|------|
| `serial open failed` | COM 口被串口助手占着 | **先关掉串口助手**再启动 bridge |
| `failed to parse: xxx` | 串口数据格式不匹配 | 把这行 xxx 的内容贴出来分析 |
| `websocket error: Connection refused` | 云端服务器没开 | 浏览器访问 http://119.91.114.175:18082/api/status 确认返回 200 |
| 连上了但前端不显示数据 | bridge 发的数据格式后端没认 | 看 bridge 日志里 `sensor >>` 后面的内容，确认 4 个字段都有 |
| 前端能看数据但控制不了 | 下行链路问题 | bridge 日志里找 `command >> serial`，确认命令有写到串口 |
| `ModuleNotFoundError: pyserial` | 依赖没装 | `pip install pyserial websockets` |

## 常用命令速查

```bash
# Windows 启动 bridge（改 COM3 为实际端口）
python bridge.py --port COM3 --baud 115200

# mock 模式测试（不需要硬件）
python bridge.py --mock

# 查看可用 COM 口（PowerShell）
[System.IO.Ports.SerialPort]::getportnames()

# 检查云端服务是否在线
curl http://119.91.114.175:18082/api/status
```
