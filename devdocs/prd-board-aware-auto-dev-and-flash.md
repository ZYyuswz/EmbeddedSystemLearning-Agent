# PRD：基于板卡型号的自动化代码生成与烧录运行系统

## 1. 需求摘要

目标是建设一个“板卡感知开发助手”能力：用户连接外接板卡后，系统可在用户提供或未提供型号的情况下完成板卡识别，自动检索官网资料（参数、芯片手册、官方 SDK/示例、烧录说明），再根据用户功能需求生成可编译代码、执行烧录并运行验证，最终返回可追溯的执行结果与问题定位信息。

本期范围按“嵌入式系统设计与学习 AGENT”拆分后，明确聚焦两项：
- 第 1 点中的 `c. 嵌入式系统学习 AGENT`（主线能力）。
- 第 2 点 `AGENT 评估与优化`（必须完成：小项目原型、可行性评估、性能评估、改进设想）。

核心价值：
- 降低嵌入式开发从“资料查找 -> 环境配置 -> 代码生成 -> 烧录调试”的门槛与耗时。
- 提供“可审计、可回滚、可复现”的自动化流程，而不是不可控的一次性脚本执行。
- 在存在高风险动作（烧录、擦除、复位）时，引入强制确认与安全门禁。

## 2. 范围定义（In Scope / Out of Scope）

### In Scope
- AGENT 研发范围：
- 本期实现“嵌入式系统学习 AGENT”，支持基于板卡信息与需求生成可执行学习路径、示例工程与实验步骤。
- 板卡识别：
- 用户显式输入板卡型号（如 `STM32F103C8T6-BluePill`）时直接使用。
- 用户未输入型号时，自动通过 USB 设备信息（VID/PID、串口描述、调试探针信息）与候选库匹配并给出候选结果。
- 官网资料检索：
- 按“厂商官网 -> 官方文档站 -> 官方代码仓库（若为厂商官方）”优先级抓取资料。
- 提取结构化参数：MCU/SoC、Flash/RAM、时钟、引脚复用、外设能力、供电、烧录工具、支持框架。
- 需求到代码：
- 接收用户任务（如“采集温湿度并每秒串口输出”），生成工程模板与核心业务代码。
- 输出构建脚本、依赖清单、烧录命令、运行验证脚本。
- 烧录与运行：
- 根据板卡与工具链适配（如串口下载/JTAG/SWD）执行烧录。
- 执行基础运行验收（串口日志、心跳灯、返回码、超时检测）。
- AGENT 评估与优化：
- 创建至少 1 个小项目原型，并按 AGENT 给出的方案在华为、飞腾等开发板之一完成搭建与运行。
- 输出可行性评估（能否落地、成本、稳定性）与 AGENT 性能评估（正确率、成功率、耗时、人工介入次数）。
- 基于评估结果输出可执行改进建议与优先级。
- 结果回传：
- 返回执行日志、产物路径、版本信息、失败定位与可重试建议。

### Out of Scope
- 非官方来源资料作为主依据（论坛帖子、个人博客）默认不作为最终参数来源。
- 完整 IDE 图形化集成（仅提供 CLI/服务能力）。
- 硬件电路设计与原理图自动生成。
- 远程硬件农场调度（本期只覆盖本机连接设备）。
- 对存在安全锁或量产加密流程的芯片进行绕过操作。

## 3. 接口定义（OpenAPI 风格草案）

### 3.1 识别板卡

- `POST /api/v1/boards/detect`
- 鉴权：`Bearer Token`
- 请求体：
```json
{
  "userProvidedModel": "optional string",
  "scanPorts": true,
  "scanUsb": true
}
```
- 响应体：
```json
{
  "requestId": "req_xxx",
  "resolvedBoard": {
    "vendor": "ST",
    "model": "STM32F103C8T6-BluePill",
    "confidence": 0.93
  },
  "candidates": [
    {
      "vendor": "ST",
      "model": "STM32F103C8T6-BluePill",
      "confidence": 0.93
    }
  ],
  "probeInfo": {
    "usbVid": "0483",
    "usbPid": "3748",
    "serialPorts": ["/dev/tty.usbmodem1101"]
  }
}
```
- 错误码：
- `BOARD_DETECT_EMPTY`: 未发现可识别设备
- `BOARD_DETECT_AMBIGUOUS`: 候选冲突需人工确认
- `BOARD_DETECT_PERMISSION_DENIED`: 无设备访问权限

### 3.2 拉取官方资料与参数

- `POST /api/v1/boards/knowledge/sync`
- 鉴权：`Bearer Token`
- 请求体：
```json
{
  "boardModel": "STM32F103C8T6-BluePill",
  "vendorHint": "ST",
  "forceRefresh": false
}
```
- 响应体：
```json
{
  "knowledgeId": "kb_xxx",
  "sources": [
    {
      "url": "https://...",
      "sourceType": "official_docs",
      "fetchedAt": "2026-04-12T12:00:00Z"
    }
  ],
  "specSummary": {
    "mcu": "STM32F103C8T6",
    "flashKB": 64,
    "ramKB": 20,
    "supportedProgrammers": ["stlink", "uart_bootloader"]
  }
}
```
- 错误码：
- `OFFICIAL_SOURCE_NOT_FOUND`
- `OFFICIAL_SOURCE_UNREACHABLE`
- `SPEC_PARSE_FAILED`

### 3.3 生成代码与工程

- `POST /api/v1/projects/generate`
- 鉴权：`Bearer Token`
- 请求体：
```json
{
  "boardModel": "STM32F103C8T6-BluePill",
  "knowledgeId": "kb_xxx",
  "requirementText": "每秒读取温湿度并通过串口输出",
  "language": "c",
  "frameworkPreference": "auto"
}
```
- 响应体：
```json
{
  "projectId": "prj_xxx",
  "workspacePath": "/workspace/projects/prj_xxx",
  "buildCommand": "make all",
  "flashCommand": "st-flash write build/app.bin 0x8000000",
  "runCheckCommand": "python scripts/check_serial.py --timeout 15"
}
```
- 错误码：
- `GEN_REQUIREMENT_INVALID`
- `GEN_TEMPLATE_NOT_SUPPORTED`
- `GEN_DEPENDENCY_RESOLVE_FAILED`

### 3.4 编译与烧录

- `POST /api/v1/projects/{projectId}/flash`
- 鉴权：`Bearer Token`
- 请求体：
```json
{
  "port": "/dev/tty.usbmodem1101",
  "programmer": "stlink",
  "eraseMode": "chip",
  "dryRun": false,
  "userConfirmedRisk": true
}
```
- 响应体：
```json
{
  "taskId": "task_xxx",
  "status": "running",
  "startedAt": "2026-04-12T12:05:00Z"
}
```
- 错误码：
- `FLASH_CONFIRMATION_REQUIRED`
- `FLASH_TOOL_NOT_FOUND`
- `FLASH_DEVICE_BUSY`
- `FLASH_FAILED`

### 3.5 运行验证与日志查询

- `POST /api/v1/projects/{projectId}/run-check`
- `GET /api/v1/tasks/{taskId}`
- 鉴权：`Bearer Token`
- 请求体（run-check）：
```json
{
  "checkProfile": "serial_heartbeat",
  "timeoutSec": 20
}
```
- 响应体（task 查询）：
```json
{
  "taskId": "task_xxx",
  "status": "success",
  "logs": [
    "编译成功",
    "烧录完成",
    "串口收到 20 条数据"
  ],
  "artifacts": {
    "binary": "/workspace/projects/prj_xxx/build/app.bin",
    "report": "/workspace/projects/prj_xxx/reports/run-check.json"
  }
}
```
- 错误码：
- `RUN_CHECK_TIMEOUT`
- `RUN_CHECK_NO_SIGNAL`
- `RUN_CHECK_PROFILE_INVALID`

### 3.6 AGENT 评估与优化

- `POST /api/v1/evaluations/prototype/run`
- 鉴权：`Bearer Token`
- 请求体：
```json
{
  "projectId": "prj_xxx",
  "boardPlatform": "huawei|phytium|other",
  "scenarioName": "sensor_monitor_demo",
  "acceptanceChecklist": ["boot_ok", "data_output_ok", "recover_ok"]
}
```
- 响应体：
```json
{
  "evaluationTaskId": "eval_xxx",
  "status": "running"
}
```
- 错误码：
- `EVAL_BOARD_NOT_READY`
- `EVAL_SCENARIO_INVALID`

- `POST /api/v1/evaluations/reports/generate`
- 鉴权：`Bearer Token`
- 请求体：
```json
{
  "evaluationTaskId": "eval_xxx",
  "includeImprovementProposal": true
}
```
- 响应体：
```json
{
  "reportId": "report_xxx",
  "feasibility": "high",
  "agentScore": 82,
  "improvements": [
    "增加板卡候选消歧步骤",
    "优化烧录失败自动诊断策略"
  ]
}
```

## 4. 数据模型草案

### 4.1 BoardProfile

- `id`：string，必填，主键
- `vendor`：string，必填，如 `ST` / `Espressif`
- `model`：string，必填，唯一键之一
- `mcuSoc`：string，必填
- `flashKB`：integer，非必填，默认 `null`
- `ramKB`：integer，非必填，默认 `null`
- `programmers`：string[]，必填，默认 `[]`
- `frameworks`：string[]，必填，默认 `[]`
- `pinMap`：object，非必填，默认 `{}`
- `officialSources`：SourceRef[]，必填，默认 `[]`
- `updatedAt`：datetime，必填

### 4.2 SourceRef

- `url`：string，必填，需满足 URL 格式
- `sourceType`：enum，必填：`official_site` / `official_docs` / `official_repo`
- `versionTag`：string，非必填
- `fetchedAt`：datetime，必填
- `checksum`：string，非必填

### 4.3 ProjectTask

- `taskId`：string，必填，主键
- `projectId`：string，必填，索引
- `taskType`：enum，必填：`generate` / `build` / `flash` / `run_check`
- `status`：enum，必填：`pending` / `running` / `success` / `failed` / `cancelled`
- `command`：string，必填
- `logs`：string[]，必填，默认 `[]`
- `errorCode`：string，非必填
- `startedAt`：datetime，非必填
- `endedAt`：datetime，非必填

### 4.4 SafetyPolicy

- `boardModel`：string，必填
- `requiresConfirmBeforeFlash`：boolean，必填，默认 `true`
- `allowedProgrammers`：string[]，必填
- `forbiddenCommands`：string[]，必填，默认 `[]`
- `maxFlashRetry`：integer，必填，默认 `1`

### 4.5 AgentEvaluationReport

- `reportId`：string，必填，主键
- `evaluationTaskId`：string，必填，索引
- `projectId`：string，必填
- `boardPlatform`：enum，必填：`huawei` / `phytium` / `other`
- `feasibilityLevel`：enum，必填：`high` / `medium` / `low`
- `metrics`：object，必填，含 `taskSuccessRate`、`avgLeadTimeSec`、`manualInterventionCount`、`specAccuracyScore`
- `findings`：string[]，必填，默认 `[]`
- `improvementProposals`：string[]，必填，默认 `[]`
- `createdAt`：datetime，必填

## 5. 前端影响面说明

- 页面与路由：
- 新增“板卡助手”主页面：设备识别、需求输入、生成结果、执行日志四段式布局。
- 新增任务详情路由：`/board-assistant/tasks/:taskId`。
- 状态管理：
- 需要维护 `boardDetectState`、`knowledgeSyncState`、`projectGenerationState`、`flashTaskState`。
- 新增 `evaluationState`，用于原型评估任务进度、评分结果、改进建议展示。
- 支持任务轮询与断线重连恢复。
- 交互与校验：
- 当识别置信度低于阈值（建议 0.8）时，必须弹出候选确认，不允许直接烧录。
- 执行 `flash` 前必须二次确认（展示板卡型号、端口、烧录器、擦除模式）。
- 用户需求文本为空时禁止生成任务。
- 兼容策略：
- 首版支持桌面端优先（外设连接能力更稳定）。
- 浏览器不支持本地设备扫描时，引导用户手动选择端口与板卡型号。
- 新增评估结果页，展示可行性等级、关键指标雷达图、改进建议列表与导出报告按钮。

## 6. 验收标准（Given-When-Then）

1. 正常识别与生成
- Given：用户已连接可识别板卡且网络可访问官方资料
- When：用户输入开发需求并发起生成
- Then：系统返回可编译工程、构建命令与烧录命令，状态为成功

2. 未提供型号自动识别
- Given：用户未填写型号但 USB/串口信息可读取
- When：用户点击“自动识别”
- Then：系统返回主候选与置信度；若置信度 >= 0.8 自动进入下一步，否则要求用户确认

3. 官方资料不可达
- Given：板卡型号有效，但官网/官方文档暂时不可访问
- When：用户发起资料同步
- Then：系统返回明确错误码 `OFFICIAL_SOURCE_UNREACHABLE`，并提示稍后重试，不进入生成与烧录

4. 烧录高风险确认
- Given：系统已完成编译并准备烧录
- When：用户未勾选风险确认
- Then：接口拒绝执行并返回 `FLASH_CONFIRMATION_REQUIRED`

5. 烧录后运行验证
- Given：烧录成功，运行检查配置为 `serial_heartbeat`
- When：系统执行运行验证
- Then：在超时前收到预期串口输出并标记任务成功；否则返回 `RUN_CHECK_TIMEOUT` 或 `RUN_CHECK_NO_SIGNAL`

6. 可追溯性
- Given：任一任务执行完成
- When：用户查询任务详情
- Then：可查看命令、中文日志、产物路径、错误码与时间戳

7. 学习 AGENT 主线达成
- Given：用户选择“嵌入式系统学习 AGENT”模式
- When：输入学习目标与板卡信息后发起任务
- Then：系统输出学习步骤、示例工程、实验检查点，并可执行编译与烧录

8. 评估与优化闭环达成
- Given：小项目原型已在华为或飞腾开发板完成一次端到端执行
- When：用户发起评估报告生成
- Then：系统返回可行性结论、性能指标、问题清单与改进建议

## 7. 风险与待确认项（按优先级）

### P0
- 待确认：允许自动执行到哪一步（仅生成代码，还是默认包含自动烧录）
- 影响范围：安全责任边界、默认交互流程、误操作风险

- 待确认：官方来源白名单规则（域名级/仓库组织级）
- 影响范围：参数可信度、法务与合规风险

- 待确认：评估基线指标阈值（如成功率、耗时、人工介入次数）及评分权重
- 影响范围：第 2 点“评估与优化”结论的一致性与可比性

### P1
- 待确认：首批支持板卡清单（例如 STM32/ESP32/RP2040 的具体子型号）
- 影响范围：识别算法与模板覆盖率、交付节奏

- 风险：同系列板卡硬件差异导致引脚/外设映射错误
- 影响范围：代码可运行性、烧录后行为异常

- 风险：华为/飞腾开发板资源不足或驱动环境未就绪，导致评估计划延期
- 影响范围：第 2 点原型评估进度与报告完整性

### P2
- 待确认：是否需要离线缓存官方资料与本地知识库 TTL 策略
- 影响范围：网络波动场景下可用性、文档新鲜度

- 风险：多系统环境（macOS/Linux/Windows）下串口与烧录工具行为不一致
- 影响范围：跨平台可用性与支持成本

## 8. 落盘信息

- 目标路径：`devdocs/prd-board-aware-auto-dev-and-flash.md`
- 文档版本：`v1.1`
- 产出角色：`Agent 1（需求与接口设计）`
