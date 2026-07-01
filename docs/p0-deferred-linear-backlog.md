# P0 Deferred Linear Backlog

最后更新：2026-06-30

用途：记录 P0 之后仍未处理、被推迟或需要现场证据补齐的事项。格式按 Linear issue 粒度组织，后续可直接迁移到 Linear/Jira/GitHub Issues。

## 统一最终目标

所有 backlog、P1/P2 决策、实现切片和现场验收都只服务于同一个最终目标，不创建脱离该目标的独立产品线：

1. 温度、湿度、光照能实时在 OLED 屏幕显示数据，并向上位机发送数据。
2. 数据异常时流水灯报警；当湿度不够，APP 自动开启水泵浇水。
3. 手动开关普通浇水、手动开关施肥水泵、手动开关灭虫灯。
4. 在上位机查看温湿度、二氧化碳、土壤湿度、土壤 TDS/电导率传感器、红外传感器的数据；配置土壤湿度、土壤肥力阈值信息；当数据不满足阈值时有特别显示；可查看近期历史数据。

进入 Linear 前必须检查：

- 每个 issue 必须映射到上述 4 条之一。
- 如果一个 issue 不能解释它服务哪条 Trace Bullet，就先不进入 backlog。
- 技术债、部署、测试、文档、云端 smoke 也必须说明它支撑哪条最终目标的验收。
- 不允许把 pending 字段、云端部署、测试模式、硬件增强当成新的目标；它们只是为了让上述 4 条可实现、可演示、可验收。

当前口径：

- P0 已完成的是“可演示的软件闭环”：测试注入、真实/测试来源追溯、土壤低湿自动浇水规则、安全关泵、前端测试模式、History/AlarmLog 过滤。
- 本文件只记录 P0 未完成或 P0 明确推迟的后续，不把已完成事项重复列入。
- 当前按单板课程设计收口：施肥泵、灭虫灯、CO2、土壤 EC/TDS/肥力、红外可以做模拟/模型演示，但必须标明来源，不能伪装成硬件实测。
- 硬件按 C/ED 双板架构验收：C 板接串口和 `serial_bridge`；ED 板接传感器、OLED、继电器/LED 执行器。
- P1 第一条 smoke 固定为：C 串口输出 `t/h/l/s` -> bridge 出现 `sensor` 日志 -> 云端上位机实时/历史可见。

## Linear 状态约定

| 字段 | 值 |
| --- | --- |
| Status | Backlog / Ready / Blocked / In Progress / Done |
| Priority | P0 = 必须补证据或阻塞验收；P1 = 下一阶段核心功能；P2 = 增强或技术债 |
| Area | Cloud / Bridge / Firmware / Backend / Frontend / Hardware / Docs / QA |
| Source | 从 P0 Trace Bullet 或 P0 实现后边界推迟而来 |

## P0 后续 Issue 列表

| Linear ID | Title | Priority | Area | Status | 依赖/阻塞 | 验收标准 |
| --- | --- | --- | --- | --- | --- | --- |
| AGR-FUP-001 | 云端部署 P0 最新版本并做 smoke | P0 | Cloud / QA | Backlog | 需要确认是否允许部署、是否需要备份远端 SQLite | 云端 `/api/status`、`/api/boards`、`/api/history?board_id=A`、`/api/control-rules/soil-moisture-pump` 返回正常；前端可打开最新版 |
| AGR-FUP-002 | 现场 bridge 真实串口链路验收 | P0 | Bridge / Hardware / QA | Backlog | 需要真实 C 板串口号和现场 ED 板 | C 串口持续输出 `t/h/l/s`；`serial_bridge` 日志持续出现 `sensor >> board=A {...}`；云端 History 能看到最新真实记录；Dashboard 实时波动 |
| AGR-FUP-003 | 单板三路控制 smoke 证据 | P0 | Hardware / QA | Backlog | 需要现场连接 ED 板 | 手动 `pump/fertilizer/pest_light` 三路 on/off 均有 `ControlLog`、bridge 命令日志、ED 端响应视频或照片；施肥/灭虫按课程模拟指示验收 |
| AGR-FUP-004 | 自动浇水真实硬件验收 | P0 | Backend / Bridge / Hardware / QA | Backlog | 依赖 AGR-FUP-001/002/003；需要 auto 模式和可控测试样本 | 自动触发 `pump on/off` 必须同时有 `ControlLog`、bridge 命令、ED 水泵/继电器证据；临时调阈值 smoke 只证明控制链路，不证明真实低湿传感 |
| AGR-FUP-005 | 部署前数据库备份与回滚 SOP | P0 | Cloud / Docs | Backlog | 需要远端实际数据库路径确认 | 部署前备份 SQLite；记录恢复命令；部署后 smoke 失败时可回滚 |
| AGR-FUP-006 | 固件 IAR 编译与烧录验收记录 | P1 | Firmware / QA | Backlog | 需要 IAR/Z-Stack 工程环境 | 终端/协调器工程编译通过；烧录版本、PAN ID、信道、板卡角色记录在文档中 |
| AGR-FUP-007 | OLED P1 必做口径固化 | P1 | Product / Firmware | Backlog | 需要 OLED 驱动和 IAR 工程条件 | 文档和验收模板明确 OLED 是 P1 必做；只显示温度、空气湿度、光照相对值 |
| AGR-FUP-008 | OLED 驱动启用与现场显示 | P1 | Firmware / Hardware | Backlog | 依赖 AGR-FUP-007；需要 `HalOled.h`、SPI 引脚和 IAR include path | ED OLED 显示温度、空气湿度、光照相对值；有现场照片或视频 |
| AGR-FUP-009 | 流水灯报警现场验收 | P1 | Firmware / Hardware / QA | Ready | 后端已有 `BLEALARM1/BLEALARM0`，ED 固件已有流水灯代码 | 异常触发后 ED 流水灯可见；恢复/确认后停止；不覆盖 `pump` 继电器，不误改施肥/灭虫状态 |
| AGR-FUP-010 | 流水灯报警烧录记录 | P1 | Firmware / QA | Backlog | 依赖 IAR/Z-Stack 工程环境 | 记录烧录版本、触发条件、现场视频/照片路径 |
| AGR-FUP-011 | 光照 GL5516/P0.7 ADC 真实采集决策 | P1 | Product / Firmware / Hardware | Ready | 已知板载 GL5516 接 P0.7；当前未现场 smoke | 明确路线为 GL5516/P0.7 ADC；单位口径为相对光照值，不再宣称 lux；未 smoke 前标待验收 |
| AGR-FUP-012 | 光照 ADC 固件接入 | P1 | Firmware / Hardware | Blocked | 依赖 AGR-FUP-011；需要 CC2530 ADC API/寄存器实现和现场验证 | `l:` 来自 ED 的 P0.7 ADC 相对值；后端字段来源改为 `measured_firmware`；Dashboard/OLED 看到遮光/照光波动 |
| AGR-FUP-013 | 土壤湿度模拟口径固化 | P1 | Product / Firmware / Docs | Ready | 当前 `soil_moisture` 是固件模拟值 | 文档、字段目录、答辩口径统一为课程模拟值；自动浇水用该模拟值演示 |
| AGR-FUP-014 | 模拟土壤低湿自动浇水复验 | P1 | Firmware / Backend / Hardware / QA | Backlog | 依赖现场单板 smoke | 用模拟低湿或调阈值触发自动浇水，现场可复验 |
| AGR-FUP-015 | 模型字段公式和范围确认 | P1 | Product / Backend / Data | Ready | 课程设计允许模拟/模型字段 | 明确 CO2、soil_ec、soil_tds、soil_fertility、infrared 的单位、范围、公式版本；写入 PRD 和字段目录 |
| AGR-FUP-016 | CO2/EC/TDS/肥力/红外 simulated facts | P1 | Backend / Data | Done | 课程设计允许模拟/模型字段 | `/api/history` 和 WS facts 中模型字段有值、来源、`formula_version`；不再 pending |
| AGR-FUP-017 | 土壤模型字段持久化策略 | P1 | Backend / DB | Blocked | 依赖 AGR-FUP-015/016 | 明确存 raw、存 computed，还是两者都存；历史回放和导出可解释 |
| AGR-FUP-018 | 土壤肥力阈值开放配置 | P1 | Backend / Frontend | Done | 已接入 `soil_fertility` 默认阈值 | Settings 可配置肥力阈值；History/AlarmLog 支持肥力异常；测试覆盖模型字段和肥力告警 |
| AGR-FUP-019 | CO2 模拟字段接入 | P1 | Backend / Frontend | Done | 由后端 `compute_model_values()` v1 生成 | CO2 以 `simulated_backend` 输出，Dashboard/History/CSV 可查看和追溯 |
| AGR-FUP-020 | 红外模拟事件接入 | P1 | Backend / Frontend | Done | 由后端 `compute_model_values()` v1 生成 | 红外以 `simulated_backend` 输出，Dashboard/History/CSV 可查看和追溯 |
| AGR-FUP-021 | TDS/EC 模型接入 | P1 | Backend / Frontend | Backlog | 依赖 AGR-FUP-015 | EC/TDS 以 `computed_backend` 输出，TDS 可由 EC 换算，保留公式版本 |
| AGR-FUP-022 | 模型字段历史与告警联动 | P1 | Backend / Frontend | Backlog | 依赖 AGR-FUP-016/019/020/021 | 后端 facts、历史、阈值、告警和 CSV 导出都包含模型字段 |
| AGR-FUP-023 | 告警确认/恢复工作流 | P1 | Backend / Frontend | Backlog | 当前 AlarmLog 有来源追溯，但没有处理状态接口 | 增加告警状态、确认/恢复接口、操作人/时间；AlarmLog 页面按钮真正调用后端 |
| AGR-FUP-024 | 告警摘要统计口径测试 | P1 | Backend / QA | Backlog | 当前已有 summary 接口，但统计口径测试不足 | `/api/alarms/summary` 有单元/接口测试覆盖真实/测试、字段类型、时间范围 |
| AGR-FUP-025 | 阈值接口完整测试与校验 | P1 | Backend / QA | Backlog | P0 主要覆盖自动浇水；`GET/PUT /api/thresholds` 仍缺完整校验测试 | 覆盖创建、更新、未知字段、非法范围、min > max、pending 字段不可配置 |
| AGR-FUP-026 | 前端 WebSocket 环境变量 fallback | P1 | Frontend / Deploy | Backlog | 当前生产 env 依赖外部配置；历史曾有 `undefined/ws/data` 风险 | 未配置 `VITE_WS_BASE` 时能从 `window.location` 或 API base 推导；build 通过 |
| AGR-FUP-027 | 板卡在线状态与测试注入边界复验 | P1 | Backend / Frontend / QA | Backlog | P0 决策为测试注入不改变真实 online | 注入测试样本后 Dashboard 当前值可变但 board online 不被伪造；前端有测试标识 |
| AGR-FUP-028 | 多板 board_id 绑定与管理页 | P2 | Backend / Frontend / Bridge | Backlog | 当前已有多板路由，但完整绑定/命名管理未做 | 前端可管理 board name/location/enabled；bridge 注入和固件 id 策略明确；历史/控制可按板筛选 |
| AGR-FUP-029 | 施肥和灭虫模拟执行器验收 | P1 | Hardware / Docs / QA | Backlog | 课程设计按单板 LED/指示模拟 | 记录三路 on/off 的前端、bridge、ED 指示证据，不再要求真实施肥泵/灭虫灯负载 |
| AGR-FUP-030 | 固件旧“天窗/window”命名清理 | P2 | Firmware / Docs | Backlog | 第三路产品语义已是 `pest_light`，但固件局部变量/注释可能仍有旧命名 | 固件变量、注释、README 与 `pest_light` 语义一致；不改变底层 `BLEGLED3` 兼容命令 |
| AGR-FUP-031 | 云端 systemd/bridge 运行形态决策 | P1 | Cloud / Bridge / Docs | Backlog | 云端只跑 FastAPI；bridge 应跑在接串口机器 | 明确 bridge 是现场电脑常驻、边缘机常驻，还是另做服务；写出启动/重连/SOP |
| AGR-FUP-032 | 现场验收记录模板 | P1 | Docs / QA | Backlog | 需要稳定沉淀证据，不只聊天说明 | 模板包含命令、时间、负责人、截图/视频路径、curl 输出、bridge 日志、失败处理 |
| AGR-FUP-033 | Vite chunk 体积警告处理 | P2 | Frontend | Backlog | `npm run build` 通过但提示 chunk > 500 kB | 按需 code split 或调整 chunk limit；不影响功能验收 |
| AGR-FUP-034 | 生产 Secret 与配置硬化 | P2 | Backend / Deploy | Backlog | `SECRET_KEY` 仍有默认值；部署安全不是 P0 范围 | 生产从环境变量读取 secret；缺失时给明确提示；不把密钥写进代码 |

## 按 Trace Bullet 反查

### Trace Bullet 1：温度、湿度、光照 OLED 显示并向上位机发送

P0 已完成：

- 云端上位机实时/历史链路的软件合同。
- 温度、空气湿度真实 DHT11；光照推荐走 ED 板 GL5516/P0.7 ADC 相对值，未 smoke 前仍标待验收。

仍未完成：

- AGR-FUP-001：云端 smoke。
- AGR-FUP-002：现场 bridge 真实串口链路。
- AGR-FUP-006：固件编译/烧录验收。
- AGR-FUP-007/008：OLED P1 必做和启用。
- AGR-FUP-011/012：GL5516/P0.7 相对光照 ADC。

### Trace Bullet 2：异常流水灯报警，湿度不够自动浇水

P0 已完成：

- 土壤低湿自动浇水后端规则。
- 安全关泵、冷却、ControlLog reason。
- 测试注入可触发测试告警和自动浇水测试。

仍未完成：

- AGR-FUP-004：单板自动浇水 smoke。
- AGR-FUP-009/010：ED 流水灯烧录和现场验收。
- AGR-FUP-013/014：土壤湿度模拟口径和模拟低湿复验。
- AGR-FUP-023/024：告警处理工作流和统计测试。

### Trace Bullet 3：手动开关浇水、施肥、灭虫灯

P0 已完成：

- `pump/fertilizer/pest_light` 设备语义和后端校验。
- 多板控制不 fallback。
- 前端文案改为“施肥泵/指示”“灭虫灯/指示”。

仍未完成：

- AGR-FUP-003：现场硬件控制证据。
- AGR-FUP-029：施肥和灭虫按课程模拟执行器完成现场证据。
- AGR-FUP-030：固件旧命名清理。

### Trace Bullet 4：上位机查看 CO2、土壤湿度、TDS/电导率、红外；配置阈值；历史

P0 已完成：

- available 字段实时/历史/告警/测试来源追溯。
- `soil_moisture` 阈值和自动浇水规则配置。
- History/AlarmLog 真实/测试过滤。

仍未完成：

- AGR-FUP-015/016/017/018：模型字段公式、EC/TDS/肥力和肥力阈值。
- AGR-FUP-019：CO2 模拟字段已接入。
- AGR-FUP-020：红外模拟事件已接入。
- AGR-FUP-021/022：TDS/EC 与模型字段历史/告警联动。
- AGR-FUP-025：阈值接口完整校验。

## 建议进入 Linear 的首批队列

先不要一次全开。建议首批只放 10 个，仍然只围绕 4 条 Trace Bullet：

| 顺序 | Linear ID | 原因 |
| --- | --- | --- |
| 1 | AGR-FUP-005 | 部署前必须先有备份/回滚 |
| 2 | AGR-FUP-001 | 云端是否是最新版要先证实 |
| 3 | AGR-FUP-002 | 真实串口链路是后续硬件验收基础 |
| 4 | AGR-FUP-003 | 三路控制必须有板端证据 |
| 5 | AGR-FUP-004 | P0 自动浇水要从软件闭环升级为硬件闭环 |
| 6 | AGR-FUP-032 | 每次现场验收需要固定模板 |
| 7 | AGR-FUP-007 | OLED 已纳入 P1 必做，需先固化驱动和显示口径 |
| 8 | AGR-FUP-011 | 光照要先从 lux 口径切到 GL5516/P0.7 相对值 |
| 9 | AGR-FUP-009 | 流水灯需要做 ED 板现场验收 |
| 10 | AGR-FUP-015 | 模型字段都依赖公式和范围 |

## 暂不进入首批的事项

这些不代表不重要，只是不该抢在现场链路验收之前：

- Vite chunk：AGR-FUP-033。
- Secret/config hardening：AGR-FUP-034。
- 多板管理页：AGR-FUP-028。
