# Agent2 改动计划：基于板卡型号的自动化代码生成与烧录运行系统（v1）

## 1. 改动总览

基于 `devdocs/prd-board-aware-auto-dev-and-flash.md`，当前仓库从“单体 Streamlit 问答应用”扩展为“Streamlit 前端 + FastAPI 后端 + 本地任务执行与追踪”的双层架构，分两条能力线并行落地：

- 主线 A（学习 AGENT）：保留现有问答能力，并新增“板卡助手”流程入口（识别 -> 资料同步 -> 生成 -> 烧录 -> 运行验证 -> 评估报告）。
- 主线 B（评估闭环）：新增原型评估执行与报告生成链路，输出可行性、性能指标与改进建议。

约束与原则：

- Agent3 仅按本计划执行，若偏离需记录“差异原因与影响”。
- 高风险动作（flash/erase/reset）必须二次确认，后端强校验 `userConfirmedRisk`。
- 日志文本除专有名词外全部中文。
- 本期采用 SQLite 本地持久化，保证任务可追溯和可回滚。

Context7 参考（本计划涉及框架实现方式）：

- `libraryId: /fastapi/fastapi`，关键词：`APIRouter`、`Pydantic model`、`HTTPException`、`BackgroundTasks`
- `libraryId: /streamlit/streamlit`，关键词：`session_state`、`cache_data/cache_resource`、`chat_input/chat_message`、`navigation`

## 2. 文件级改动清单（表格）

| 操作 | 文件 | 模块/类/方法 | 改动目的 | 实现要点 | 需求/AC 映射 |
|---|---|---|---|---|---|
| 新增 | `backend/main.py` | `app = FastAPI()`、应用启动 | 提供后端 API 入口 | 注册 6 组路由、统一异常处理、中间件日志 | 接口 3.1~3.6，AC1~8 |
| 新增 | `backend/api/routes/boards.py` | `detect_board()`、`sync_board_knowledge()` | 实现板卡识别与官方资料同步接口 | 参数校验、错误码映射、返回 `resolvedBoard/candidates/probeInfo/specSummary` | 3.1/3.2，AC2/3 |
| 新增 | `backend/api/routes/projects.py` | `generate_project()`、`flash_project()`、`run_check()` | 实现生成/烧录/运行校验接口 | 生成任务记录；`flash` 前强校验 `userConfirmedRisk` | 3.3/3.4/3.5，AC1/4/5 |
| 新增 | `backend/api/routes/tasks.py` | `get_task_detail()` | 任务日志与状态查询 | 返回命令、中文日志、产物路径、错误码、时间戳 | 3.5，AC6 |
| 新增 | `backend/api/routes/evaluations.py` | `run_prototype_eval()`、`generate_eval_report()` | 评估执行与报告生成 | 评估任务异步执行，报告含 feasibility/agentScore/improvements | 3.6，AC8 |
| 新增 | `backend/models/schemas.py` | Pydantic 请求/响应模型 | 统一接口契约 | 对齐 PRD 字段名、默认值、枚举、可选项 | 接口与数据模型 |
| 新增 | `backend/core/errors.py` | `ErrorCode`、`AppException` | 统一业务错误码 | 固化 PRD 错误码，映射 HTTP 状态码 | 全部异常流 |
| 新增 | `backend/core/auth.py` | `require_bearer_token()` | 鉴权占位与扩展点 | 先实现静态 Token 校验，后续可替换 JWT | “Bearer Token” |
| 新增 | `backend/core/config.py` | `Settings` | 后端配置管理 | 读取 DB 路径、工具链路径、超时阈值、置信度阈值 | 运行配置 |
| 新增 | `backend/services/board_detection_service.py` | `detect()` | 设备识别核心逻辑 | 用户给定型号优先；否则走 USB/串口扫描 + 候选匹配 + 置信度排序 | 2 In Scope、AC2 |
| 新增 | `backend/services/knowledge_sync_service.py` | `sync_official_sources()` | 官方资料同步与结构化解析 | 来源优先级：官网 -> 官方文档 -> 官方仓库；失败返回标准错误码 | 2 In Scope、AC3 |
| 新增 | `backend/services/project_generation_service.py` | `generate_project()` | 需求生成可编译工程 | 写入 workspace、生成 build/flash/check 命令与脚本 | 3.3，AC1/7 |
| 新增 | `backend/services/flash_service.py` | `flash_project()` | 烧录执行与安全控制 | 二次确认门禁、dry-run 支持、重试与失败诊断 | 3.4，AC4/5 |
| 新增 | `backend/services/run_check_service.py` | `run_check()` | 运行验收执行 | 支持 `serial_heartbeat`、超时检测、日志采集 | 3.5，AC5 |
| 新增 | `backend/services/evaluation_service.py` | `run_prototype()`、`generate_report()` | 评估任务与报告 | 输出可行性等级、成功率、耗时、人工介入次数、改进建议 | 3.6，AC8 |
| 新增 | `backend/services/task_service.py` | `create_task()`、`update_task()`、`append_log()`、`get_task()` | 任务生命周期管理 | 统一任务状态机，保证可追溯性 | AC6 |
| 新增 | `backend/services/safety_service.py` | `check_flash_policy()` | 烧录安全策略 | 校验 allowedProgrammers/forbiddenCommands/maxFlashRetry | 数据模型 SafetyPolicy |
| 新增 | `backend/infrastructure/device_scanner.py` | `scan_usb()`、`scan_serial_ports()` | 设备信息采集 | 抽象 pyusb/pyserial，权限失败抛 `BOARD_DETECT_PERMISSION_DENIED` | 3.1，AC2 |
| 新增 | `backend/infrastructure/official_source_client.py` | `fetch_sources()`、`parse_specs()` | 官方资料抓取与解析 | 限定白名单域名，网络失败与解析失败明确区分 | 3.2，风险 P0 |
| 新增 | `backend/repositories/sqlite_repo.py` | Repository 类 | SQLite 读写抽象 | BoardProfile/SourceRef/ProjectTask/SafetyPolicy/AgentEvaluationReport 持久化 | 数据模型 4.1~4.5 |
| 新增 | `backend/repositories/schema.sql` | DDL | 初始化数据库 | 建表与索引脚本，支持重复执行幂等 | 数据层 |
| 新增 | `backend/worker/executor.py` | `run_command()`、`run_task_async()` | 命令执行与日志回传 | subprocess 包装、超时与退出码处理、日志入库 | 任务执行链路 |
| 新增 | `frontend/board_assistant_page.py` | `render_board_assistant_page()` | 新增“板卡助手”主页面 | 四段式布局：识别/需求输入/执行控制/日志 | 前端影响面 |
| 新增 | `frontend/task_detail_page.py` | `render_task_detail_page(task_id)` | 任务详情页 | 路由 `/board-assistant/tasks/:taskId` 等价实现（Streamlit query params） | 前端影响面 |
| 新增 | `frontend/api_client.py` | `BackendApiClient` | 前端调用后端 API | 封装 token/header、错误码翻译、轮询 | 接口消费 |
| 修改 | `webui.py` | `main()`、侧栏/页面切换 | 集成旧问答与新板卡助手 | 新增导航：“学习问答”/“板卡助手”/“评估结果” | AC7/8 |
| 修改 | `login.py` | 登录后跳转逻辑 | 保持入口不变并支持新页面 | 登录态与 token 注入 `st.session_state` | 鉴权链路 |
| 修改 | `requirements.txt` | 依赖清单 | 支持新后端能力 | 新增 `fastapi`、`uvicorn`、`pydantic`、`pyserial`、`pyusb`（按 Agent3 版本锁定策略） | 构建发布影响 |
| 新增 | `scripts/start_backend.py` | 启动脚本 | 统一本地联调入口 | 启动 FastAPI，供 Streamlit 调用 | 联调顺序 |
| 新增 | `scripts/check_serial.py` | 运行校验脚本 | `serial_heartbeat` 检查 | 参数化端口、超时、关键字计数 | 3.5 |
| 新增 | `docs/board-assistant-api.md` | API 文档 | 对齐接口消费与调试 | 记录字段、错误码、示例请求 | 前后端契约 |
| 修改 | `README.md` | 运行说明 | 增加前后端双进程启动说明 | 本地运行、环境变量、常见问题 | 交付可用性 |
| 修改 | `prompts/sirius-api.postman.json` | Postman 集合 | 同步新增/变更接口 | 新增 3.1~3.6 接口请求与示例响应 | 仓库强制规则 |

## 3. 关键逻辑伪代码

### 3.1 板卡识别 -> 资料同步 -> 代码生成主链路

```python
def create_project_flow(input_payload, token):
    require_auth(token)

    # 1) detect
    detect_result = board_detection_service.detect(
        user_model=input_payload.userProvidedModel,
        scan_usb=input_payload.scanUsb,
        scan_ports=input_payload.scanPorts,
    )
    if detect_result.confidence < settings.detect_confidence_threshold:
        return {"status": "need_confirm", "candidates": detect_result.candidates}

    # 2) knowledge sync
    kb = knowledge_sync_service.sync_official_sources(
        board_model=detect_result.resolved_model,
        vendor_hint=detect_result.vendor,
        force_refresh=False,
    )

    # 3) generate project
    generation = project_generation_service.generate_project(
        board_model=detect_result.resolved_model,
        knowledge_id=kb.knowledge_id,
        requirement_text=input_payload.requirementText,
        language=input_payload.language,
        framework_preference=input_payload.frameworkPreference,
    )
    return generation
```

### 3.2 烧录与运行验证（强制门禁）

```python
def flash_and_check(project_id, flash_req):
    task = task_service.create_task(project_id=project_id, task_type="flash")

    if not flash_req.userConfirmedRisk:
        raise AppException("FLASH_CONFIRMATION_REQUIRED")

    safety_service.check_flash_policy(
        board_model=project.board_model,
        programmer=flash_req.programmer,
        erase_mode=flash_req.eraseMode,
    )

    flash_result = flash_service.flash_project(project, flash_req, task.task_id)
    if not flash_result.ok:
        task_service.fail(task.task_id, error_code="FLASH_FAILED")
        return

    check_task = task_service.create_task(project_id=project_id, task_type="run_check")
    check_result = run_check_service.run_check(project, profile="serial_heartbeat", timeout_sec=20)
    task_service.finish(check_task.task_id, check_result)
```

### 3.3 评估报告生成

```python
def generate_eval_report(evaluation_task_id, include_improvement=True):
    raw = evaluation_service.collect_metrics(evaluation_task_id)
    feasibility = score_to_feasibility(raw.success_rate, raw.lead_time, raw.manual_count)
    report = {
        "agentScore": compute_agent_score(raw),
        "feasibility": feasibility,
        "improvements": evaluation_service.propose_improvements(raw) if include_improvement else [],
    }
    repo.save_evaluation_report(report)
    return report
```

### 3.4 前端状态机（Streamlit）

```python
state = {
    "boardDetectState": "idle|running|success|failed|need_confirm",
    "knowledgeSyncState": "idle|running|success|failed",
    "projectGenerationState": "idle|running|success|failed",
    "flashTaskState": "idle|running|success|failed",
    "evaluationState": "idle|running|success|failed",
}

on_click_detect() -> call /boards/detect -> update boardDetectState
on_click_sync() -> call /boards/knowledge/sync -> update knowledgeSyncState
on_click_generate() -> call /projects/generate -> update projectGenerationState
on_click_flash() -> modal_confirm -> call /projects/{id}/flash -> poll /tasks/{taskId}
on_click_eval() -> call /evaluations/prototype/run -> poll -> call /evaluations/reports/generate
```

## 4. 数据层与接口变更计划

### 4.1 数据层变更

- 类型：新增 SQLite 持久化（有数据层改动，非“无”）
- 存储文件建议：`data/board_assistant.db`

DDL（由 `backend/repositories/schema.sql` 落地，Agent3 按 SQL 实现）：

1. `board_profiles`：对应 `BoardProfile`，唯一键 `(vendor, model)`
2. `source_refs`：关联 `board_profile_id`，索引 `fetched_at`
3. `project_tasks`：对应 `ProjectTask`，索引 `(project_id, task_type, status)`
4. `safety_policies`：对应 `SafetyPolicy`，主键 `board_model`
5. `evaluation_reports`：对应 `AgentEvaluationReport`，索引 `evaluation_task_id`

迁移顺序：

1. 首次启动执行 `schema.sql`
2. 写入默认 `safety_policies`
3. 接口层切换到 Repository 访问

兼容策略：

- 保留现有 `tmp_data/user_credentials.json` 登录机制，不迁移用户体系。
- 新数据独立入库，不破坏现有知识库检索逻辑。

### 4.2 后端接口变更

- 新增接口：`/api/v1/boards/detect`
- 新增接口：`/api/v1/boards/knowledge/sync`
- 新增接口：`/api/v1/projects/generate`
- 新增接口：`/api/v1/projects/{projectId}/flash`
- 新增接口：`/api/v1/projects/{projectId}/run-check`
- 新增接口：`/api/v1/tasks/{taskId}`
- 新增接口：`/api/v1/evaluations/prototype/run`
- 新增接口：`/api/v1/evaluations/reports/generate`

鉴权：

- 统一 `Authorization: Bearer <token>`，缺失或无效返回 401。

错误码：

- 严格对齐 PRD 中定义，不新增未登记错误码；新增内部错误需映射为通用 `*_FAILED`。

### 4.3 前端改动计划

- 页面：
  - 现有问答页保留。
  - 新增“板卡助手主页面”：设备识别、需求输入、生成结果、执行日志四段式。
  - 新增“评估结果页”：可行性等级、指标可视化、改进建议、导出按钮。
  - 新增“任务详情页”（通过 query params 映射任务 ID）。
- 状态：
  - `boardDetectState`
  - `knowledgeSyncState`
  - `projectGenerationState`
  - `flashTaskState`
  - `evaluationState`
- 交互：
  - 置信度 < 0.8 强制候选确认
  - flash 前二次确认（型号/端口/烧录器/擦除模式）
  - 空需求禁用“生成”
  - 任务轮询 + 断线重连恢复

## 5. 实施步骤（Step-by-step）

1. 建立基础骨架：新增 `backend/` 与 `frontend/` 目录、配置模块、错误码与鉴权中间件。
2. 落地数据层：实现 SQLite schema + repository + 默认安全策略初始化。
3. 实现板卡能力：`detect` 与 `knowledge/sync` 两个接口和服务。
4. 实现工程生成能力：`projects/generate` 接口 + workspace 产物生成。
5. 实现任务与执行引擎：命令执行器、任务状态机、日志回写。
6. 实现高风险链路：`flash` + `run-check` + 强制确认门禁。
7. 实现评估闭环：原型评估任务、报告生成接口、评分与改进建议输出。
8. 实现前端页面：将 `webui.py` 接入“问答 + 板卡助手 + 评估”导航与状态机。
9. 联调顺序：
   1) `detect -> sync`  
   2) `generate -> flash(dryRun) -> run-check`  
   3) `evaluation/run -> report/generate`
10. 文档与交付：更新 `README.md`、`docs/board-assistant-api.md`、`prompts/sirius-api.postman.json`。

## 6. 风险、回滚与兼容策略

主要风险：

- P0：默认自动化深度不明确（生成后是否默认烧录）
- P0：官方来源白名单不明确导致可信度/合规风险
- P1：板卡同系列差异导致模板或引脚映射错误
- P1：华为/飞腾板卡环境未就绪导致评估延期
- P2：多系统工具链差异导致 flash 命令不稳定

风险缓解：

- 将自动化默认策略设为“生成完成即停”，烧录必须显式触发 + 二次确认。
- 首版启用域名白名单配置，记录每条来源 URL 与抓取时间戳。
- 模板按 `boardModel + toolchain` 分层，低置信度强制人工确认。
- 对 flash/run-check 提供 dry-run 与重试建议，不直接重复危险操作。

回滚点：

1. 回滚前端：隐藏“板卡助手”入口，保留原问答功能。
2. 回滚后端：停用 `backend/` 进程，前端切回仅本地 RAG 模式。
3. 回滚数据：保留 `data/board_assistant.db.bak`，异常时切回备份。

兼容策略：

- 不移除现有 `login.py + webui.py` 路径，保持原启动命令可用。
- 新功能以独立模块增量接入，确保老功能可单独运行。

## 7. 测试关注点（前端/后端）

前端测试重点：

- 页面流转：识别 -> 同步 -> 生成 -> 烧录确认 -> 运行校验 -> 评估结果
- 状态机正确性：失败重试、断线恢复、轮询终止条件
- 表单校验：空需求禁用、低置信度候选确认、flash 二次确认必填
- 接口映射：错误码展示与用户提示一致

后端测试重点：

- 鉴权：缺失/错误 Token 拒绝访问
- 接口契约：请求校验、响应字段、错误码与 PRD 对齐
- 任务状态机：`pending/running/success/failed/cancelled` 转移合法性
- 命令执行：超时、非零退出码、日志完整性、产物路径落盘
- 安全策略：`FLASH_CONFIRMATION_REQUIRED` 与 `allowedProgrammers` 生效
- 评估报告：指标计算正确、改进建议可生成、报告可追溯

建议 QA 最低自动化命令（供 Agent4）：

- 后端：`pytest backend/tests -q`
- 前端（若补充 UI 自动化）：`pytest frontend/tests -q`
- 冒烟：`python scripts/start_backend.py` + `python -m streamlit run login.py`

## 8. 落盘信息

- 目标路径：`.ai-workspace/agent2-plan-board-aware-auto-dev-and-flash-v1.md`
- 计划版本：`v1`
- 产出角色：`Agent 2（代码改动规划）`
- 上游输入：`devdocs/prd-board-aware-auto-dev-and-flash.md`
- 供下游执行：`Agent 3`

## 9. `LATEST.md` 更新信息

- 目标路径：`.ai-workspace/LATEST.md`
- 指向内容：`agent2-plan-board-aware-auto-dev-and-flash-v1.md`
- 解析规则：Agent3 读取该文件首行文件名并在 `.ai-workspace/` 下定位计划文件执行
