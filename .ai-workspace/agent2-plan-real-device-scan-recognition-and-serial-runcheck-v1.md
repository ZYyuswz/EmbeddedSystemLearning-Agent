# Agent2 改动计划：真实设备扫描、融合识别与真实串口运行校验（v1）

## 1. 改动总览

基于 `devdocs/prd-real-device-scan-recognition-and-serial-runcheck.md`，本次改动目标是把当前后端与前端中的占位能力替换为真实可执行能力，重点消除以下 Mock/硬编码：

- `backend/infrastructure/device_scanner.py` 当前固定返回 `VID=0483 PID=3748` 与 `"/dev/tty.usbmodem1101"`。
- `backend/services/board_detection_service.py` 当前主要依赖硬编码 `MODEL_MAP`，缺少多信号融合评分与解释输出。
- `backend/services/run_check_service.py` 当前仅执行命令并返回固定“通过”文案，不做真实串口读写与关键字断言。
- `frontend/board_assistant_page.py` 当前烧录端口和运行校验配置均为硬编码，未体现 `needConfirm` 的完整二次识别闭环。

本计划输出供 Agent3 直接执行，不允许引入 mock 占位路径。所有日志文本（除专有名词）保持中文。

Context7 调研依据：

- `libraryId`: `/pyserial/pyserial`
  - 查询关键词：`list_ports.comports attributes vid pid serial_number location manufacturer product interface`
  - 查询关键词：`Serial timeout write_timeout readline reset_input_buffer reset_output_buffer`
- `libraryId`: `/fastapi/fastapi`
  - 查询关键词：`APIRouter POST request body response_model validation`

关键结论（用于本计划约束）：

- `serial.tools.list_ports.comports()` 可直接提供识别所需扩展字段（`vid/pid/serial_number/location/manufacturer/product/interface`），是串口枚举主数据源。
- `serial.Serial` 支持 `timeout/write_timeout/readline` 与输入输出缓冲区清理，可实现“真实串口探测 + 超时控制 + 关键字断言”。
- FastAPI 路由保持“Pydantic 请求模型 + `response_model` 输出约束”的现有风格即可满足接口演进。

## 2. 文件级改动清单（表格）

| 操作 | 文件 | 模块/类/方法 | 改动目的 | 实现要点 | PRD/AC 映射 |
|---|---|---|---|---|---|
| 修改 | `backend/infrastructure/device_scanner.py` | `scan_serial_ports()`、`scan_usb()`、`collect_probe_info()` | 用真实枚举替换固定返回值 | 使用 `serial.tools.list_ports.comports()` 采集完整 `SerialPortInfo` 字段；新增按 OS 的 USB 枚举适配层（macOS/Linux/Windows）；统一归一化输出；权限异常映射错误码 | 3.1, AC1 |
| 新增 | `backend/infrastructure/usb_scanner.py` | `scan_usb_devices()`、平台子方法 | 解耦 USB 枚举与串口枚举 | macOS 通过 `system_profiler SPUSBDataType -json`，Linux 通过 `lsusb`（可选补充 `/sys`），Windows 通过 `wmic`/PowerShell；解析失败映射 `BOARD_DETECT_SCAN_FAILED` | 2 In Scope, 3.1 |
| 修改 | `backend/models/schemas.py` | `ProbeInfo` 扩展、新增 `MatchSignals`、`IdentifyBoard*`、`SerialConfig`、`RunCheckRequest` 扩展 | 对齐 PRD 接口与字段 | `DetectBoardResponse` 增加 `matchSignals`；新增 `/boards/identify` 请求响应；`RunCheckRequest` 支持 `serial_keyword_assert`、`serialConfig`、`probeCommand`、`expectKeywords`、`assertMode` | 3.1, 3.2, 3.3 |
| 修改 | `backend/core/errors.py` | `ErrorCode` | 补齐真实扫描与串口断言错误码 | 新增 `BOARD_DETECT_SCAN_FAILED`、`RUN_CHECK_PORT_OPEN_FAILED`、`RUN_CHECK_WRITE_FAILED`、`RUN_CHECK_KEYWORD_MISSING`；保留已有码兼容 | 3.1, 3.3 |
| 修改 | `backend/services/board_detection_service.py` | `detect()` 重构、新增 `identify()` | 实现多信号融合识别与可解释输出 | 基于 `用户输入 + VID/PID + 端口描述/产品 + 端口命名特征` 打分；返回 `needConfirm/confidence/matchSignals/candidates`；支持阈值与 top1-top2 差值门限 | 2 In Scope, AC2, AC3 |
| 新增 | `backend/services/board_matcher.py` | `score_candidates()`、`build_explain()` | 将融合策略独立为可测试模块 | 内置板卡特征库（VID/PID、alias、关键词）；输出候选排序及 `signalBreakdown` | 4.3, AC2 |
| 修改 | `backend/api/routes/boards.py` | `detect_board()`、新增 `identify_board()` | 暴露识别二次确认接口 | 新增 `POST /api/v1/boards/identify`；读取历史 `probe snapshot` + 用户手工候选做最终判定 | 3.2, AC3 |
| 修改 | `backend/repositories/schema.sql` | 新增数据表 | 落地追溯模型 | 新增 `device_probe_snapshots`、`board_match_traces`、`serial_run_check_reports`，并加索引 | 4.1~4.4, AC6 |
| 修改 | `backend/repositories/sqlite_repo.py` | `save/get probe`、`save match trace`、`save run-check report` | 支撑审计与任务详情回看 | 新增仓储方法，持久化扫描快照、候选评分、串口执行证据与失败原因 | AC6 |
| 修改 | `backend/services/run_check_service.py` | `run_check()` 全量重写 | 从“命令执行”改为“真实串口读写断言” | 打开串口、写入 `probeCommand`、循环读取到超时、按 `all/any` 断言关键字、保存 transcript 与报告 | 3.3, AC4, AC5 |
| 修改 | `backend/api/routes/projects.py` | `run_check_route()` | 接入新的运行校验参数与产物 | 使用请求体 `serialConfig/expectKeywords/...` 调用真实串口校验；task artifacts 增加 `serialTranscriptPath/matchedKeywords` | 3.3, AC4~6 |
| 修改 | `backend/services/task_service.py` | 任务 artifact 更新逻辑 | 承载新增报告字段 | 统一 artifacts 键（`report`、`serialTranscriptPath`、`matchedKeywords`） | AC6 |
| 修改 | `frontend/api_client.py` | `identify_board()`、`run_check()` 入参适配 | 前端消费新接口 | 新增 `/boards/identify` 调用；`run_check` 传递扩展请求体 | 5 前端影响 |
| 修改 | `frontend/board_assistant_page.py` | 识别卡片、运行校验卡片 | 去除硬编码并完善门禁 | 增加候选手工确认 + 二次识别按钮；串口参数表单（端口/波特率/校验位/停止位/写超时）；关键词断言配置与错误分类展示 | 5 前端影响, AC3~5 |
| 修改 | `backend/tests/test_backend_api.py` | 新增/调整接口测试 | 覆盖真实流程边界 | 增加无设备、低置信度、identify 二次确认、串口超时、关键字缺失等测试；用 monkeypatch 注入 fake 串口对象而非业务 mock 返回 | 测试与回归要求 |
| 修改 | `prompts/sirius-api.postman.json` | 新增/更新请求样例 | 同步接口契约 | 补充 `/boards/identify`；更新 `/projects/{projectId}/run-check` 请求字段和错误码样例 | 仓库 Post Coding 规则 |

## 3. 关键逻辑伪代码

### 3.1 真实设备扫描与快照落库

```python
def collect_probe_info(scan_usb_flag: bool, scan_ports_flag: bool) -> ProbeSnapshot:
    serial_ports = []
    usb_devices = []

    if scan_ports_flag:
        for p in serial.tools.list_ports.comports():
            serial_ports.append({
                "device": p.device,
                "description": p.description,
                "hwid": p.hwid,
                "vid": p.vid,
                "pid": p.pid,
                "serialNumber": p.serial_number,
                "location": p.location,
                "manufacturer": p.manufacturer,
                "product": p.product,
                "interface": p.interface,
            })

    if scan_usb_flag:
        usb_devices = usb_scanner.scan_usb_devices()  # 平台适配

    if not serial_ports and not usb_devices:
        raise AppException(ErrorCode.BOARD_DETECT_EMPTY, "未扫描到可识别设备", 404)

    snapshot = {"requestId": gen_request_id(), "serialPorts": serial_ports, "usbDevices": usb_devices}
    repo.save_probe_snapshot(snapshot)
    return snapshot
```

### 3.2 融合识别评分与门禁

```python
def identify_with_fusion(user_input, manual_candidate, snapshot, threshold, margin):
    candidates = board_matcher.score_candidates(
        user_input=user_input,
        manual_candidate=manual_candidate,
        serial_ports=snapshot.serial_ports,
        usb_devices=snapshot.usb_devices,
    )

    top1 = candidates[0]
    top2 = candidates[1] if len(candidates) > 1 else None
    need_confirm = (top1.score < threshold) or (top2 and (top1.score - top2.score) < margin)

    repo.save_match_traces(request_id=snapshot.request_id, candidates=candidates, need_confirm=need_confirm)

    return {
        "resolvedBoard": top1.to_board(),
        "needConfirm": need_confirm,
        "matchSignals": top1.match_signals,
        "candidates": [c.to_board() for c in candidates],
        "explain": top1.explain,
    }
```

### 3.3 真实串口关键字断言

```python
def run_serial_keyword_assert(payload, report_dir):
    started = now()
    transcript_lines = []

    try:
        with serial.Serial(
            port=payload.serialConfig.port,
            baudrate=payload.serialConfig.baudrate,
            bytesize=payload.serialConfig.bytesize,
            parity=payload.serialConfig.parity,
            stopbits=payload.serialConfig.stopbits,
            timeout=0.2,
            write_timeout=payload.serialConfig.writeTimeoutSec,
        ) as ser:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            if payload.probeCommand:
                ser.write(payload.probeCommand.encode("utf-8"))
                ser.flush()

            deadline = time.monotonic() + payload.timeoutSec
            while time.monotonic() < deadline:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    transcript_lines.append(f"[{utc_now()}] RX {line}")
                if assert_keywords(transcript_lines, payload.expectKeywords, payload.assertMode):
                    break
    except SerialException as exc:
        raise map_serial_exception(exc)

    matched = matched_keywords(transcript_lines, payload.expectKeywords)
    passed = evaluate(matched, payload.expectKeywords, payload.assertMode)
    if not passed:
        raise AppException(ErrorCode.RUN_CHECK_KEYWORD_MISSING, "未命中期望关键字", 422)

    transcript_path = write_transcript(report_dir, transcript_lines)
    return build_report(started, now(), transcript_path, matched, passed=True)
```

## 4. 数据层与接口变更计划

### 4.1 数据层变更（有）

新增表（SQLite）：

1. `device_probe_snapshots`
- 字段：`probe_id`、`request_id`、`serial_ports_json`、`usb_devices_json`、`scanned_at`
- 索引：`idx_probe_request_id(request_id)`

2. `board_match_traces`
- 字段：`id`、`request_id`、`candidate_model`、`score`、`signal_breakdown_json`、`decision`
- 索引：`idx_match_request_id(request_id)`

3. `serial_run_check_reports`
- 字段：`report_id`、`task_id`、`port`、`baudrate`、`probe_command`、`expect_keywords_json`、`assert_mode`、`captured_lines_json`、`matched_keywords_json`、`passed`、`failure_reason`、`started_at`、`ended_at`
- 索引：`idx_runcheck_task_id(task_id)`

迁移顺序：

1. 修改 `schema.sql` 增加新表（全部 `IF NOT EXISTS`）。
2. 在 `SQLiteRepo.init_schema()` 保留向后兼容迁移逻辑（旧库自动补字段/补表）。
3. 路由服务改为先写快照与trace，再返回识别结果。

兼容策略：

- 保留 `projects` 与 `project_tasks` 现有结构，不破坏既有评估链路。
- 新增报告表与任务 artifacts 双写，保证“旧任务查询接口”可继续工作。

### 4.2 后端接口变更

1. `POST /api/v1/boards/detect`（改）
- 返回新增：`matchSignals`、更完整 `probeInfo`
- 错误码补齐：`BOARD_DETECT_EMPTY`、`BOARD_DETECT_PERMISSION_DENIED`、`BOARD_DETECT_SCAN_FAILED`

2. `POST /api/v1/boards/identify`（增）
- 请求：`requestId`、`userProvidedModel`、`manualCandidateModel`
- 响应：`resolvedBoard`、`needConfirm`、`explain`

3. `POST /api/v1/projects/{projectId}/run-check`（改）
- 请求改为真实串口断言配置：`checkProfile=serial_keyword_assert`、`serialConfig`、`probeCommand`、`expectKeywords`、`assertMode`
- 错误码补齐：`RUN_CHECK_PORT_OPEN_FAILED`、`RUN_CHECK_WRITE_FAILED`、`RUN_CHECK_KEYWORD_MISSING`、`RUN_CHECK_TIMEOUT`

4. `GET /api/v1/tasks/{taskId}`（兼容增强）
- `artifacts` 新增：`serialTranscriptPath`、`matchedKeywords`

### 4.3 前端改动

- 识别区域：
  - 展示扫描明细（串口 + USB）。
  - `needConfirm=true` 时仅允许“人工选候选 + 调用 identify”，禁止继续同步资料。
- 运行校验区域：
  - 新增串口配置表单并从识别结果自动带入默认端口（可编辑）。
  - 新增期望关键字与断言模式（`all/any`）。
  - 错误提示按错误码分类显示。

## 5. 实施步骤（Step-by-step）

1. 重构扫描基础设施：先完成 `device_scanner + usb_scanner`，并通过本机设备/无设备场景验证。
2. 扩展 Schema 与错误码：补齐模型字段与 `ErrorCode`，保证接口编译通过。
3. 落地识别算法：新增 `board_matcher`，改造 `detect`，再新增 `identify` 接口闭环。
4. 增加持久化：实现快照/trace/report 的仓储方法和表结构。
5. 重写运行校验：`run_check_service` 切换到真实串口读写与断言；接入任务 artifacts。
6. 改造前端消费：更新 `api_client` + `board_assistant_page`，去除硬编码端口和 profile。
7. 更新接口文档：同步 `prompts/sirius-api.postman.json`。
8. 自测顺序：
   1) `/boards/detect` 无设备与有设备；
   2) `/boards/identify` 高置信度/低置信度；
   3) `/projects/{id}/run-check` 通过/超时/关键字缺失。

## 6. 风险、回滚与兼容策略

主要风险：

- P0：各平台 USB 枚举命令输出差异导致解析脆弱。
- P0：串口设备可见但不可打开（权限问题）导致误判为设备异常。
- P1：同 VID/PID 多型号冲突，融合策略阈值不合理导致误判率上升。
- P2：高频串口输出导致 transcript 过大。

缓解策略：

- USB 枚举采用“命令失败可降级，仅串口维持可用”策略，但必须明确 `matchSignals` 缺失原因。
- 串口异常按类型映射错误码，向前端返回可诊断文案。
- 引入 `detect_confidence_threshold + top1_top2_margin` 双门限。
- transcript 设定最大行数（例如 2000 行）和最大文件大小上限，超限截断并记录提示。

回滚点：

1. 若识别链路异常，回滚 `boards` 路由到旧版本并保持 `/boards/identify` 下线。
2. 若串口校验不稳定，回滚 `run_check_service` 到命令模式但接口保持新字段兼容（服务端忽略新字段并告警）。
3. DB 回滚仅删除新增三张表，不影响既有 `projects/project_tasks`。

## 7. 测试关注点（前端/后端）

后端测试重点：

- 设备扫描：无设备、权限拒绝、扫描器异常。
- 融合识别：
  - 用户输入 + VID/PID 双命中自动通过；
  - 仅弱特征命中触发 `needConfirm=true`；
  - `identify` 手工候选后二次判定通过。
- 串口校验：端口打开失败、写入超时、关键字缺失、超时与成功路径。
- 可追溯性：任务详情可返回完整 artifacts 与报告字段。

前端测试重点：

- `needConfirm=true` 时流程门禁是否生效（未确认不能同步资料）。
- 串口表单参数是否准确传递到后端。
- 错误码映射文案是否可区分端口打开失败/写入失败/超时/关键字缺失。
- 任务详情展示是否包含 transcript 路径与关键字匹配结果。

## 8. 落盘信息

- 目标路径：`.ai-workspace/agent2-plan-real-device-scan-recognition-and-serial-runcheck-v1.md`
- 用途：供 Agent3 直接执行的最新改动计划（非 mock 实现）

## 9. LATEST.md 更新信息

- 目标路径：`.ai-workspace/LATEST.md`
- 计划写入内容：`agent2-plan-real-device-scan-recognition-and-serial-runcheck-v1.md`
