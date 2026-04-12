# PRD：真实设备扫描、融合识别与真实串口运行校验

## 1. 需求摘要

本需求要求将现有占位能力替换为可在真实开发板上执行的能力，聚焦 6 个功能：

1. 真实设备扫描：用真实 USB/串口枚举替换固定返回值。  
2. 板卡识别规则增强：基于 `VID/PID + 端口特征 + 用户输入` 融合判定。  
3. 运行校验真实化：由“模拟脚本输出”改为“真实串口读写 + 关键字断言”。
4. 官方资料同步真实化：厂商 API / 网页 / PDF 索引抓取，支持缓存与过期刷新。
5. 工程生成模板化：从“示例 main.c”升级为“按板卡/框架模板生成”。
6. 烧录命令动态化：按板卡与工具链生成命令（`stlink/esptool/openocd`）。
### 实现状态

✅ **已实现** (3/6)

1. ✅ **真实设备扫描**：用真实 USB/串口枚举替换固定返回值。  
  - 实现文件：`backend/infrastructure/device_scanner.py`、`usb_scanner.py`
  - 支持 macOS/Linux/Windows 平台
   
2. ✅ **板卡识别规则增强**：基于 `VID/PID + 端口特征 + 用户输入` 融合判定。  
  - 实现文件：`backend/services/board_matcher.py`
  - 支持多信号融合评分和置信度计算
   
3. ✅ **运行校验真实化**：由"模拟脚本输出"改为"真实串口读写 + 关键字断言"。
  - 实现文件：`backend/services/run_check_service.py`
  - 支持完整的串口通信与断言验证

⚠️ **部分实现** (1/6)

4. ⚠️ **官方资料同步真实化**：厂商 API / 网页 / PDF 索引抓取，支持缓存与过期刷新。
  - 当前状态：仅返回硬编码链接，未实现真实抓取
  - 实现文件：`backend/infrastructure/official_source_client.py`
  - 待完成：HTTP 抓取、解析、缓存机制

❌ **待完成** (2/6)

5. ❌ **工程生成模板化**：从"示例 main.c"升级为"按板卡/框架模板生成"。
  - 当前状态：仅生成占位 main.c
  - 实现文件：`backend/services/project_generation_service.py`
  - 待完成：模板注册表、动态渲染、多框架支持
   
6. ❌ **烧录命令动态化**：按板卡与工具链生成命令（`stlink/esptool/openocd`）。
  - 当前状态：返回纯 mock 命令（`echo '模拟烧录成功'`）
  - 实现文件：`backend/services/flash_service.py`
  - 待完成：真实工具链集成、命令动态生成、执行反馈
目标是形成“可连接真实硬件、可复现、可审计”的端到端闭环，为后续学习 AGENT 与评估优化提供可信底座。

## 2. 范围定义（In Scope / Out of Scope）

### In Scope

- 后端设备扫描替换为真实实现：
- 串口枚举：使用 `pyserial` 的 `serial.tools.list_ports.comports()` 获取端口及 USB 扩展属性。
- USB 枚举：实现平台适配层（macOS/Linux/Windows）采集 USB 设备信息，并统一归一化输出。

- 板卡识别增强：
- 引入多信号融合评分：`用户输入`、`VID/PID`、`端口描述/产品字符串`、`端口命名特征`。
- 输出 `needConfirm`、`confidence`、`matchSignals` 与候选排序依据，支持可解释性。

- 运行校验真实化：
- 打开真实串口、发送测试命令、读取串口回包、执行关键字断言。
- 记录完整执行证据（发送内容、接收片段、时间戳、断言结果、失败原因）。

- 官方资料同步真实化：
- 按优先级抓取：厂商 API > 官方文档网页 > 官方 PDF 索引。
- 抓取结果落库缓存，支持 TTL、强制刷新与来源追踪。

- 工程生成模板化：
- 建立模板注册表：`board_family + framework + toolchain + template_version`。
- 生成时按识别结果选择模板，渲染配置（引脚、串口、依赖、构建脚本）。

- 动态烧录命令：
- 根据目标板卡工具链自动选择 `st-flash`、`esptool`、`openocd`。
- 生成可审计命令计划（含参数来源），执行前可二次确认。

#### ✅ **已实现**（3/6 功能完成）

**1. 后端设备扫描替换为真实实现：** ✅
- ✅ 串口枚举：使用 `pyserial` 的 `serial.tools.list_ports.comports()` 获取端口及 USB 扩展属性。
  - 实现：`backend/infrastructure/device_scanner.py:scan_serial_ports()`
- ✅ USB 枚举：实现平台适配层（macOS/Linux/Windows）采集 USB 设备信息，并统一归一化输出。
  - 实现：`backend/infrastructure/usb_scanner.py:_scan_macos_usb()`、`_scan_linux_usb()`、`_scan_windows_usb()`

**2. 板卡识别增强：** ✅
- ✅ 引入多信号融合评分：`用户输入`、`VID/PID`、`端口描述/产品字符串`、`端口命名特征`。
  - 实现：`backend/services/board_matcher.py:score_candidates()`
  - 权重：userInput(0.45) > vidPid(0.35) > serialKeyword(0.15) > usbKeyword(0.12)
- ✅ 输出 `needConfirm`、`confidence`、`matchSignals` 与候选排序依据，支持可解释性。
  - 实现：`backend/services/board_detection_service.py:detect()`

**3. 运行校验真实化：** ✅
- ✅ 打开真实串口、发送测试命令、读取串口回包、执行关键字断言。
  - 实现：`backend/services/run_check_service.py:run_check()`
- ✅ 记录完整执行证据（发送内容、接收片段、时间戳、断言结果、失败原因）。
  - 实现：`backend/repositories/sqlite_repo.py:save_serial_run_check_report()`
  - 支持档位：`serial_keyword_assert`、`serial_heartbeat`
  - 断言模式：`all`（全匹配）、`any`（任意匹配）

#### ⚠️ **部分实现**（1/6 功能部分完成）

**4. 官方资料同步真实化：** ⚠️
- ✅ 按优先级指定来源规则（框架已准备）
- ✅ 缓存与过期刷新框架设计
- ❌ 未实现：厂商 API 真实抓取、网页解析、PDF 索引获取
  - 当前实现：`backend/infrastructure/official_source_client.py` 仅返回硬编码链接
  - 待完成：HTTP 客户端、HTML 解析（BeautifulSoup）、PDF 提取（pdfplumber）

#### ❌ **待完成**（2/6 功能尚未实现）

**5. 工程生成模板化：** ❌
- ❌ 建立模板注册表：`board_family + framework + toolchain + template_version`。
  - 当前状态：`backend/services/project_generation_service.py` 仅生成固定占位 main.c
  - 待完成：
    - 建立 `TEMPLATE_REGISTRY` 映射表
    - 集成 Jinja2 模板引擎
    - 支持多框架（baremetal、FreeRTOS、Arduino）
- ❌ 生成时按识别结果选择模板，渲染配置（引脚、串口、依赖、构建脚本）。

**6. 动态烧录命令：** ❌
- ❌ 根据目标板卡工具链自动选择 `st-flash`、`esptool`、`openocd`。
  - 当前状态：`backend/services/flash_service.py` 返回 mock 命令（`echo '模拟烧录成功'`）
  - 待完成：
    - 工具链检测（是否安装 `arm-none-eabi-gcc`、`esptool` 等）
    - 真实编译执行（调用工具链进行源代码编译）
    - 动态命令生成（根据版本、参数生成命令）
    - 命令执行与反馈（流式日志、错误诊断）
- ❌ 生成可审计命令计划（含参数来源），执行前可二次确认。

- 测试与回归：
- 覆盖无设备、设备冲突、低置信度、串口超时、关键字不匹配等场景。

### Out of Scope

- 自动安装板卡驱动、自动修复系统串口权限。
- JTAG/SWD 调试协议级解析（本期只做串口通道运行校验）。
- 多设备并发调度（本期同一任务默认单设备）。
- 非官方来源论坛帖自动纳入参数真值源。

## 3. 接口定义（OpenAPI 风格草案）

### 3.1 真实设备扫描

- `POST /api/v1/boards/detect`
### 3.1 真实设备扫描 ✅ **已实现**

- `POST /api/v1/boards/detect` ✅
- 鉴权：`Bearer Token`
- 请求体：
```json
{
  "userProvidedModel": "optional string",
  "scanPorts": true,
  "scanUsb": true
}
```
- 响应体（新增字段）：
```json
{
  "requestId": "req_xxx",
  "resolvedBoard": {
    "vendor": "ST",
    "model": "STM32F103C8T6-BluePill",
    "confidence": 0.91
  },
  "needConfirm": false,
  "matchSignals": {
    "userInputMatched": true,
    "vidPidMatched": true,
    "portFeatureMatched": true
  },
  "candidates": [],
  "probeInfo": {
    "usbVid": "0483",
    "usbPid": "3748",
    "serialPorts": ["/dev/tty.usbmodem1101"]
  }
}
```
- 错误码补充：
- `BOARD_DETECT_EMPTY`：无可识别串口/USB设备
- `BOARD_DETECT_PERMISSION_DENIED`：设备访问权限不足
- `BOARD_DETECT_SCAN_FAILED`：平台扫描器异常

### 3.2 融合识别策略配置（新增）

- `POST /api/v1/boards/identify`
### 3.2 融合识别策略配置 ✅ **已实现**

- `POST /api/v1/boards/identify` ✅
- 鉴权：`Bearer Token`
- 说明：当用户在前端手动选择候选或调整模型提示后重新识别，返回融合后的最终判定。
- 请求体：
```json
{
  "requestId": "req_xxx",
  "userProvidedModel": "stm32f103c8",
  "manualCandidateModel": "STM32F103C8T6-BluePill"
}
```
- 响应体：
```json
{
  "resolvedBoard": {
    "vendor": "ST",
    "model": "STM32F103C8T6-BluePill",
    "confidence": 0.96
  },
  "needConfirm": false,
  "explain": [
    "VID/PID 命中 0483:3748",
    "端口描述包含 STLink",
    "用户输入与型号别名命中"
  ]
}
```

### 3.3 官方资料同步（真实抓取 + 缓存）

- `POST /api/v1/boards/knowledge/sync`
### 3.3 官方资料同步（真实抓取 + 缓存）⚠️ **部分实现**

- `POST /api/v1/boards/knowledge/sync` ⚠️
  - ✅ 框架已准备、缓存机制已设计
  - ❌ 待完成：真实 HTTP 抓取、网页解析、缓存实现

- 鉴权：`Bearer Token`
- 请求体：
```json
{
  "boardModel": "STM32F103C8T6-BluePill",
  "vendorHint": "ST",
  "forceRefresh": false,
  "sourcePolicy": {
    "allowApi": true,
    "allowWeb": true,
    "allowPdfIndex": true
  }
}
```
- 响应体：
```json
{
  "knowledgeId": "kb_xxx",
  "cache": {
    "cacheHit": true,
    "expiresAt": "2026-04-13T12:00:00Z",
    "ttlSec": 86400
  },
  "sources": [
    {
      "url": "https://www.st.com/...",
      "sourceType": "official_docs",
      "retrievedAt": "2026-04-12T12:00:00Z"
    }
  ],
  "specSummary": {
    "mcu": "STM32F103C8T6",
    "flashKB": 64,
    "ramKB": 20
  }
}
```
- 错误码补充：
- `OFFICIAL_SOURCE_NOT_FOUND`
- `OFFICIAL_SOURCE_UNREACHABLE`
- `OFFICIAL_SOURCE_PARSE_FAILED`

### 3.4 工程生成（模板化）

- `POST /api/v1/projects/generate`
### 3.4 工程生成（模板化）❌ **待完成**

- `POST /api/v1/projects/generate` ❌
  - 当前：仅生成占位 main.c
  - 待完成：模板选择、动态渲染、多框架支持

- 鉴权：`Bearer Token`
- 请求体：
```json
{
  "boardModel": "STM32F103C8T6-BluePill",
  "knowledgeId": "kb_xxx",
  "framework": "baremetal|freertos|arduino",
  "toolchain": "gcc-arm-none-eabi",
  "requirementText": "每秒输出 heartbeat",
  "templateOptions": {
    "uartBaudrate": 115200,
    "enableWatchdog": false
  }
}
```
- 响应体：
```json
{
  "projectId": "prj_xxx",
  "workspacePath": "/workspace/projects/prj_xxx",
  "templateId": "stm32f1-baremetal-uart-v2",
  "generatedFiles": ["src/main.c", "Makefile", "scripts/flash.sh", "scripts/run_check.py"],
  "buildCommand": "make all",
  "flashPlanId": "fp_xxx"
}
```
- 错误码补充：
- `GEN_TEMPLATE_NOT_SUPPORTED`
- `GEN_TEMPLATE_RENDER_FAILED`

### 3.5 动态烧录命令规划（新增）

- `POST /api/v1/projects/{projectId}/flash/plan`
### 3.5 动态烧录命令规划（新增）❌ **待完成**

- `POST /api/v1/projects/{projectId}/flash/plan` ❌
  - 当前：无实现
  - 待完成：工具链检测、命令动态生成

- 鉴权：`Bearer Token`
- 请求体：
```json
{
  "preferredTool": "auto|stlink|esptool|openocd",
  "port": "/dev/tty.usbmodem1101",
  "programmer": "stlink",
  "chip": "esp32|stm32f103",
  "artifacts": {
    "bin": "build/app.bin",
    "elf": "build/app.elf"
  }
}
```
- 响应体：
```json
{
  "flashPlanId": "fp_xxx",
  "tool": "stlink",
  "command": "st-flash write build/app.bin 0x08000000",
  "explain": [
    "板卡映射到 stlink",
    "固件类型为 bin，使用 write 子命令"
  ],
  "requiresConfirm": true
}
```
- 错误码补充：
- `FLASH_PLAN_UNSUPPORTED_BOARD`
- `FLASH_PLAN_ARTIFACT_MISSING`
- `FLASH_PLAN_TOOL_NOT_FOUND`

### 3.6 真实串口运行校验

- `POST /api/v1/projects/{projectId}/run-check`
### 3.6 真实串口运行校验 ✅ **已实现**

- `POST /api/v1/projects/{projectId}/run-check` ✅
- 鉴权：`Bearer Token`
- 请求体（扩展）：
```json
{
  "checkProfile": "serial_keyword_assert",
  "timeoutSec": 20,
  "serialConfig": {
    "port": "/dev/tty.usbmodem1101",
    "baudrate": 115200,
    "bytesize": 8,
    "parity": "N",
    "stopbits": 1,
    "writeTimeoutSec": 2
  },
  "probeCommand": "ping\\n",
  "expectKeywords": ["pong", "ready"],
  "assertMode": "all"
}
```
- 响应体：
```json
{
  "taskId": "task_xxx",
  "status": "success",
  "startedAt": "2026-04-12T12:05:00Z"
}
```
- 任务详情 artifacts（新增建议）：
```json
{
  "report": "断言通过",
  "serialTranscriptPath": "/workspace/projects/prj_xxx/reports/serial-transcript.log",
  "matchedKeywords": ["pong", "ready"]
}
```
- 错误码补充：
- `RUN_CHECK_PORT_OPEN_FAILED`
- `RUN_CHECK_WRITE_FAILED`
- `RUN_CHECK_KEYWORD_MISSING`
- `RUN_CHECK_TIMEOUT`

## 4. 数据模型草案

### 4.1 DeviceProbeSnapshot（新增）

- `probeId`：string，必填，主键
- `requestId`：string，必填，索引
- `serialPorts`：SerialPortInfo[]，必填
- `usbDevices`：UsbDeviceInfo[]，必填
- `scannedAt`：datetime，必填

### 4.2 SerialPortInfo（新增）

- `device`：string，必填（如 `/dev/tty.usbmodem1101`、`COM5`）
- `description`：string，非必填
- `hwid`：string，非必填
- `vid`：integer，非必填
- `pid`：integer，非必填
- `serialNumber`：string，非必填
- `location`：string，非必填
- `manufacturer`：string，非必填
- `product`：string，非必填
- `interface`：string，非必填

### 4.3 BoardMatchTrace（新增）

- `requestId`：string，必填
- `candidateModel`：string，必填
- `score`：float，必填（0~1）
- `signalBreakdown`：object，必填：
- `userInputScore`
- `vidPidScore`
- `portFeatureScore`
- `historyScore`
- `decision`：enum，必填：`auto_accept` / `need_confirm` / `reject`

### 4.4 SerialRunCheckReport（新增）

- `reportId`：string，必填
- `taskId`：string，必填，索引
- `port`：string，必填
- `baudrate`：integer，必填
- `probeCommand`：string，非必填
- `expectKeywords`：string[]，必填
- `assertMode`：enum，必填：`all` / `any`
- `capturedLines`：string[]，必填（建议限制最大行数）
- `matchedKeywords`：string[]，必填
- `passed`：boolean，必填
- `failureReason`：string，非必填
- `startedAt`：datetime，必填
- `endedAt`：datetime，必填

### 4.5 KnowledgeCacheEntry（新增）

- `cacheKey`：string，必填，主键（建议由 `vendor+boardModel+sourcePolicy` 计算）
- `boardModel`：string，必填
- `payloadJson`：string，必填（规格摘要与来源）
- `sourceDigest`：string，必填（用于判定变更）
- `ttlSec`：integer，必填
- `fetchedAt`：datetime，必填
- `expiresAt`：datetime，必填

### 4.6 ProjectTemplateRegistry（新增）

- `templateId`：string，必填，主键
- `boardFamily`：string，必填（如 `stm32f1`、`esp32`）
- `framework`：enum，必填：`baremetal` / `freertos` / `arduino`
- `toolchain`：string，必填
- `templateVersion`：string，必填
- `entryFiles`：string[]，必填
- `status`：enum，必填：`active` / `deprecated`

### 4.7 FlashPlan（新增）

- `flashPlanId`：string，必填，主键
- `projectId`：string，必填
- `tool`：enum，必填：`stlink` / `esptool` / `openocd`
- `command`：string，必填
- `parameterSources`：object，必填（端口、芯片、镜像路径等来源）
- `createdAt`：datetime，必填

## 5. 前端影响面说明

- “板卡识别”卡片新增：
- 扫描明细展示（串口 + USB）
- 识别解释信息（命中信号与评分）
- `needConfirm=true` 时必须人工确认后才能进入下一步

- “运行校验”卡片新增：
- 串口参数表单（端口、波特率、校验位等）
- 探测命令输入框、关键字断言配置（`all/any`）
- 实时日志区（显示发送/接收与断言状态）

- 失败可诊断性：
- 错误提示应区分“端口打开失败/写入失败/超时/关键字缺失”

- “资料同步”卡片新增：
- 显示抓取来源、缓存命中状态、过期时间、强制刷新开关。

- “工程生成”卡片新增：
- 选择框架/工具链；展示命中的模板 ID 与生成文件清单。

- “烧录”卡片新增：
- 先展示动态命令计划，再允许执行；显示命令来源解释。

## 6. 验收标准（Given-When-Then）

1. 真实枚举替换占位值
- Given：机器连接了至少 1 个真实串口设备
- When：调用 `/boards/detect`
- Then：返回的端口列表与系统当前设备一致，不再出现固定硬编码值

2. 融合识别自动通过
- Given：用户输入型号与设备 `VID/PID` 同时命中同一板卡
- When：调用识别接口
- Then：`confidence >= threshold` 且 `needConfirm=false`

3. 融合识别低置信度门禁
- Given：仅命中弱特征（如端口名模糊匹配）
- When：调用识别接口
- Then：`needConfirm=true`，未确认前禁止同步资料/生成工程

4. 真实串口断言通过
- Given：目标板卡串口可读写，设备回包包含 `pong` 与 `ready`
- When：执行 `serial_keyword_assert`
- Then：任务成功，报告记录匹配关键字与接收日志

5. 真实串口断言失败
- Given：设备未返回期望关键字
- When：执行运行校验
- Then：返回 `RUN_CHECK_KEYWORD_MISSING`，并附带接收日志片段

6. 可追溯性
- Given：运行校验任务完成
- When：查询任务详情
- Then：可查看串口参数、发送命令、接收日志、断言结果与失败原因

7. 资料同步缓存命中
- Given：同一板卡在 TTL 内重复同步
- When：调用 `/boards/knowledge/sync` 且 `forceRefresh=false`
- Then：返回 `cacheHit=true`，且来源与摘要可追溯

8. 模板化工程生成
- Given：板卡与框架在模板注册表中存在匹配模板
- When：调用 `/projects/generate`
- Then：返回 `templateId` 与生成文件清单，不再仅输出固定 `main.c`

9. 动态烧录命令生成
- Given：板卡、工具链与固件产物齐全
- When：调用 `/projects/{projectId}/flash/plan`
- Then：返回可执行命令与参数来源解释，工具选择符合板卡映射规则

## 7. 风险与待确认项（按优先级）

### P0
- 待确认：华为/飞腾板卡首批型号清单及其串口参数基线（默认波特率、换行规范）
- 影响范围：识别准确率、运行校验通过率

- 风险：不同 OS 权限策略导致设备可见但不可打开
- 影响范围：真实校验稳定性、用户体验

- 待确认：厂商 API 访问频率限制与网页/PDF 抓取合规策略
- 影响范围：同步稳定性、法务风险

### P1
- 风险：同 VID/PID 对应多个近似型号，单一信号可能误判
- 影响范围：识别置信度和烧录安全

- 待确认：`confidence` 阈值与 `top1-top2` 差值门限
- 影响范围：自动通过比例与误判风险平衡

- 风险：模板版本漂移导致生成工程与最新 SDK 不兼容
- 影响范围：编译成功率与交付稳定性

### P2
- 风险：串口日志高频输出导致内存/存储增长
- 影响范围：任务服务性能

- 风险：动态命令模板参数缺失导致烧录失败
- 影响范围：烧录成功率

## 8. 落盘信息

- 目标路径：`devdocs/prd-real-device-scan-recognition-and-serial-runcheck.md`
- 文档版本：`v1.1`
- 产出角色：`Agent 1（需求与接口设计）`

---

## 调研依据（Context7）

- `libraryId`: `/pyserial/pyserial`  
- 查询关键词 1：`tools.list_ports.comports fields vid pid serial_number location product hwid`  
- 查询关键词 2：`Serial read write timeout readline in_waiting reset_input_buffer`
- `libraryId`: `/espressif/esptool`
- 查询关键词 3：`write_flash command examples --port --baud --before --after --flash-size detect`
- `libraryId`: `/websites/openocd_doc_html`
- 查询关键词 4：`openocd -f ... -c "program ... verify reset exit"`

调研结论（用于实现决策）：
- `pyserial` 的 `list_ports.comports()` 可返回 `vid/pid/serial_number/location/manufacturer/product/interface` 等扩展字段，可作为“真实枚举 + 识别信号”核心数据源。
- `pyserial.Serial(...)` 支持 `timeout/write_timeout/readline/flush/reset_*_buffer`，可满足“真实串口读写 + 关键字断言 + 超时控制”的运行校验实现要求。
- `esptool` 官方文档支持 `--port/--baud/--before/--after/write-flash` 等参数组合，可用于 ESP 系列动态命令模板。
- OpenOCD 官方文档支持 `-f <board cfg> -c "program <bin/elf> verify reset exit"`，可用于 SWD/JTAG 路径动态命令模板。
- `stlink` 在 Context7 未检索到权威库条目；命令模板暂按现有实践采用 `st-flash write <bin> <addr>`，后续需以官方手册再做一次核对。【假设】
