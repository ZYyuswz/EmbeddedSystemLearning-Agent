"""安全策略服务。"""
from __future__ import annotations

from backend.core.errors import AppException, ErrorCode
from backend.repositories.sqlite_repo import SQLiteRepo


def check_flash_policy(
    repo: SQLiteRepo,
    board_model: str,
    programmer: str,
    command: str,
    parameter_sources: dict[str, str] | None = None,
) -> None:
    """校验烧录安全策略。"""
    _ = parameter_sources
    policy = repo.get_safety_policy(board_model)
    if not policy:
        return
    if programmer and programmer not in policy["allowedProgrammers"]:
        raise AppException(ErrorCode.FLASH_TOOL_NOT_FOUND, "当前烧录器不在允许列表", status_code=422)
    for forbidden in policy["forbiddenCommands"]:
        if forbidden and forbidden in command:
            raise AppException(ErrorCode.FLASH_FAILED, "烧录命令触发安全禁令", status_code=422)
