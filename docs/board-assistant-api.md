# Board Assistant API（v1）

## 鉴权

- Header: `Authorization: Bearer <token>`
- 默认本地 token：`dev-token`（可通过 `BOARD_ASSISTANT_API_TOKEN` 覆盖）

## 接口列表

### 1. 识别板卡

- `POST /api/v1/boards/detect`
- 请求体：

```json
{
  "userProvidedModel": "STM32F103C8T6-BluePill",
  "scanPorts": true,
  "scanUsb": true
}
```

### 2. 同步官方资料

- `POST /api/v1/boards/knowledge/sync`

### 3. 生成工程

- `POST /api/v1/projects/generate`

### 4. 烧录项目

- `POST /api/v1/projects/{projectId}/flash`
- 要求：`userConfirmedRisk=true`

### 5. 运行校验

- `POST /api/v1/projects/{projectId}/run-check`

### 6. 任务详情

- `GET /api/v1/tasks/{taskId}`

### 7. 评估运行

- `POST /api/v1/evaluations/prototype/run`

### 8. 评估报告

- `POST /api/v1/evaluations/reports/generate`

## 错误码

- 板卡识别：`BOARD_DETECT_EMPTY`、`BOARD_DETECT_AMBIGUOUS`、`BOARD_DETECT_PERMISSION_DENIED`
- 资料同步：`OFFICIAL_SOURCE_NOT_FOUND`、`OFFICIAL_SOURCE_UNREACHABLE`、`SPEC_PARSE_FAILED`
- 工程生成：`GEN_REQUIREMENT_INVALID`、`GEN_TEMPLATE_NOT_SUPPORTED`、`GEN_DEPENDENCY_RESOLVE_FAILED`
- 烧录运行：`FLASH_CONFIRMATION_REQUIRED`、`FLASH_TOOL_NOT_FOUND`、`FLASH_DEVICE_BUSY`、`FLASH_FAILED`
- 运行校验：`RUN_CHECK_TIMEOUT`、`RUN_CHECK_NO_SIGNAL`、`RUN_CHECK_PROFILE_INVALID`
- 评估：`EVAL_BOARD_NOT_READY`、`EVAL_SCENARIO_INVALID`
