"""任务查询路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.auth import require_bearer_token
from backend.core.config import get_settings
from backend.core.errors import AppException, ErrorCode
from backend.models.schemas import TaskDetailResponse
from backend.repositories.sqlite_repo import SQLiteRepo

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(require_bearer_token)])


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task_detail(task_id: str) -> TaskDetailResponse:
    """查询任务详情。"""
    repo = SQLiteRepo(get_settings().db_path)
    task = repo.get_task(task_id)
    if not task:
        raise AppException(ErrorCode.NOT_FOUND, "任务不存在", status_code=404)
    return TaskDetailResponse(**task)
