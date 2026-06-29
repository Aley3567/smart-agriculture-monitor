# 多板命名与远端日志设计

## 一、目标

硬件接入阶段需要把每块接入的板子命名为稳定编号，例如 A、B、C。腾讯云服务器收到数据后，必须能区分数据来自哪块板，并能远端查询对应板子的在线状态、传感器日志、控制日志和基础信息。

本设计在现有链路上做最小扩展：

```
终端板 A/B/C -> ZigBee/串口 -> serial_bridge -> FastAPI -> SQLite -> Vue/远端 API
```

## 二、命名规则

| 编号 | 推荐名称 | 角色 | 说明 |
|------|----------|------|------|
| A | greenhouse-a | 终端节点 1 | 默认第一块接入板，优先用于现场演示 |
| B | greenhouse-b | 终端节点 2 | 第二块板，可用于对比或备用 |
| C | greenhouse-c | 终端节点 3 | 第三块板，可用于扩展区域 |

命名约束：

- `board_id` 使用短编号：`A`、`B`、`C`
- `board_name` 使用可读名称：`greenhouse-a`、`greenhouse-b`、`greenhouse-c`
- 现场贴纸、固件配置、bridge 启动参数、后端数据库必须保持一致
- 不用设备用途命名板子，例如不要直接命名为 `pump`，因为用途以后可能变化

## 三、当前系统缺口

现有项目仍是单设备模型：

| 层级 | 当前状态 | 缺口 |
|------|----------|------|
| 固件上行 | 发送 `t:25-h:60-l:800-s:45` | 数据里没有板子编号 |
| `serial_bridge` | 解析 4 个传感器字段后推给后端 | 没有 `board_id` |
| 后端 `sensor_data` | 只存 temp/humi/light/soil | 不能按板子查历史 |
| 后端 `control_log` | 只存 device/action/source | 不能知道控制的是哪块板 |
| `/api/status` | 只有一个 `device_online` | 不能显示 A/B/C 分别在线 |

## 四、推荐数据协议

### 方案 A：bridge 注入 board_id（推荐，最小改动）

固件仍然发送：

```text
t:25-h:60-l:800-s:45
```

每个 `serial_bridge` 启动时指定板子编号：

```bash
python bridge.py --port COM3 --baud 115200 --board-id A --board-name greenhouse-a
```

bridge 推送给后端：

```json
{
  "type": "sensor_data",
  "board_id": "A",
  "board_name": "greenhouse-a",
  "data": {
    "temp": 25.0,
    "humi": 60.0,
    "light": 800.0,
    "soil": 45.0
  }
}
```

优点：

- 不改 CC2530 固件
- 每块板只需要用不同启动参数
- 适合当前课程设计快速接真机

限制：

- 如果多个终端节点共用同一个协调器串口，bridge 无法从串口行里天然区分 A/B/C，除非固件把编号发出来

### 方案 B：固件携带 board_id（多终端推荐）

终端节点直接发送：

```text
id:A-t:25-h:60-l:800-s:45
```

bridge 解析后推给后端：

```json
{
  "type": "sensor_data",
  "board_id": "A",
  "data": {
    "temp": 25.0,
    "humi": 60.0,
    "light": 800.0,
    "soil": 45.0
  }
}
```

优点：

- 一个协调器可以同时接收多个终端节点
- 后端日志能准确区分每条数据来自哪块终端板

限制：

- 需要改终端固件发送格式
- 需要改 `serial_bridge` 解析器，兼容 `id:` 字段

## 五、后端数据模型设计

新增 `boards` 表，保存板子基础信息：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| board_id | TEXT UNIQUE | `A` / `B` / `C` |
| board_name | TEXT | `greenhouse-a` |
| location | TEXT | 安装位置，例如 `温室1号区` |
| role | TEXT | `end_device` / `coordinator` |
| enabled | BOOLEAN | 是否启用 |
| last_seen | DATETIME | 最近一次上报时间 |
| note | TEXT | 备注 |

扩展 `sensor_data`：

| 字段 | 说明 |
|------|------|
| board_id | 数据来源板子编号 |

扩展 `alarm_log`：

| 字段 | 说明 |
|------|------|
| board_id | 触发报警的板子编号 |

扩展 `control_log`：

| 字段 | 说明 |
|------|------|
| board_id | 被控制的板子编号 |

## 六、远端 API 设计

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/boards` | 查询全部板子信息和在线状态 |
| GET | `/api/boards/{board_id}` | 查询单块板详情 |
| GET | `/api/history?board_id=A` | 查询 A 板传感器历史 |
| GET | `/api/alarms?board_id=A` | 查询 A 板报警日志 |
| GET | `/api/control-log?board_id=A` | 查询 A 板控制日志 |
| POST | `/api/control` | 增加 `board_id` 参数，控制指定板子 |
| GET | `/api/status` | 返回 `boards` 在线表，而不是单个 `device_online` |

`/api/status` 推荐返回：

```json
{
  "mode": "auto",
  "boards": {
    "A": {
      "board_name": "greenhouse-a",
      "online": true,
      "last_seen": "2026-06-29T06:30:00Z",
      "actuators": {
        "pump": false,
        "fertilizer": false,
        "skylight": true
      }
    },
    "B": {
      "board_name": "greenhouse-b",
      "online": false,
      "last_seen": null,
      "actuators": {
        "pump": false,
        "fertilizer": false,
        "skylight": false
      }
    }
  }
}
```

## 七、控制链路设计

前端/远端发送：

```json
{
  "device": "pump",
  "action": "on",
  "board_id": "A"
}
```

后端转发给 bridge：

```json
{
  "type": "control",
  "board_id": "A",
  "command": "BLEGLED1"
}
```

单 bridge 单板模式下：

- bridge 只接收与自己 `board_id` 相同的命令
- 其他板子的命令忽略

一个协调器多终端模式下：

- 协调器固件需要知道 `board_id -> ZigBee shortAddr` 的映射
- 控制命令需要包含目标板编号，例如 `A:BLEGLED1`
- 终端节点只执行发给自己的命令

## 八、现场接入流程

1. 给板子贴纸：`A / greenhouse-a`
2. 在接线记录里登记：板子编号、串口号、位置、用途、负责人
3. 启动 bridge 时带上编号：

```bash
python bridge.py --port COM3 --baud 115200 --board-id A --board-name greenhouse-a
```

4. 串口看到传感器数据后，检查 bridge 日志：

```text
sensor >> board=A {'temp': 25.0, 'humi': 60.0, 'light': 800.0, 'soil': 45.0}
```

5. 访问腾讯云后端：

```bash
curl "http://119.91.114.175:18082/api/boards"
curl "http://119.91.114.175:18082/api/history?board_id=A"
```

6. 前端看板确认 A 板在线，数据时间持续刷新
7. 远端点击 A 板水泵开关，确认 `control_log` 记录 `board_id=A`

## 九、落地优先级

### P0：必须做

- `serial_bridge` 增加 `--board-id` / `--board-name`
- WebSocket 消息增加 `board_id`
- `sensor_data` 增加 `board_id`
- `/api/history` 支持 `board_id` 筛选
- `/api/status` 能显示每块板最后上报时间

### P1：建议做

- 新增 `boards` 表
- 新增 `/api/boards`
- `control_log` 增加 `board_id`
- 前端控制按钮绑定当前选中的板子

### P2：多终端扩展

- 固件发送 `id:A`
- bridge 解析 `id`
- 协调器支持按目标板转发控制命令

## 十、当前项目建议

当前最适合先采用方案 A：bridge 注入 `board_id`。

原因是现有固件、串口格式、后端数据流已经能跑通，先通过 bridge 启动参数区分 A/B/C，可以最快支持腾讯云远端查看“哪块板在线、哪块板上传了什么数据、哪块板被控制过”。等单板链路跑稳后，再升级到方案 B，让终端固件自己携带编号。
