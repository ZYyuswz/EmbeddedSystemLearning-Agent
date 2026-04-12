"""烧录服务。"""
from __future__ import annotations

import shlex
import shutil
from pathlib import Path
from uuid import uuid4

from backend.core.errors import AppException, ErrorCode
from backend.models.schemas import FlashPlanRequest, FlashPlanResponse, FlashProjectRequest
from backend.repositories.sqlite_repo import SQLiteRepo
from backend.worker.executor import run_command


def build_flash_plan(
    repo: SQLiteRepo,
    project_id: str,
    board_model: str,
    workspace_path: str,
    payload: FlashPlanRequest,
) -> FlashPlanResponse:
    """构建可审计烧录计划。"""
    artifact_path = _resolve_artifact_path(workspace_path, payload.artifactPath)
    if not artifact_path.exists():
        raise AppException(ErrorCode.FLASH_PLAN_ARTIFACT_MISSING, "缺少可烧录产物文件", status_code=422)

    tool = _resolve_tool(board_model, payload.preferredTool)
    _ensure_tool_available(tool)

    command, explain, sources = _render_command(tool, artifact_path, payload)
    flash_plan_id = f"fpl_{uuid4().hex[:12]}"
    repo.save_flash_plan(flash_plan_id, project_id, tool, command, sources, explain)
    return FlashPlanResponse(
        flashPlanId=flash_plan_id,
        tool=tool,
        command=command,
        explain=explain,
        parameterSources=sources,
        requiresConfirm=True,
    )


def flash_project(command: str, request: FlashProjectRequest, timeout_sec: int) -> dict[str, object]:
    """执行烧录或 dry-run。"""
    if request.dryRun:
        return {"ok": True, "message": "已执行 dry-run", "artifacts": {"command": command}}
    result = run_command(command, timeout_sec)
    if not result.ok:
        raise AppException(
            ErrorCode.FLASH_FAILED,
            f"烧录失败: {result.stderr or result.stdout or '未知错误'}",
            status_code=500,
        )
    return {"ok": True, "message": "烧录成功", "artifacts": {"flashLog": result.stdout, "command": command}}


def _resolve_artifact_path(workspace_path: str, artifact_path: str | None) -> Path:
    """解析烧录产物路径。"""
    workspace = Path(workspace_path)
    if artifact_path:
        path = Path(artifact_path)
        return path if path.is_absolute() else workspace / artifact_path
    return workspace / "build" / "firmware.bin"


def _resolve_tool(board_model: str, preferred_tool: str | None) -> str:
    """根据板卡型号确定烧录工具。"""
    if preferred_tool:
        return preferred_tool
    lowered = board_model.lower()
    if "esp32" in lowered:
        return "esptool"
    if "stm32" in lowered or "bluepill" in lowered:
        return "stlink"
    raise AppException(ErrorCode.FLASH_PLAN_UNSUPPORTED_BOARD, "当前板卡暂不支持自动烧录规划", status_code=422)


def _ensure_tool_available(tool: str) -> None:
    """检查工具链可用性。"""
    binary = {
        "esptool": "esptool.py",
        "openocd": "openocd",
        "stlink": "st-flash",
    }.get(tool, tool)
    if shutil.which(binary):
        return
    if tool == "stlink":
        # stlink 工具在很多开发机上不预装，保留降级能力但仍记录为可审计命令。
        return
    raise AppException(ErrorCode.FLASH_PLAN_TOOL_NOT_FOUND, f"烧录工具不存在: {binary}", status_code=422)


def _render_command(tool: str, artifact_path: Path, payload: FlashPlanRequest) -> tuple[str, str, dict[str, str]]:
    """渲染工具对应的命令与参数来源。"""
    quoted_artifact = shlex.quote(str(artifact_path))
    sources = {
        "artifact": "request.artifactPath or default(build/firmware.bin)",
        "port": "request.port",
        "baudrate": "request.baudrate",
        "eraseMode": "request.eraseMode",
    }

    if tool == "esptool":
        port = payload.port or "/dev/ttyUSB0"
        command = f"esptool.py --chip esp32 --port {shlex.quote(port)} --baud {payload.baudrate} write_flash 0x1000 {quoted_artifact}"
        explain = "使用 esptool 写入 ESP32 固件"
        return command, explain, sources

    if tool == "openocd":
        command = f"openocd -f interface/stlink.cfg -f target/stm32f1x.cfg -c \"program {quoted_artifact} verify reset exit\""
        explain = "使用 openocd 通过 ST-Link 烧录"
        return command, explain, sources

    if tool == "stlink":
        command = f"st-flash --reset write {quoted_artifact} 0x8000000"
        explain = "使用 st-flash 烧录 STM32 固件"
        return command, explain, sources

    raise AppException(ErrorCode.FLASH_PLAN_TOOL_NOT_FOUND, f"不支持的烧录工具: {tool}", status_code=422)
