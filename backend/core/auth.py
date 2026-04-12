"""鉴权工具。"""
from __future__ import annotations

from fastapi import Header

from backend.core.config import get_settings
from backend.core.errors import AppException, ErrorCode


def require_bearer_token(authorization: str | None = Header(default=None)) -> str:
    """校验 Bearer Token。"""
    settings = get_settings()
    if not authorization or not authorization.startswith("Bearer "):
        raise AppException(ErrorCode.UNAUTHORIZED, "缺少鉴权信息", status_code=401)
    token = authorization.split(" ", 1)[1].strip()
    if token != settings.api_token:
        raise AppException(ErrorCode.UNAUTHORIZED, "Token 无效", status_code=401)
    return token
