"""后端配置模块。"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """应用运行配置。"""

    api_token: str
    db_path: str
    workspace_root: str
    detect_confidence_threshold: float
    default_timeout_sec: int


def get_settings() -> Settings:
    """读取环境变量并返回配置对象。"""
    return Settings(
        api_token=os.getenv("BOARD_ASSISTANT_API_TOKEN", "dev-token"),
        db_path=os.getenv("BOARD_ASSISTANT_DB_PATH", "data/board_assistant.db"),
        workspace_root=os.getenv("BOARD_ASSISTANT_WORKSPACE", "data/workspaces"),
        detect_confidence_threshold=float(os.getenv("BOARD_DETECT_CONFIDENCE", "0.8")),
        default_timeout_sec=int(os.getenv("BOARD_DEFAULT_TIMEOUT_SEC", "20")),
    )
