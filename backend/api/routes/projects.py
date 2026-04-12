"""项目相关路由。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from backend.core.auth import require_bearer_token
from backend.core.config import get_settings
from backend.core.errors import AppException, ErrorCode
from backend.models.schemas import (
    FlashPlanRequest,
    FlashPlanResponse,
    FlashProjectRequest,
    GenerateProjectRequest,
    GenerateProjectResponse,
    RunCheckRequest,
    TaskStartResponse,
)
from backend.repositories.sqlite_repo import SQLiteRepo
from backend.services.flash_service import build_flash_plan, flash_project
from backend.services.project_generation_service import generate_project
from backend.services.run_check_service import run_check
from backend.services.safety_service import check_flash_policy
from backend.services.task_service import append_log, create_task, fail_task, finish_task

router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[Depends(require_bearer_token)])


def _repo() -> SQLiteRepo:
    """创建仓储实例。"""
    return SQLiteRepo(get_settings().db_path)


@router.post("/generate", response_model=GenerateProjectResponse)
def generate_project_route(payload: GenerateProjectRequest) -> GenerateProjectResponse:
    """生成项目。"""
    settings = get_settings()
    return generate_project(_repo(), settings.workspace_root, payload)


@router.post("/{project_id}/flash/plan", response_model=FlashPlanResponse)
def plan_flash_route(project_id: str, payload: FlashPlanRequest) -> FlashPlanResponse:
    """生成烧录计划。"""
    repo = _repo()
    project = repo.get_project(project_id)
    if not project:
        raise AppException(ErrorCode.NOT_FOUND, "项目不存在", status_code=404)
    return build_flash_plan(repo, project_id, str(project["board_model"]), str(project["workspace_path"]), payload)


@router.post("/{project_id}/flash", response_model=TaskStartResponse)
def flash_project_route(project_id: str, payload: FlashProjectRequest) -> TaskStartResponse:
    """执行烧录任务。"""
    if not payload.userConfirmedRisk:
        raise AppException(ErrorCode.FLASH_CONFIRMATION_REQUIRED, "烧录前需要用户确认风险", status_code=422)

    repo = _repo()
    project = repo.get_project(project_id)
    if not project:
        raise AppException(ErrorCode.NOT_FOUND, "项目不存在", status_code=404)

    command = str(project["flash_command"])
    parameter_sources: dict[str, str] | None = None
    if payload.flashPlanId:
        plan = repo.get_flash_plan(payload.flashPlanId)
        if not plan or plan["projectId"] != project_id:
            raise AppException(ErrorCode.NOT_FOUND, "烧录计划不存在或不属于当前项目", status_code=404)
        command = str(plan["command"])
        parameter_sources = plan["parameterSources"]

    check_flash_policy(repo, str(project["board_model"]), payload.programmer, command, parameter_sources)

    task = create_task(repo, project_id, "flash", command)
    try:
        append_log(repo, task["taskId"], "开始执行烧录")
        result = flash_project(command, payload, get_settings().default_timeout_sec)
        append_log(repo, task["taskId"], str(result["message"]))
        finish_task(repo, task["taskId"], artifacts=result.get("artifacts", {}))
    except AppException as exc:
        fail_task(repo, task["taskId"], exc.code.value, exc.message)
        raise

    return TaskStartResponse(taskId=task["taskId"], status="success", startedAt=datetime.fromisoformat(task["startedAt"]))


@router.post("/{project_id}/run-check", response_model=TaskStartResponse)
def run_check_route(project_id: str, payload: RunCheckRequest) -> TaskStartResponse:
    """执行运行验证任务。"""
    repo = _repo()
    project = repo.get_project(project_id)
    if not project:
        raise AppException(ErrorCode.NOT_FOUND, "项目不存在", status_code=404)

    workspace_path = str(project["workspace_path"])
    task = create_task(repo, project_id, "run_check", str(project["run_check_command"]), cwd=workspace_path)
    try:
        append_log(repo, task["taskId"], "开始执行运行校验")
        result = run_check(payload, workspace_path, task["taskId"], repo)
        finish_task(
            repo,
            task["taskId"],
            artifacts={
                "report": str(result["report"]),
                "serialTranscriptPath": str(result["serialTranscriptPath"]),
                "matchedKeywords": result["matchedKeywords"],
            },
        )
    except AppException as exc:
        fail_task(repo, task["taskId"], exc.code.value, exc.message)
        raise

    return TaskStartResponse(taskId=task["taskId"], status="success", startedAt=datetime.fromisoformat(task["startedAt"]))
