"""SQLite 数据访问层。"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator


@dataclass
class SQLiteRepo:
    """SQLite 仓储实现。"""

    db_path: str

    def __post_init__(self) -> None:
        """确保数据库目录存在并初始化结构。"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()
        self.init_default_safety_policy()
        self.init_default_template_registry()

    @contextmanager
    def conn(self) -> Generator[sqlite3.Connection, None, None]:
        """提供事务连接上下文。"""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def init_schema(self) -> None:
        """初始化数据库表结构。"""
        schema_path = Path(__file__).with_name("schema.sql")
        with self.conn() as connection:
            connection.executescript(schema_path.read_text(encoding="utf-8"))
            self._apply_compat_migrations(connection)

    def _apply_compat_migrations(self, connection: sqlite3.Connection) -> None:
        """执行向后兼容迁移，保证旧库可用。"""
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(project_tasks)").fetchall()}
        if "cwd" not in columns:
            connection.execute("ALTER TABLE project_tasks ADD COLUMN cwd TEXT")

    def init_default_safety_policy(self) -> None:
        """写入默认烧录安全策略。"""
        policies = [
            ("STM32F103C8T6-BluePill", 1, ["stlink", "uart_bootloader"], ["rm -rf /"], 1),
            ("ESP32-DevKitC", 1, ["esptool"], ["erase_flash_all"], 1),
        ]
        with self.conn() as connection:
            for board_model, require_confirm, allowed, forbidden, retry in policies:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO safety_policies(
                        board_model, requires_confirm_before_flash, allowed_programmers_json,
                        forbidden_commands_json, max_flash_retry
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (board_model, require_confirm, json.dumps(allowed), json.dumps(forbidden), retry),
                )

    def init_default_template_registry(self) -> None:
        """写入默认工程模板注册信息。"""
        templates = [
            (
                "stm32f1-stdc-make-v1",
                "stm32f1",
                "baremetal",
                "make",
                "v1",
                ["src/main.c", "Makefile", "scripts/check_serial.py"],
                "active",
            ),
            (
                "esp32-idf-cmake-v1",
                "esp32",
                "esp-idf",
                "cmake",
                "v1",
                ["main/main.c", "CMakeLists.txt", "scripts/check_serial.py"],
                "active",
            ),
        ]
        with self.conn() as connection:
            for template in templates:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO project_template_registry(
                        template_id, board_family, framework, toolchain, template_version, entry_files_json, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        template[0],
                        template[1],
                        template[2],
                        template[3],
                        template[4],
                        json.dumps(template[5], ensure_ascii=False),
                        template[6],
                    ),
                )

    def save_project(self, project: dict[str, Any]) -> None:
        """保存项目记录。"""
        with self.conn() as connection:
            connection.execute(
                """
                INSERT INTO projects(project_id, board_model, knowledge_id, workspace_path,
                build_command, flash_command, run_check_command, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project["project_id"],
                    project["board_model"],
                    project["knowledge_id"],
                    project["workspace_path"],
                    project["build_command"],
                    project["flash_command"],
                    project["run_check_command"],
                    project["created_at"],
                ),
            )

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        """读取项目记录。"""
        with self.conn() as connection:
            row = connection.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        return dict(row) if row else None

    def save_source_refs(self, board_profile_id: str, sources: list[dict[str, Any]]) -> None:
        """保存资料来源记录。"""
        with self.conn() as connection:
            for source in sources:
                connection.execute(
                    """
                    INSERT INTO source_refs(board_profile_id, url, source_type, fetched_at, version_tag, checksum)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        board_profile_id,
                        source["url"],
                        source["sourceType"],
                        source["fetchedAt"],
                        source.get("versionTag"),
                        source.get("checksum"),
                    ),
                )

    def create_task(self, task: dict[str, Any]) -> None:
        """创建任务记录。"""
        with self.conn() as connection:
            connection.execute(
                """
                INSERT INTO project_tasks(task_id, project_id, task_type, status, command, cwd,
                logs_json, artifacts_json, error_code, started_at, ended_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task["task_id"],
                    task["project_id"],
                    task["task_type"],
                    task["status"],
                    task["command"],
                    task.get("cwd"),
                    json.dumps(task.get("logs", []), ensure_ascii=False),
                    json.dumps(task.get("artifacts", {}), ensure_ascii=False),
                    task.get("error_code"),
                    task.get("started_at"),
                    task.get("ended_at"),
                ),
            )

    def update_task(
        self,
        task_id: str,
        *,
        status: str | None = None,
        logs: list[str] | None = None,
        artifacts: dict[str, Any] | None = None,
        error_code: str | None = None,
        ended_at: str | None = None,
    ) -> None:
        """更新任务记录。"""
        with self.conn() as connection:
            current = self.get_task(task_id)
            if not current:
                return
            next_status = status or current["status"]
            next_logs = logs if logs is not None else current["logs"]
            next_artifacts = artifacts if artifacts is not None else current["artifacts"]
            next_error = error_code if error_code is not None else current["errorCode"]
            next_ended = ended_at if ended_at is not None else current["endedAt"]
            connection.execute(
                """
                UPDATE project_tasks
                SET status = ?, logs_json = ?, artifacts_json = ?, error_code = ?, ended_at = ?
                WHERE task_id = ?
                """,
                (
                    next_status,
                    json.dumps(next_logs, ensure_ascii=False),
                    json.dumps(next_artifacts, ensure_ascii=False),
                    next_error,
                    next_ended,
                    task_id,
                ),
            )

    def append_task_log(self, task_id: str, line: str) -> None:
        """追加任务日志。"""
        task = self.get_task(task_id)
        if not task:
            return
        logs = task["logs"]
        logs.append(line)
        self.update_task(task_id, logs=logs)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """读取任务详情。"""
        with self.conn() as connection:
            row = connection.execute("SELECT * FROM project_tasks WHERE task_id = ?", (task_id,)).fetchone()
        if not row:
            return None
        return {
            "taskId": row["task_id"],
            "projectId": row["project_id"],
            "taskType": row["task_type"],
            "status": row["status"],
            "command": row["command"],
            "cwd": row["cwd"],
            "logs": json.loads(row["logs_json"]),
            "artifacts": json.loads(row["artifacts_json"]),
            "errorCode": row["error_code"],
            "startedAt": _parse_dt(row["started_at"]),
            "endedAt": _parse_dt(row["ended_at"]),
        }

    def get_safety_policy(self, board_model: str) -> dict[str, Any] | None:
        """读取烧录安全策略。"""
        with self.conn() as connection:
            row = connection.execute("SELECT * FROM safety_policies WHERE board_model = ?", (board_model,)).fetchone()
        if not row:
            return None
        return {
            "boardModel": row["board_model"],
            "requiresConfirmBeforeFlash": bool(row["requires_confirm_before_flash"]),
            "allowedProgrammers": json.loads(row["allowed_programmers_json"]),
            "forbiddenCommands": json.loads(row["forbidden_commands_json"]),
            "maxFlashRetry": row["max_flash_retry"],
        }

    def save_probe_snapshot(self, snapshot: dict[str, Any]) -> None:
        """保存设备探测快照。"""
        with self.conn() as connection:
            connection.execute(
                """
                INSERT INTO device_probe_snapshots(request_id, serial_ports_json, usb_devices_json, scanned_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    snapshot["request_id"],
                    json.dumps(snapshot.get("serial_ports", []), ensure_ascii=False),
                    json.dumps(snapshot.get("usb_devices", []), ensure_ascii=False),
                    now_iso(),
                ),
            )

    def get_probe_snapshot(self, request_id: str) -> dict[str, Any] | None:
        """按请求 ID 查询设备快照。"""
        with self.conn() as connection:
            row = connection.execute(
                """
                SELECT request_id, serial_ports_json, usb_devices_json, scanned_at
                FROM device_probe_snapshots
                WHERE request_id = ?
                ORDER BY probe_id DESC
                LIMIT 1
                """,
                (request_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "requestId": row["request_id"],
            "serialPorts": json.loads(row["serial_ports_json"]),
            "usbDevices": json.loads(row["usb_devices_json"]),
            "scannedAt": row["scanned_at"],
        }

    def save_match_trace(self, request_id: str, candidates: list[Any], need_confirm: bool, decision: str) -> None:
        """保存板卡匹配评分轨迹。"""
        with self.conn() as connection:
            for candidate in candidates:
                connection.execute(
                    """
                    INSERT INTO board_match_traces(
                        request_id, candidate_model, score, signal_breakdown_json, decision, need_confirm, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request_id,
                        getattr(candidate, "model", ""),
                        float(getattr(candidate, "score", 0.0)),
                        json.dumps(getattr(candidate, "signals", {}), ensure_ascii=False, default=lambda x: x.model_dump()),
                        decision,
                        1 if need_confirm else 0,
                        now_iso(),
                    ),
                )

    def save_serial_run_check_report(self, report: dict[str, Any]) -> None:
        """保存串口运行校验报告。"""
        with self.conn() as connection:
            connection.execute(
                """
                INSERT INTO serial_run_check_reports(
                    report_id, task_id, port, baudrate, probe_command, expect_keywords_json,
                    assert_mode, captured_lines_json, matched_keywords_json, passed,
                    failure_reason, started_at, ended_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report["reportId"],
                    report["taskId"],
                    report["port"],
                    report["baudrate"],
                    report.get("probeCommand", ""),
                    json.dumps(report.get("expectKeywords", []), ensure_ascii=False),
                    report.get("assertMode", "all"),
                    json.dumps(report.get("capturedLines", []), ensure_ascii=False),
                    json.dumps(report.get("matchedKeywords", []), ensure_ascii=False),
                    1 if report.get("passed") else 0,
                    report.get("failureReason"),
                    report["startedAt"],
                    report["endedAt"],
                ),
            )

    def get_knowledge_cache(self, cache_key: str) -> dict[str, Any] | None:
        """读取资料同步缓存。"""
        with self.conn() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_cache_entries WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
        if not row:
            return None
        return {
            "cacheKey": row["cache_key"],
            "boardModel": row["board_model"],
            "payload": json.loads(row["payload_json"]),
            "sourceDigest": row["source_digest"],
            "ttlSec": row["ttl_sec"],
            "fetchedAt": row["fetched_at"],
            "expiresAt": row["expires_at"],
        }

    def save_knowledge_cache(
        self,
        cache_key: str,
        board_model: str,
        payload: dict[str, Any],
        source_digest: str,
        ttl_sec: int,
    ) -> None:
        """写入资料同步缓存。"""
        fetched_at = now_iso()
        expires_at = datetime.fromisoformat(fetched_at).timestamp() + ttl_sec
        expires_at_iso = datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()
        with self.conn() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_cache_entries(
                    cache_key, board_model, payload_json, source_digest, ttl_sec, fetched_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    source_digest=excluded.source_digest,
                    ttl_sec=excluded.ttl_sec,
                    fetched_at=excluded.fetched_at,
                    expires_at=excluded.expires_at
                """,
                (
                    cache_key,
                    board_model,
                    json.dumps(payload, ensure_ascii=False),
                    source_digest,
                    ttl_sec,
                    fetched_at,
                    expires_at_iso,
                ),
            )

    def find_template(self, board_family: str, framework: str, toolchain: str) -> dict[str, Any] | None:
        """按维度查询模板注册记录。"""
        with self.conn() as connection:
            row = connection.execute(
                """
                SELECT * FROM project_template_registry
                WHERE board_family = ? AND framework = ? AND toolchain = ? AND status = 'active'
                LIMIT 1
                """,
                (board_family, framework, toolchain),
            ).fetchone()
        if not row:
            return None
        return {
            "templateId": row["template_id"],
            "boardFamily": row["board_family"],
            "framework": row["framework"],
            "toolchain": row["toolchain"],
            "templateVersion": row["template_version"],
            "entryFiles": json.loads(row["entry_files_json"]),
            "status": row["status"],
        }

    def save_flash_plan(
        self,
        flash_plan_id: str,
        project_id: str,
        tool: str,
        command: str,
        parameter_sources: dict[str, str],
        explain: str,
    ) -> None:
        """保存烧录计划。"""
        with self.conn() as connection:
            connection.execute(
                """
                INSERT INTO flash_plans(
                    flash_plan_id, project_id, tool, command, parameter_sources_json, explain, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    flash_plan_id,
                    project_id,
                    tool,
                    command,
                    json.dumps(parameter_sources, ensure_ascii=False),
                    explain,
                    now_iso(),
                ),
            )

    def get_flash_plan(self, flash_plan_id: str) -> dict[str, Any] | None:
        """读取烧录计划。"""
        with self.conn() as connection:
            row = connection.execute(
                "SELECT * FROM flash_plans WHERE flash_plan_id = ?",
                (flash_plan_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "flashPlanId": row["flash_plan_id"],
            "projectId": row["project_id"],
            "tool": row["tool"],
            "command": row["command"],
            "parameterSources": json.loads(row["parameter_sources_json"]),
            "explain": row["explain"],
            "createdAt": row["created_at"],
        }

    def save_evaluation_report(self, report: dict[str, Any]) -> None:
        """保存评估报告。"""
        with self.conn() as connection:
            connection.execute(
                """
                INSERT INTO evaluation_reports(report_id, evaluation_task_id, project_id, board_platform,
                feasibility_level, metrics_json, findings_json, improvement_proposals_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report["report_id"],
                    report["evaluation_task_id"],
                    report["project_id"],
                    report["board_platform"],
                    report["feasibility_level"],
                    json.dumps(report["metrics"], ensure_ascii=False),
                    json.dumps(report["findings"], ensure_ascii=False),
                    json.dumps(report["improvement_proposals"], ensure_ascii=False),
                    report["created_at"],
                ),
            )

    def create_evaluation_task(self, task: dict[str, Any]) -> None:
        """创建评估任务记录。"""
        with self.conn() as connection:
            connection.execute(
                """
                INSERT INTO evaluation_tasks(
                    evaluation_task_id, project_id, board_platform, scenario_name,
                    checklist_json, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task["evaluation_task_id"],
                    task["project_id"],
                    task["board_platform"],
                    task["scenario_name"],
                    json.dumps(task["checklist"], ensure_ascii=False),
                    task["status"],
                    task["created_at"],
                ),
            )

    def get_evaluation_task(self, evaluation_task_id: str) -> dict[str, Any] | None:
        """查询评估任务记录。"""
        with self.conn() as connection:
            row = connection.execute(
                "SELECT * FROM evaluation_tasks WHERE evaluation_task_id = ?",
                (evaluation_task_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "evaluationTaskId": row["evaluation_task_id"],
            "projectId": row["project_id"],
            "boardPlatform": row["board_platform"],
            "scenarioName": row["scenario_name"],
            "checklist": json.loads(row["checklist_json"]),
            "status": row["status"],
            "createdAt": _parse_dt(row["created_at"]),
        }


def now_iso() -> str:
    """返回 UTC ISO 时间。"""
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    """解析 ISO 时间字符串。"""
    if not value:
        return None
    return datetime.fromisoformat(value)
