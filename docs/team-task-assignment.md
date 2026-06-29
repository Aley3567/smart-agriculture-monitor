# 组队分工 & 硬件对接任务（创思通信集成板 · 双板 ZigBee）

> 2026-06-29 拿到硬件后的分工表。实物为两块"创思通信 CC2530 物联网集成板"，DHT11/光敏/继电器/LED/OLED/CH340 全部板载，走双板 ZigBee。

---

## 硬件方案 & 真实引脚（先看懂）

| 板 | 固件 | 角色 | 接 PC？ |
|----|------|------|--------|
| **板1** | `end_device` | 终端：采 DHT11 + 控继电器/LED | 否，USB 供电即可 |
| **板2** | `coordinator` | 协调器：板载 UART(CH340) 桥接 | 是，跑 bridge |

> 协调器板自身也板载传感器，但烧 coordinator 后不工作——数据全部来自板1。引脚真值见 `docs/hardcoding-checklist.md`：

| 器件 | 引脚 | 电平语义 |
|------|------|---------|
| DHT11 数据线 | P2.0 | —— |
| 继电器（水泵） | **P0.6** | **高电平吸合** |
| LED1/2/3 | P1.0/P1.1/P1.6 | **低电平亮** |
| 光敏（光照） | P0.7 | 未接 ADC，`l` 为模拟值 |
| 板载串口 UART0 | P0.2/P0.3 | CH340，直连 PC |

命令语义：`BLEGLED1`→继电器吸合+LED1亮；`BLEGLED2/3`→LED2/3亮；`BLEK*`→对应关闭。

---

## 成员分工

| 成员 | 角色 | 设备 | 负责模块 |
|------|------|------|----------|
| **张育逢 (yufeng)** | 软件/系统集成 | Mac | 后端 + 前端 + 云端部署 + 串口桥接逻辑 + 系统联调 |
| **yh** | 硬件/烧写 | Windows (IAR) | 固件编译烧写 + 硬件接线 + 串口调试 + bridge 运行 |
| **gln** | 协助/测试 | - | 辅助接线测试 + 记录实验现象 + 拍摄演示视频 |

---

## 每人需要下载的内容

### 张育逢 (yufeng) — 不需要额外下载

你已经有完整仓库。核心工作：
- 在 Mac 浏览器打开 http://119.91.114.175:18082 监控实时数据
- 通过前端界面测试控制命令
- 如有问题通过 Claude 实时排错

### yh — 下载以下内容

从 GitHub 仓库 clone 或下载 zip：

```
需要的文件：
├── firmware/                        ← 固件源码
│   ├── coordinator/SampleApp.c/.h   ← 协调器固件
│   ├── end_device/SampleApp.c/.h    ← 终端节点固件
│   └── README.md                    ← 烧写说明
├── serial_bridge/                   ← 串口桥接程序
│   ├── bridge.py                    ← 主程序
│   ├── config.py                    ← 配置（已设好线上服务器地址）
│   ├── mock_serial.py               ← mock 测试用
│   └── requirements.txt             ← Python 依赖
└── docs/
    ├── hardware-quick-debug.md      ← 排错速查表（必看）
    ├── hardware-interface-alignment.md ← 接口对接清单（参考）
    └── board-naming-log-design.md   ← 多板命名和远端日志设计
```

**Windows 环境准备：**
```bash
# 1. 安装 Python 依赖
pip install pyserial websockets

# 2. 测试 mock 模式
cd serial_bridge
python bridge.py --mock
# 看到 "websocket connected" 和 "sensor >>" 日志就说明通了
# Ctrl+C 停掉

# 3. IAR 编译准备（拿到硬件前就做）
# 复制两份 Z-Stack 工程（之前做实验的那个）
# 分别命名为"协调器"和"终端节点"
# 用 firmware/ 里的文件替换对应工程的 Source/SampleApp.c 和 SampleApp.h
# 协调器工程选 CoordinatorEB 配置，编译
# 终端节点工程选 EndDeviceEB 配置，编译
# 两个都 0 Errors 就准备就绪
```

### gln — 下载以下内容

```
需要的文件：
└── docs/
    ├── hardware-quick-debug.md      ← 排错速查表
    └── team-task-assignment.md      ← 本文件
```

不需要编程环境。重点任务：
- 记录每个测试步骤的结果（成功/失败/现象）
- 用手机拍摄演示视频（板子 LED 变化、串口输出画面）
- 辅助 yh 接线（看清引脚号，防止接错）

---

## 硬件对接步骤（按顺序执行）

### 第 0 步：板子命名（yh + gln，3 分钟）

- [ ] 给终端板贴纸：第一块为 **A / greenhouse-a**
- [ ] 如果有第二、三块终端板，依次贴 **B / greenhouse-b**、**C / greenhouse-c**
- [ ] 记录每块板对应的串口号、安装位置、用途和负责人
> 注：多板上传区分是**未来设计**（见 `docs/board-naming-log-design.md`）。**当前 `bridge.py` 不支持 `--board-id/--board-name`**，单终端无需带——第 5 步按普通命令启动即可。物理贴纸命名仅用于团队记录。

### 第 1 步：检查硬件（gln 清点，3 分钟）

- [ ] 创思通信集成板 ×2
- [ ] CC Debugger（或板载 DOWNLOAD 口烧录方式）
- [ ] USB 数据线 ×2（板2 接 PC，板1 供电）

> DHT11、USB 转串口都板载，**不用外接传感器/转串口模块/杜邦线**。

### 第 2 步：编译烧写（yh 操作，15 分钟）

> 装 `5.开发工具/1.IAR EW8051 V8.1` + `ZStack-CC2530-2.3.0-1.4.0` 协议栈。工程从哪打开、为什么**别用**资料里现成的 `SampleApp.eww`（那是 Smart Energy 版、没有我们的源码）：见 `firmware/README.md` 步骤1。

- [ ] IAR 打开协调器工程 → `CoordinatorEB` → F7 编译 → 0 Errors
- [ ] CC Debugger 连协调器板 → Ctrl+D 烧写 → Ctrl+Shift+D 退出
- [ ] 协调器上电（先不断电）
- [ ] IAR 打开终端节点工程 → `EndDeviceEB` → F7 编译 → 0 Errors
- [ ] CC Debugger 改连终端节点板 → Ctrl+D 烧写 → Ctrl+Shift+D 退出

> 编译报错？看 `docs/hardware-quick-debug.md` 阶段一。
> OLED 报 `HalOled.h` 缺失：**不要**加 `HAL_OLED` 宏，直接编译跳过。

> ⚠️ **最容易翻车 — 组网参数必须一致：** 两个工程的 `f8wConfig.cfg` 里 `ZDAPP_CONFIG_PAN_ID` 和 `DEFAULT_CHANLIST`（信道）必须**完全相同**，否则两板组不上网、串口无数据。多组同场要错开 PAN ID 防串数据。

### 第 3 步：供电 & 接 PC（yh + gln，3 分钟）

集成板无需接线（DHT11/CH340 板载）：

- [ ] **板2（协调器）**：`UART` 那个 USB 口用数据线接 PC
- [ ] **板1（终端）**：USB 口接电脑/电源供电（不接 bridge）

### 第 4 步：上电 & 串口验证（yh 操作，yufeng 远程观察，5 分钟）

- [ ] **板2 协调器先上电**（等 3 秒让它建网）
- [ ] **板1 终端后上电**（自动入网）
- [ ] 打开串口助手 → 选**板2** 的 COM 口 → **115200** → 8N1
- [ ] 等数据出现：`t:25-h:60-l:800-s:45`（温湿度真实；光照/土壤目前是**模拟值**，正常）
- [ ] 手动发送 `BLEGLED1` → 板1 **继电器吸合（咔哒声）+ LED1 亮**
- [ ] 手动发送 `BLEKLED1` → 继电器断开 + LED1 灭

> 串口异常？看 `docs/hardware-quick-debug.md` 阶段三

### 第 5 步：启动 bridge（yh 操作，5 分钟）

- [ ] **关掉串口助手**（释放 COM 口）
- [ ] 打开 cmd/PowerShell：
  ```
  cd serial_bridge
  python bridge.py --port COM3 --baud 115200
  ```
  （COM3 改成实际 COM 编号）
- [ ] 看到 `websocket connected` → 成功
- [ ] 看到 `sensor >> {'temp': ...}` → 数据在上传

### 第 6 步：全链路验证（yufeng 操作，gln 拍视频，5 分钟）

- [ ] yufeng 在 Mac 打开 http://119.91.114.175:18082
- [ ] 监控看板显示真实温湿度数据（变化的，不是 0 或固定值）
- [ ] 点击"开启水泵" → 板1 **继电器吸合 + LED1(P1.0) 亮**（gln 拍下来）
- [ ] 点击"关闭水泵" → 继电器断开 + 灭
- [ ] 测试施肥（LED2/P1.1）和天窗（LED3/P1.6）控制
- [ ] 检查历史数据页面是否有记录
- [ ] 检查报警日志是否正常

> bridge 异常？看 `docs/hardware-quick-debug.md` 阶段四

---

## 时间预估

| 步骤 | 耗时 | 累计 |
|------|------|------|
| 检查硬件 | 3 min | 3 min |
| 编译烧写（两块板） | 15 min | 18 min |
| 供电接 PC | 3 min | 21 min |
| 串口验证 | 5 min | 26 min |
| 启动 bridge | 5 min | 31 min |
| 全链路验证 | 5 min | **36 min** |

顺利约 35 分钟全通。留排错时间预计 1 小时。最大不确定性在**组网参数一致**和**烧录配置选对**两处。
