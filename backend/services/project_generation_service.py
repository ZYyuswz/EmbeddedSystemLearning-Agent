"""工程生成服务。"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.core.errors import AppException, ErrorCode
from backend.models.schemas import GenerateProjectRequest, GenerateProjectResponse
from backend.repositories.sqlite_repo import SQLiteRepo, now_iso
from backend.services.template_registry import render_project_files, resolve_template


def generate_project(repo: SQLiteRepo, workspace_root: str, request: GenerateProjectRequest) -> GenerateProjectResponse:
    """根据需求生成工程目录与模板文件。"""
    if not request.requirementText.strip():
        raise AppException(ErrorCode.GEN_REQUIREMENT_INVALID, "需求文本不能为空", status_code=422)

    template = resolve_template(repo, request.boardModel, request.framework, request.toolchain)
    if not template:
        raise AppException(ErrorCode.GEN_TEMPLATE_NOT_SUPPORTED, "未找到匹配模板", status_code=422)

    project_id = f"prj_{uuid4().hex[:12]}"
    workspace = Path(workspace_root) / project_id
    workspace.mkdir(parents=True, exist_ok=True)

    rendered_files = render_project_files(
        template,
        {
            "requirementText": request.requirementText,
            "templateOptions": request.templateOptions,
            "boardModel": request.boardModel,
        },
    )
    _write_rendered_files(workspace, rendered_files)

    # 预置一个可被 flash plan 消费的示例产物，方便后续流程联调与回归测试。
    build_dir = workspace / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = build_dir / "firmware.bin"
    artifact_path.write_bytes(b"DEMO_BIN")

    run_check_command = "python3 scripts/check_serial.py --timeout 15"
    build_command = "echo '模拟构建成功'"
    flash_command = "echo '模拟烧录成功'"

    repo.save_project(
        {
            "project_id": project_id,
            "board_model": request.boardModel,
            "knowledge_id": request.knowledgeId,
            "workspace_path": str(workspace),
            "build_command": build_command,
            "flash_command": flash_command,
            "run_check_command": run_check_command,
            "created_at": now_iso(),
        }
    )

    return GenerateProjectResponse(
        projectId=project_id,
        workspacePath=str(workspace),
        buildCommand=build_command,
        flashCommand=flash_command,
        runCheckCommand=run_check_command,
        templateId=template.template_id,
        generatedFiles=sorted(rendered_files.keys()) + ["build/firmware.bin"],
        flashPlanId=None,
    )


def _write_rendered_files(workspace: Path, rendered_files: dict[str, str]) -> None:
    """将模板渲染结果写入工程目录。"""
    for relative_path, content in rendered_files.items():
        file_path = workspace / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
