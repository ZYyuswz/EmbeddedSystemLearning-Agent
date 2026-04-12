"""后端测试通用夹具。"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture()
def api_token() -> str:
    """返回测试使用的 Bearer Token。"""
    return "test-token"


@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, api_token: str) -> None:
    """为每个测试用例设置隔离的数据库和工作区。"""
    db_path = tmp_path / "board_assistant.db"
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("BOARD_ASSISTANT_API_TOKEN", api_token)
    monkeypatch.setenv("BOARD_ASSISTANT_DB_PATH", str(db_path))
    monkeypatch.setenv("BOARD_ASSISTANT_WORKSPACE", str(workspace_root))

    yield

    os.environ.pop("BOARD_ASSISTANT_API_TOKEN", None)
    os.environ.pop("BOARD_ASSISTANT_DB_PATH", None)
    os.environ.pop("BOARD_ASSISTANT_WORKSPACE", None)


@pytest.fixture()
def client() -> TestClient:
    """创建 FastAPI 测试客户端。"""
    return TestClient(app)


@pytest.fixture()
def auth_headers(api_token: str) -> dict[str, str]:
    """返回携带鉴权头的请求头。"""
    return {"Authorization": f"Bearer {api_token}"}
