"""USB 设备扫描器。"""
from __future__ import annotations

import json
import platform
import re
import subprocess
from typing import Any

from backend.core.errors import AppException, ErrorCode


def scan_usb_devices() -> list[dict[str, str]]:
    """按平台扫描 USB 设备信息。"""
    system = platform.system().lower()
    try:
        if system == "darwin":
            return _scan_macos_usb()
        if system == "linux":
            return _scan_linux_usb()
        if system == "windows":
            return _scan_windows_usb()
        return []
    except AppException:
        raise
    except Exception as exc:  # pragma: no cover - 防御性兜底
        raise AppException(ErrorCode.BOARD_DETECT_SCAN_FAILED, f"USB 设备扫描失败: {exc}", status_code=500) from exc


def _scan_macos_usb() -> list[dict[str, str]]:
    """通过 macOS system_profiler 获取 USB 设备。"""
    result = subprocess.run(
        ["system_profiler", "SPUSBDataType", "-json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AppException(ErrorCode.BOARD_DETECT_SCAN_FAILED, "system_profiler 执行失败", status_code=500)
    payload = json.loads(result.stdout or "{}")
    root_nodes = payload.get("SPUSBDataType", [])
    devices: list[dict[str, str]] = []

    def walk(node: dict[str, Any], location_prefix: str = "") -> None:
        location = str(node.get("location_id", location_prefix) or "")
        vid, pid = _extract_vid_pid_from_text(str(node.get("vendor_id", "")))
        if node.get("_name") and (vid or pid):
            devices.append(
                {
                    "vid": vid,
                    "pid": pid,
                    "manufacturer": str(node.get("manufacturer", "")),
                    "product": str(node.get("_name", "")),
                    "serialNumber": str(node.get("serial_num", "")),
                    "location": location,
                }
            )
        for child in node.get("_items", []) or []:
            if isinstance(child, dict):
                walk(child, location)

    for item in root_nodes:
        if isinstance(item, dict):
            walk(item)
    return devices


def _scan_linux_usb() -> list[dict[str, str]]:
    """通过 lsusb 获取 Linux USB 设备。"""
    result = subprocess.run(["lsusb"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "not found" in stderr.lower():
            return []
        raise AppException(ErrorCode.BOARD_DETECT_SCAN_FAILED, "lsusb 执行失败", status_code=500)

    devices: list[dict[str, str]] = []
    pattern = re.compile(r"^Bus\s+(\d+)\s+Device\s+(\d+):\s+ID\s+([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\s*(.*)$")
    for line in result.stdout.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        bus, device, vid, pid, desc = match.groups()
        devices.append(
            {
                "vid": vid.lower(),
                "pid": pid.lower(),
                "manufacturer": "",
                "product": desc.strip(),
                "serialNumber": "",
                "location": f"bus-{bus}-device-{device}",
            }
        )
    return devices


def _scan_windows_usb() -> list[dict[str, str]]:
    """通过 PowerShell 获取 Windows USB 设备。"""
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-CimInstance Win32_PnPEntity | "
        "Where-Object {$_.PNPDeviceID -like 'USB\\VID_*'} | "
        "Select-Object Name,Manufacturer,PNPDeviceID | ConvertTo-Json",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return []

    raw = result.stdout.strip()
    if not raw:
        return []

    parsed = json.loads(raw)
    rows = parsed if isinstance(parsed, list) else [parsed]
    devices: list[dict[str, str]] = []
    regex = re.compile(r"VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})")
    for row in rows:
        pnp_id = str(row.get("PNPDeviceID", ""))
        matched = regex.search(pnp_id)
        if not matched:
            continue
        vid, pid = matched.groups()
        devices.append(
            {
                "vid": vid.lower(),
                "pid": pid.lower(),
                "manufacturer": str(row.get("Manufacturer", "")),
                "product": str(row.get("Name", "")),
                "serialNumber": "",
                "location": pnp_id,
            }
        )
    return devices


def _extract_vid_pid_from_text(text: str) -> tuple[str, str]:
    """从文本中提取 VID/PID。"""
    matched = re.search(r"0x([0-9A-Fa-f]{4})\s*\(?(?:[^)]*)?\)?", text)
    if not matched:
        return "", ""
    vid = matched.group(1).lower()
    tail = text[matched.end():]
    matched_pid = re.search(r"0x([0-9A-Fa-f]{4})", tail)
    pid = matched_pid.group(1).lower() if matched_pid else ""
    return vid, pid
