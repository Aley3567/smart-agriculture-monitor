# 组队分工 & 硬件对接任务

> 2026-06-29 下午拿到硬件后的分工表

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
    └── hardware-interface-alignment.md ← 接口对接清单（参考）
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
# 协调器工程选 CoordinatorEB-Pro 配置，编译
# 终端节点工程选 EndDeviceEB-Pro 配置，编译
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

### 第 1 步：检查硬件（gln 清点，5 分钟）

- [ ] CC2530 开发板 x2
- [ ] CC Debugger 或板载 USB 烧写口
- [ ] USB 转串口模块
- [ ] DHT11 温湿度传感器模块
- [ ] 杜邦线若干
- [ ] USB 数据线

### 第 2 步：编译烧写（yh 操作，15 分钟）

- [ ] IAR 打开协调器工程 → `CoordinatorEB-Pro` → F7 编译 → 0 Errors
- [ ] CC Debugger 连协调器板 → Ctrl+D 烧写 → Ctrl+Shift+D 退出
- [ ] 协调器上电（先不断电）
- [ ] IAR 打开终端节点工程 → `EndDeviceEB-Pro` → F7 编译 → 0 Errors
- [ ] CC Debugger 改连终端节点板 → Ctrl+D 烧写 → Ctrl+Shift+D 退出

> 编译报错？看 `docs/hardware-quick-debug.md` 阶段一

### 第 3 步：接线（yh + gln 一起，10 分钟）

**终端节点板：**
- [ ] DHT11 DATA → **P2.0**
- [ ] DHT11 VCC → 3.3V
- [ ] DHT11 GND → GND

**协调器板 → USB 转串口：**
- [ ] 协调器 P0.3 (TX) → 转串口模块 RX
- [ ] 协调器 P0.2 (RX) → 转串口模块 TX
- [ ] GND → GND
- [ ] USB 转串口模块插 yh 的 Windows 电脑

### 第 4 步：上电 & 串口验证（yh 操作，yufeng 远程观察，5 分钟）

- [ ] 协调器先上电（等 3 秒让它建网）
- [ ] 终端节点上电（自动入网）
- [ ] 打开串口助手 → 选对应 COM 口 → **115200** → 8N1
- [ ] 等待数据出现：`t:25-h:60-l:800-s:45`
- [ ] 手动发送 `BLEGLED1` → 终端节点 LED 亮
- [ ] 手动发送 `BLEKLED1` → LED 灭

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
- [ ] 监控看板显示真实温湿度数据（不是 0 或固定值）
- [ ] 点击"开启水泵" → 终端节点 P1.0 LED 亮（gln 拍下来）
- [ ] 点击"关闭水泵" → LED 灭
- [ ] 测试施肥（P1.1）和天窗（P1.6）控制
- [ ] 检查历史数据页面是否有记录
- [ ] 检查报警日志是否正常

> bridge 异常？看 `docs/hardware-quick-debug.md` 阶段四

---

## 时间预估

| 步骤 | 耗时 | 累计 |
|------|------|------|
| 检查硬件 | 5 min | 5 min |
| 编译烧写 | 15 min | 20 min |
| 接线 | 10 min | 30 min |
| 串口验证 | 5 min | 35 min |
| 启动 bridge | 5 min | 40 min |
| 全链路验证 | 5 min | **45 min** |

顺利的话 45 分钟全通。留出排错时间，预计 1-1.5 小时。
