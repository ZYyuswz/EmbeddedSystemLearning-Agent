"""前端后端 API 客户端。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class BackendApiClient:
    """封装板卡助手后端调用。"""

    base_url: str
    token: str
    timeout_sec: int = 20

    def _headers(self) -> dict[str, str]:
        """构造鉴权请求头。"""
        return {"Authorization": f"Bearer {self.token}"}

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """执行 POST 请求。"""
        with httpx.Client(timeout=self.timeout_sec) as client:
            response = client.post(f"{self.base_url}{path}", headers=self._headers(), json=payload)
        return self._unwrap(response)

    def _get(self, path: str) -> dict[str, Any]:
        """执行 GET 请求。"""
        with httpx.Client(timeout=self.timeout_sec) as client:
            response = client.get(f"{self.base_url}{path}", headers=self._headers())
        return self._unwrap(response)

    def _unwrap(self, response: httpx.Response) -> dict[str, Any]:
        """统一处理响应与错误。"""
        data: dict[str, Any]
        try:
            data = response.json()
            if not isinstance(data, dict):
                data = {"raw": str(data)}
        except ValueError:
            data = {"raw": response.text}
        if response.status_code >= 400:
            code = data.get("errorCode", "UNKNOWN")
            message = data.get("message") or data.get("raw") or "请求失败"
            raise RuntimeError(f"{code}: {message}")
        return data

    def detect_board(self, payload: dict[str, Any]) -> dict[str, Any]:
        """调用板卡识别接口。"""
        return self._post("/api/v1/boards/detect", payload)

    def identify_board(self, payload: dict[str, Any]) -> dict[str, Any]:
        """调用板卡二次识别接口。"""
        return self._post("/api/v1/boards/identify", payload)

    def sync_knowledge(self, payload: dict[str, Any]) -> dict[str, Any]:
        """调用资料同步接口。"""
        return self._post("/api/v1/boards/knowledge/sync", payload)

    def generate_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        """调用项目生成接口。"""
        return self._post("/api/v1/projects/generate", payload)

    def flash_project(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """调用烧录接口。"""
        return self._post(f"/api/v1/projects/{project_id}/flash", payload)

    def plan_flash(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """调用烧录规划接口。"""
        return self._post(f"/api/v1/projects/{project_id}/flash/plan", payload)

    def run_check(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """调用运行验证接口。"""
        return self._post(f"/api/v1/projects/{project_id}/run-check", payload)

    def get_task(self, task_id: str) -> dict[str, Any]:
        """查询任务详情。"""
        return self._get(f"/api/v1/tasks/{task_id}")

    def run_evaluation(self, payload: dict[str, Any]) -> dict[str, Any]:
        """调用评估运行接口。"""
        return self._post("/api/v1/evaluations/prototype/run", payload)

    def generate_eval_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        """调用评估报告接口。"""
        return self._post("/api/v1/evaluations/reports/generate", payload)
