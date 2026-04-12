"""任务管理服务。"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from backend.repositories.sqlite_repo import SQLiteRepo, now_iso


def create_task(
    repo: SQLiteRepo,
    project_id: str,
    task_type: str,
    command: str,
    cwd: str | None = None,
) -> dict[str, str]:
    """创建任务并写入初始状态。"""
    task_id = f"task_{uuid4().hex[:12]}"
    repo.create_task(
        {
            "task_id": task_id,
            "project_id": project_id,
            "task_type": task_type,
            "status": "running",
            "command": command,
            "cwd": cwd,
            "logs": [f"开始执行任务: {task_type}"],
            "artifacts": {},
            "started_at": now_iso(),
            "ended_at": None,
        }
    )
    return {"taskId": task_id, "status": "running", "startedAt": now_iso()}


def append_log(repo: SQLiteRepo, task_id: str, line: str) -> None:
    """追加任务日志。"""
    repo.append_task_log(task_id, line)


def finish_task(repo: SQLiteRepo, task_id: str, artifacts: dict[str, Any] | None = None) -> None:
    """结束任务并标记成功。"""
    repo.update_task(task_id, status="success", artifacts=artifacts or {}, ended_at=now_iso())


def fail_task(repo: SQLiteRepo, task_id: str, error_code: str, line: str) -> None:
    """结束任务并标记失败。"""
    task = repo.get_task(task_id)
    logs = task["logs"] if task else []
    logs.append(line)
    repo.update_task(task_id, status="failed", logs=logs, error_code=error_code, ended_at=now_iso())


def get_task(repo: SQLiteRepo, task_id: str) -> dict | None:
    """获取任务详情。"""
    return repo.get_task(task_id)
