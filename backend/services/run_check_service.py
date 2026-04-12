"""运行验证服务。"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import serial

from backend.core.errors import AppException, ErrorCode
from backend.models.schemas import RunCheckRequest
from backend.repositories.sqlite_repo import SQLiteRepo, now_iso

_MAX_TRANSCRIPT_LINES = 2000


_PARITY_MAP = {
    "N": serial.PARITY_NONE,
    "E": serial.PARITY_EVEN,
    "O": serial.PARITY_ODD,
    "M": serial.PARITY_MARK,
    "S": serial.PARITY_SPACE,
}

_BYTESIZE_MAP = {
    5: serial.FIVEBITS,
    6: serial.SIXBITS,
    7: serial.SEVENBITS,
    8: serial.EIGHTBITS,
}

_STOPBITS_MAP = {
    1: serial.STOPBITS_ONE,
    2: serial.STOPBITS_TWO,
}


def run_check(
    payload: RunCheckRequest,
    workspace_path: str,
    task_id: str,
    repo: SQLiteRepo,
) -> dict[str, object]:
    """执行串口关键字断言并返回校验报告。"""
    if payload.checkProfile not in {"serial_keyword_assert", "serial_heartbeat"}:
        raise AppException(ErrorCode.RUN_CHECK_PROFILE_INVALID, "不支持的检查档位", status_code=422)

    serial_config = payload.serialConfig
    if not serial_config or not serial_config.port.strip():
        raise AppException(ErrorCode.RUN_CHECK_PORT_OPEN_FAILED, "串口配置缺失或端口为空", status_code=422)

    expect_keywords = _resolve_expect_keywords(payload)
    started_at = now_iso()
    transcript_lines: list[str] = []

    try:
        with serial.Serial(
            port=serial_config.port,
            baudrate=serial_config.baudrate,
            bytesize=_BYTESIZE_MAP[serial_config.bytesize],
            parity=_PARITY_MAP[serial_config.parity],
            stopbits=_STOPBITS_MAP[serial_config.stopbits],
            timeout=0.2,
            write_timeout=serial_config.writeTimeoutSec,
        ) as serial_conn:
            serial_conn.reset_input_buffer()
            serial_conn.reset_output_buffer()

            if payload.probeCommand:
                _send_probe_command(serial_conn, payload.probeCommand)

            deadline = time.monotonic() + payload.timeoutSec
            while time.monotonic() < deadline:
                raw = serial_conn.readline()
                line = raw.decode("utf-8", errors="ignore").strip()
                if line:
                    transcript_lines.append(f"[{_utc_now_text()}] RX {line}")
                if len(transcript_lines) >= _MAX_TRANSCRIPT_LINES:
                    transcript_lines.append(f"[{_utc_now_text()}] 系统提示: 输出超过{_MAX_TRANSCRIPT_LINES}行，已截断")
                    break
                if expect_keywords and _evaluate_assert(transcript_lines, expect_keywords, payload.assertMode):
                    break
    except serial.SerialTimeoutException as exc:
        raise AppException(ErrorCode.RUN_CHECK_WRITE_FAILED, f"串口写入超时: {exc}", status_code=422) from exc
    except serial.SerialException as exc:
        raise AppException(ErrorCode.RUN_CHECK_PORT_OPEN_FAILED, f"串口打开失败: {exc}", status_code=422) from exc

    if not transcript_lines:
        raise AppException(ErrorCode.RUN_CHECK_TIMEOUT, "串口在超时时间内未返回数据", status_code=422)

    matched_keywords = _matched_keywords(transcript_lines, expect_keywords)
    if expect_keywords and not _assert_passed(matched_keywords, expect_keywords, payload.assertMode):
        raise AppException(ErrorCode.RUN_CHECK_KEYWORD_MISSING, "未命中期望关键字", status_code=422)

    transcript_path = _write_transcript(workspace_path, task_id, transcript_lines)
    report_id = f"rcr_{uuid4().hex[:12]}"
    ended_at = now_iso()
    report = {
        "reportId": report_id,
        "taskId": task_id,
        "port": serial_config.port,
        "baudrate": serial_config.baudrate,
        "probeCommand": payload.probeCommand,
        "expectKeywords": expect_keywords,
        "assertMode": payload.assertMode,
        "capturedLines": transcript_lines,
        "matchedKeywords": matched_keywords,
        "passed": True,
        "failureReason": None,
        "startedAt": started_at,
        "endedAt": ended_at,
    }
    repo.save_serial_run_check_report(report)

    return {
        "report": "串口关键字校验通过",
        "serialTranscriptPath": str(transcript_path),
        "matchedKeywords": matched_keywords,
    }


def _send_probe_command(serial_conn: serial.Serial, probe_command: str) -> None:
    """发送探测命令到串口。"""
    try:
        serial_conn.write(probe_command.encode("utf-8"))
        serial_conn.flush()
    except serial.SerialTimeoutException:
        raise
    except serial.SerialException as exc:
        raise AppException(ErrorCode.RUN_CHECK_WRITE_FAILED, f"串口写入失败: {exc}", status_code=422) from exc


def _resolve_expect_keywords(payload: RunCheckRequest) -> list[str]:
    """解析期望关键字列表。"""
    cleaned = [item.strip() for item in payload.expectKeywords if item and item.strip()]
    if cleaned:
        return cleaned
    if payload.checkProfile == "serial_heartbeat":
        return ["heartbeat"]
    return []


def _evaluate_assert(lines: list[str], keywords: list[str], mode: str) -> bool:
    """判断当前日志是否已经满足断言。"""
    matched = _matched_keywords(lines, keywords)
    return _assert_passed(matched, keywords, mode)


def _matched_keywords(lines: list[str], keywords: list[str]) -> list[str]:
    """返回已命中的关键字列表。"""
    full_text = "\n".join(lines).lower()
    return [word for word in keywords if word.lower() in full_text]


def _assert_passed(matched_keywords: list[str], expected_keywords: list[str], mode: str) -> bool:
    """根据断言模式判断是否通过。"""
    if not expected_keywords:
        return True
    if mode == "any":
        return len(matched_keywords) > 0
    return len(matched_keywords) == len(expected_keywords)


def _write_transcript(workspace_path: str, task_id: str, lines: list[str]) -> Path:
    """落盘串口 transcript 日志。"""
    report_dir = Path(workspace_path) / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = report_dir / f"{task_id}_serial_transcript.log"
    transcript_path.write_text("\n".join(lines), encoding="utf-8")
    return transcript_path


def _utc_now_text() -> str:
    """返回当前 UTC 时间文本。"""
    return datetime.now(timezone.utc).isoformat()
