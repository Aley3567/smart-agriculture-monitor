# 智慧农业课程设计最终收口说明

最后更新：2026-06-30

本文作为当前项目的收口总表，只服务于一个目标：判断最终 4 条课程要求已经做到哪里、还差什么现场验证，以及哪些文档应该保留、合并、归档或删除。

## 1. 最终要求

1. 温度、湿度、光照能实时在 OLED 屏幕显示数据，并向上位机发送数据。
2. 数据异常时流水灯报警；当湿度不够，APP 自动开启水泵浇水。
3. 手动开关普通浇水、手动开关施肥水泵、手动开关灭虫灯。
4. 在上位机查看温湿度、二氧化碳、土壤湿度、土壤 TDS/电导率传感器、红外传感器的数据；配置土壤湿度、土壤肥力阈值信息；当数据不满足阈值时有特别显示；可查看近期历史数据。

## 2. 当前统一口径

- 本项目按课程设计和现有条件收口：一套 C/ED 板链路，不再追问额外真实负载或新增传感器。
- C 板是 Coordinator，只负责 ZigBee 与 PC 串口桥接。
- ED 板是 End Device，负责 DHT11、GL5516/P0.7、OLED、水泵继电器、板载 LED 模拟输出。
- OLED 只显示温度、空气湿度、光照，不显示土壤 `s`。
- 串口/上报协议继续保留 `t/h/l/s`，其中 `s` 是板端土壤湿度模拟值，用于上位机和自动浇水演示。
- 施肥泵、灭虫灯按板载 LED/指示输出模拟。
- CO2、土壤 EC/TDS、土壤肥力、红外按后端模型/模拟字段实现，不能说成硬件实测。

## 3. 四条要求状态

| 要求 | 当前状态 | 已完成 | 还差什么 |
| --- | --- | --- | --- |
| 1. OLED 显示温湿度光照，并向上位机发送 | 基本完成，待现场验证 | ED 固件读取 DHT11 温湿度；光照改为 P0.7 ADC；OLED 代码只显示温度、空气湿度、光照；上报仍为 `t/h/l/s`；Coordinator 透传；bridge/后端/前端能接收 | IAR 编译启用 OLED 驱动；烧录后拍 OLED 显示；串口看到 `t/h/l/s`；上位机实时/历史可见 |
| 2. 异常流水灯报警，土壤湿度不足自动开水泵 | 基本完成，待现场验证 | 后端阈值告警写 `AlarmLog`；异常下发 `BLEALARM1/BLEALARM0`；ED 固件有流水灯报警；土壤湿度自动浇水规则已实现；板端土壤模拟能配合 `35%` 开泵、`45%` 关泵 | 烧录后验证流水灯；验证异常恢复后停止报警；验证自动开/关水泵有 `ControlLog`、bridge 命令和板端继电器响应 |
| 3. 手动开关普通浇水、施肥水泵、灭虫灯 | 软件完成，待现场三路 smoke | APP/后端支持 `pump/fertilizer/pest_light`；命令为 `BLEGLED1/2/3` 和 `BLEKLED1/2/3`；ED 固件映射到 P0.6+P1.0、P1.1、P1.6 | 明天接板逐个点击 on/off，确认后端日志、bridge 命令、板端响应 |
| 4. 上位机查看全部字段、配置土壤湿度/肥力阈值、异常特别显示、历史 | 基本完成，待页面 smoke | 后端动态生成 CO2、soil_ec、soil_tds、soil_fertility、infrared；土壤湿度和土壤肥力阈值可配置；Dashboard/History/CSV 展示模型字段；异常写 `AlarmLog` 并特别显示；历史动态补模型字段 | 启动本地/云端页面做 smoke；截图 Dashboard、History、Settings、AlarmLog；确认答辩时说明模型来源 |

## 4. 明天最小验收清单

必须拿到的证据：

1. OLED 照片或视频：只显示温度、空气湿度、光照。
2. 串口/bridge 日志：出现 `t:xx-h:xx-l:xx-s:xx`，上位机实时显示。
3. 三路手动控制：
   - `pump` on/off：`P0.6` 继电器和 `P1.0` 指示。
   - `fertilizer` on/off：`P1.1` 指示。
   - `pest_light` on/off：`P1.6` 指示。
4. 异常报警：后端下发 `BLEALARM1` 后 ED 流水灯可见；恢复或关闭后 `BLEALARM0` 停止。
5. 自动浇水：土壤湿度低于规则后自动 `pump on`，回升后自动 `pump off`。
6. 第 4 点页面截图：CO2、EC、TDS、肥力、红外有值；Settings 能配置土壤湿度和土壤肥力阈值；History 能看到近期历史。

## 5. 文档清理状态

清理前，排除 `frontend/node_modules` 和 `frontend/dist` 后，仓库有 17 个 Markdown 文档。本文新增后变为 18 个；本轮已删除 `NOTES.md` 和 `frontend/README.md`，其余过程资料按批次归档到 `docs/archive/20260630-cleanup/`，所以当前剩余 16 个 Markdown 文档。

| # | 文档 | 用途 | 当前问题 | 建议 |
| --- | --- | --- | --- | --- |
| 1 | `CLAUDE.md` | 仓库总览、架构、部署和本地开发命令 | 部分描述仍偏早期口径，例如光照/土壤模拟说法需要同步 | 保留，但应精简成当前 README 级入口 |
| 2 | `docs/archive/20260630-cleanup/root/MISSION.md` | 答辩学习目标和成功标准 | 偏教学/学习任务，不是交付文档 | 已归档 |
| 3 | `NOTES.md` | 教学备注 | 已有旧口径，且内容很短，可合并进总文档 | 已删除 |
| 4 | `docs/archive/20260630-cleanup/root/PRD.md` | 原始产品需求文档 | 很长，部分旧硬件/需求口径已被后续文档覆盖 | 已归档为历史 PRD |
| 5 | `docs/archive/20260630-cleanup/root/RESOURCES.md` | 答辩资料索引 | 有用但偏学习资源，不是实现事实 | 已归档 |
| 6 | `frontend/README.md` | Vite 模板默认说明 | 对项目没有实际价值 | 已删除 |
| 7 | `firmware/README.md` | 固件集成、引脚、协议、烧录说明 | 是明天接板核心文档 | 保留 |
| 8 | `docs/archive/20260630-cleanup/docs/board-naming-log-design.md` | 多板命名、远端日志、多板扩展设计 | 当前单板课程设计不需要多板作为主线 | 已归档为 P2 扩展 |
| 9 | `docs/hardcoding-checklist.md` | 硬件硬编码和引脚核对表 | 对接板有用 | 保留到硬件验收结束 |
| 10 | `docs/hardware-interface-alignment.md` | 硬件接口、实验源码继承、真机对齐证据 | 内容较长但有证据价值 | 保留，之后可压缩合并进固件 README |
| 11 | `docs/hardware-quick-debug.md` | 明天现场硬件排错速查 | 非常实用 | 保留到现场验收结束 |
| 12 | `docs/p0-deferred-linear-backlog.md` | P0/P1 后续 issue/backlog | 当前内容已经部分完成，后续可转 issue | 答辩前可保留；收尾后归档 |
| 13 | `docs/archive/20260630-cleanup/docs/prd-realtime-board-soil-cloud-sync.md` | 本地板卡到云端、土壤模型、多板/云端设计 PRD | 部分内容已被当前实现覆盖，也包含多板扩展 | 已归档，不作为当前收口事实源 |
| 14 | `docs/team-task-assignment.md` | 组员分工、硬件接入任务 | 明天协作有用 | 保留到接板验收结束 |
| 15 | `docs/trace-bullet-requirements-status.md` | 四条 Trace Bullet 的详细追踪矩阵 | 详细但偏过程记录，和本文重叠 | 保留为详细版；答辩前可只看本文 |
| 16 | `docs/archive/20260630-cleanup/design-handoff/smart-agriculture-ui-mockups-20260629/README.md` | UI 稿交接说明 | 设计交接历史，不是当前实现事实 | 已归档 |
| 17 | `docs/archive/20260630-cleanup/design-handoff/smart-agriculture-ui-mockups-20260629/FRONTEND_SESSION_BRIEF.md` | 前端会话交接文档 | 已经被当前实现吸收，仍含旧“光照待 ADC”口径 | 已归档 |

另有一个非 Markdown 大文件：

- `design-handoff/smart-agriculture-ui-mockups-20260629.zip`：UI 交接压缩包。本轮已删除。

## 6. 建议清理方案

### 6.1 最小保留集

答辩/接板前建议只保留这些作为主入口：

- `docs/final-requirements-status-and-doc-inventory.md`
- `firmware/README.md`
- `docs/hardware-quick-debug.md`
- `docs/hardcoding-checklist.md`
- `docs/team-task-assignment.md`
- `docs/trace-bullet-requirements-status.md`

### 6.2 本轮已归档

已移动到 `docs/archive/20260630-cleanup/`：

- `MISSION.md`
- `RESOURCES.md`
- `PRD.md`
- `docs/board-naming-log-design.md`
- `docs/prd-realtime-board-soil-cloud-sync.md`
- `design-handoff/smart-agriculture-ui-mockups-20260629/`

### 6.3 本轮已删除

- `NOTES.md`
- `frontend/README.md`
- `design-handoff/smart-agriculture-ui-mockups-20260629.zip`

### 6.4 下一批可继续处理

- `CLAUDE.md`：同步当前最终口径，压缩成项目入口。
- `docs/hardware-interface-alignment.md`：明天硬件验收后压缩合并到 `firmware/README.md`，原文归档。
- `docs/hardcoding-checklist.md`：明天验收后合并进 `firmware/README.md`。
- `docs/p0-deferred-linear-backlog.md`：把已完成项移除，只保留剩余验收事项，或归档。
- `docs/team-task-assignment.md`：接板验收结束后归档。

## 7. 当前不建议删除的原因

现在不直接删除文档，是因为明天还要接板测试。硬件现场排错时，旧的接口对齐、分工、排错文档仍可能救急。建议等明天验收结束后再做一次清理：

1. 保留最终收口文档。
2. 保留固件烧录/排错文档。
3. 把过程性 PRD、设计稿、backlog、学习材料统一移入 `docs/archive/`。
4. 删除模板 README 和短 NOTES。
