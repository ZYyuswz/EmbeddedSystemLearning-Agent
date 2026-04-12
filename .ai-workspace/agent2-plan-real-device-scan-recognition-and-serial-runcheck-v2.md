# Agent2 改动计划：真实设备扫描、融合识别与真实串口运行校验（v2）

## 0. 模板适配自检

- 角色边界：本文件仅做“代码改动规划”，不直接修改业务代码。
- 输入完整性：已读取 `devdocs/prd-real-device-scan-recognition-and-serial-runcheck.md`（v1.1，2026-04-12 更新）。
- 上下游门禁：本计划落盘于 `.ai-workspace/`，并更新 `LATEST.md` 指向本文件，供 Agent3 唯一执行。
- 规则一致性：遵循仓库约束（中文日志、接口变更同步 Postman、注释同步更新）。

## 1. 改动总览

基于 Agent1 最新 PRD 与当前代码现状，功能完成度从“全量改造”调整为“收尾落地”：

- 已实现（无需重复开发）：真实设备扫描、融合识别、真实串口运行校验。
- 待实现重点（本计划范围）：
1. 官方资料同步真实化（真实抓取 + 缓存/TTL + 强制刷新）；
2. 工程生成模板化（模板注册 + 动态渲染 + 文件清单返回）；
3. 烧录命令动态化（`flash/plan` 新接口 + 按板卡工具链生成命令 + 参数来源可审计）。

Context7 约束承接：本计划沿用 Agent1 在 PRD 中的调研结论（`/pyserial/pyserial`、`/espressif/esptool`、`/websites/openocd_doc_html`），Agent3 实现 `esptool/openocd` 命令模板时必须与这些结论一致；`stlink` 命令模板继续按【假设】标识并在代码中保留可替换配置位。

## 2. 文件级改动清单（表格）

| 操作 | 文件 | 模块/类/方法 | 改动目的 | 实现要点 | PRD/AC 映射 |
|---|---|---|---|---|---|
| 修改 | `backend/models/schemas.py` | `KnowledgeSyncRequest/Response`、`GenerateProjectRequest/Response`、新增 `FlashPlanRequest/Response` | 对齐 PRD 新字段与新接口 | `KnowledgeSyncRequest` 增加 `sourcePolicy`；`KnowledgeSyncResponse` 增加 `cache`；`GenerateProjectRequest` 增加 `framework/toolchain/templateOptions`；`GenerateProjectResponse` 增加 `templateId/generatedFiles/flashPlanId`；新增 `POST /flash/plan` 请求响应模型 | 3.3, 3.4, 3.5, AC7~9 |
| 修改 | `backend/core/errors.py` | `ErrorCode` | 补齐资料同步/烧录规划错误码 | 新增 `OFFICIAL_SOURCE_PARSE_FAILED`、`FLASH_PLAN_UNSUPPORTED_BOARD`、`FLASH_PLAN_ARTIFACT_MISSING`、`FLASH_PLAN_TOOL_NOT_FOUND` | 3.3, 3.5 |
| 修改 | `backend/repositories/schema.sql` | 新增数据表 | 持久化缓存、模板注册、烧录计划 | 新增 `knowledge_cache_entries`、`project_template_registry`、`flash_plans`；补必要索引 | 4.5~4.7, AC7~9 |
| 修改 | `backend/repositories/sqlite_repo.py` | 新增 cache/template/flash-plan 仓储方法 | 支撑 TTL 缓存与可追溯查询 | 增加 `get_knowledge_cache/save_knowledge_cache`、`find_template`、`save_flash_plan/get_flash_plan`；保证 JSON 字段序列化一致 | 4.5~4.7 |
| 修改 | `backend/infrastructure/official_source_client.py` | `fetch_sources()`、`parse_specs()` 拆分与增强 | 从硬编码改为真实抓取管线 | 拆成 `fetch_by_api/fetch_by_web/fetch_pdf_index`；统一 URL 去重与来源优先级；解析失败抛 `OFFICIAL_SOURCE_PARSE_FAILED` | 3.3, AC7 |
| 修改 | `backend/services/knowledge_sync_service.py` | `sync_official_sources()` | 实现 TTL 缓存与强制刷新 | 构造 cacheKey（vendor+board+sourcePolicy）；`forceRefresh=false` 且未过期时直接返回 `cacheHit=true`；否则抓取并落库 | 3.3, AC7 |
| 新增 | `backend/services/template_registry.py` | `resolve_template()`、`render_project_files()` | 模板化工程生成核心 | 维护 `board_family + framework + toolchain + template_version` 注册映射；用 Jinja2 渲染输出文件列表 | 3.4, AC8 |
| 修改 | `backend/services/project_generation_service.py` | `generate_project()` | 从占位工程改为模板化工程 | 依据 `boardModel+framework+toolchain` 解析模板；写入 `src/main.c/Makefile/scripts/*`；返回 `templateId/generatedFiles`；保留 run-check 脚本生成但改为模板输出 | 3.4, AC8 |
| 修改 | `backend/services/flash_service.py` | 保留 `flash_project()`，新增 `build_flash_plan()` | 生成并执行可审计烧录命令 | `build_flash_plan()` 按板卡映射生成 `stlink/esptool/openocd` 命令与 explain/parameterSources；`flash_project()` 改为消费计划命令而非项目固定命令 | 3.5, AC9 |
| 修改 | `backend/api/routes/projects.py` | 新增 `POST /{project_id}/flash/plan`；调整 `/flash` | 先规划再执行闭环 | `/flash/plan` 返回 `flashPlanId/tool/command/explain/requiresConfirm`；`/flash` 支持传入 `flashPlanId` 执行并校验归属 | 3.5 |
| 修改 | `backend/services/safety_service.py` | 校验计划命令策略 | 防止危险命令与不匹配编程器 | 安全校验从“字符串命令”扩展到“计划实体+参数来源”，保留用户确认门禁 | 风险控制 |
| 修改 | `frontend/api_client.py` | 新增 `plan_flash()`；更新 `generate_project()` payload | 前端消费新接口与字段 | 补 `POST /projects/{id}/flash/plan` 调用；`generate_project` 传 `framework/toolchain/templateOptions` | 5 前端影响 |
| 修改 | `frontend/board_assistant_page.py` | “同步资料”“生成工程”“烧录”区块 | 前端闭环对齐新能力 | 同步资料展示 `cacheHit/expiresAt/sources` 与强制刷新；工程生成增加框架/工具链选项并显示 `templateId/generatedFiles`；烧录流程改为“先生成计划再执行” | 5 前端影响 |
| 修改 | `backend/tests/test_backend_api.py` | 新增/更新测试用例 | 覆盖新增接口与关键边界 | 新增：缓存命中与强刷、模板不存在、flash plan 产物缺失/工具缺失、plan->flash 成功链路；调整旧用例对 `generate_project`、`flash` 响应断言 | AC7~9 |
| 修改 | `prompts/sirius-api.postman.json` | 新增与更新请求样例 | 接口契约同步 | 更新 `/boards/knowledge/sync` 请求/响应字段；更新 `/projects/generate`；新增 `/projects/{projectId}/flash/plan`；`/projects/{projectId}/flash` 增加 `flashPlanId` 示例 | Post Coding 规则 |

## 3. 关键逻辑伪代码

### 3.1 资料同步：TTL 缓存 + 强制刷新

```python
def sync_official_sources(repo, board_model, vendor_hint, force_refresh, source_policy):
    cache_key = build_cache_key(board_model, vendor_hint, source_policy)
    cached = repo.get_knowledge_cache(cache_key)

    if cached and (not force_refresh) and (cached.expires_at > now_utc()):
        return build_response_from_cache(cached, cache_hit=True)

    sources = official_source_client.fetch_sources(board_model, vendor_hint, source_policy)
    summary = official_source_client.parse_specs(board_model, sources)

    payload = {"sources": sources, "specSummary": summary}
    repo.save_knowledge_cache(cache_key, board_model, payload, ttl_sec=86400)
    repo.save_source_refs(knowledge_id, sources)

    return build_response(payload, cache_hit=False)
```

### 3.2 模板化工程生成

```python
def generate_project(repo, workspace_root, req):
    template = template_registry.resolve_template(
        board_model=req.boardModel,
        framework=req.framework,
        toolchain=req.toolchain,
    )
    if not template:
        raise AppException(ErrorCode.GEN_TEMPLATE_NOT_SUPPORTED, "未找到匹配模板", 422)

    project_id = new_project_id()
    workspace = make_workspace(workspace_root, project_id)

    rendered_files = template_registry.render_project_files(
        template=template,
        context={
            "requirementText": req.requirementText,
            "templateOptions": req.templateOptions,
            "boardModel": req.boardModel,
        },
    )
    write_files(workspace, rendered_files)

    repo.save_project(...)
    return {
      "projectId": project_id,
      "templateId": template.template_id,
      "generatedFiles": sorted(rendered_files.keys()),
      ...
    }
```

### 3.3 动态烧录命令规划

```python
def build_flash_plan(project, req):
    artifacts = resolve_artifacts(req, project.workspace_path)
    if not artifacts.bin and not artifacts.elf:
        raise AppException(ErrorCode.FLASH_PLAN_ARTIFACT_MISSING, "缺少可烧录产物", 422)

    tool = choose_tool(board_model=project.board_model, preferred=req.preferredTool)
    ensure_tool_available(tool)  # which/--version

    command, explain, parameter_sources = render_flash_command(tool, req, artifacts, project)
    return {
      "tool": tool,
      "command": command,
      "explain": explain,
      "parameterSources": parameter_sources,
      "requiresConfirm": True,
    }
```

## 4. 数据层与接口变更计划

### 4.1 数据层变更

- 有数据库改动。
- 新增表：
1. `knowledge_cache_entries`：`cache_key`、`board_model`、`payload_json`、`source_digest`、`ttl_sec`、`fetched_at`、`expires_at`
2. `project_template_registry`：`template_id`、`board_family`、`framework`、`toolchain`、`template_version`、`entry_files_json`、`status`
3. `flash_plans`：`flash_plan_id`、`project_id`、`tool`、`command`、`parameter_sources_json`、`created_at`

- 迁移顺序：
1. `schema.sql` 追加新表与索引（`IF NOT EXISTS`）；
2. `sqlite_repo.py` 增加读写方法并接入服务层；
3. API 层切换读取新实体；
4. 保留旧 `projects.flash_command` 字段用于兼容回退。

### 4.2 后端接口变更

1. `POST /api/v1/boards/knowledge/sync`（改）
- 请求新增：`sourcePolicy.allowApi/allowWeb/allowPdfIndex`
- 响应新增：`cache.cacheHit/cache.expiresAt/cache.ttlSec`

2. `POST /api/v1/projects/generate`（改）
- 请求新增：`framework`、`toolchain`、`templateOptions`
- 响应新增：`templateId`、`generatedFiles`、`flashPlanId(可空)`

3. `POST /api/v1/projects/{projectId}/flash/plan`（增）
- 返回命令计划与解释，默认 `requiresConfirm=true`

4. `POST /api/v1/projects/{projectId}/flash`（改）
- 请求新增 `flashPlanId`（推荐路径），保留兼容参数但优先执行计划命令

### 4.3 前端改动

- 同步资料卡片：增加“强制刷新”开关、缓存命中与过期时间展示、来源列表展示。
- 工程生成卡片：新增 `framework/toolchain` 选择与 `templateOptions` 输入，展示模板命中与文件清单。
- 烧录卡片：新增“生成烧录计划”按钮，显示计划命令与 explain，用户确认后再执行 `flash`。

## 5. 实施步骤（Step-by-step）

1. 扩模型与错误码：先改 `schemas.py`、`errors.py`，保证接口与 DTO 编译通过。
2. 扩数据库：新增三张表与仓储方法，补缓存/计划读写能力。
3. 落地资料同步：实现 `official_source_client` 抓取管线与 `knowledge_sync_service` 缓存逻辑。
4. 落地模板引擎：新增 `template_registry.py` 与模板资源，改造 `generate_project()`。
5. 落地烧录规划：实现 `build_flash_plan()`，新增 `/flash/plan` 路由并调整 `/flash` 执行路径。
6. 前端联调：更新 `api_client.py` 与 `board_assistant_page.py` 三个卡片交互。
7. 补测试：覆盖新增接口、缓存命中、模板不命中、命令规划失败与成功链路。
8. 更新 Postman：同步接口变更到 `prompts/sirius-api.postman.json`。

## 6. 风险、回滚与兼容策略

- 主要风险：
1. 外部站点抓取不稳定（限流、反爬、HTML 结构变更）。
2. 模板注册与板卡映射不一致导致误命中或空命中。
3. 本机工具链缺失导致 `flash/plan` 或 `flash` 执行失败。

- 缓解策略：
1. 抓取失败时按来源粒度降级，返回可诊断错误码，不吞错；
2. 模板匹配规则显式记录（board_family/framework/toolchain），响应里返回 templateId；
3. 命令规划前执行工具可用性检查并给出中文诊断日志。

- 回滚点：
1. 回滚 `/flash/plan` 路由与相关服务改动时，保留旧 `/flash` dry-run 能力；
2. 资料同步真实抓取不稳定时，可临时回退到缓存优先 + 只读历史来源；
3. 模板化不可用时回退到当前最小工程模板（作为兜底，但标记 `deprecated_fallback`）。

## 7. 测试关注点（前端/后端）

- 后端：
1. `/boards/knowledge/sync`：TTL 命中、过期刷新、`forceRefresh=true` 强刷、来源抓取失败分支。
2. `/projects/generate`：模板匹配成功、模板不支持、渲染变量缺失。
3. `/projects/{id}/flash/plan`：工具链缺失、产物缺失、命令生成成功且参数来源完整。
4. `/projects/{id}/flash`：`flashPlanId` 不存在/不归属/成功执行。

- 前端：
1. 缓存信息展示正确（命中态、过期时间）。
2. 模板选项传参与后端响应字段展示一致。
3. 烧录步骤严格遵循“先计划后执行”，且错误文案可定位问题。

## 8. 落盘信息

- 目标路径：`.ai-workspace/agent2-plan-real-device-scan-recognition-and-serial-runcheck-v2.md`
- 用途：供 Agent3 执行的最新计划（覆盖 PRD v1.1 剩余能力）

## 9. LATEST.md 更新信息

- 目标路径：`.ai-workspace/LATEST.md`
- 应写入：`agent2-plan-real-device-scan-recognition-and-serial-runcheck-v2.md`
