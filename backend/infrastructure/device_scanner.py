"""设备扫描基础设施。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import serial.tools.list_ports

from backend.core.errors import AppException, ErrorCode
from backend.infrastructure.usb_scanner import scan_usb_devices


@dataclass
class DeviceProbeResult:
    """扫描结果。"""

    usb_vid: str
    usb_pid: str
    serial_ports: list[str]
    serial_port_details: list[dict[str, Any]] = field(default_factory=list)
    usb_devices: list[dict[str, str]] = field(default_factory=list)


def scan_usb() -> tuple[str, str, list[dict[str, str]]]:
    """扫描 USB 设备信息。"""
    devices = scan_usb_devices()
    if devices:
        first = devices[0]
        return first.get("vid", ""), first.get("pid", ""), devices
    return "", "", []


def scan_serial_ports() -> tuple[list[str], list[dict[str, Any]]]:
    """扫描串口设备列表。"""
    ports: list[str] = []
    details: list[dict[str, Any]] = []
    try:
        for port in serial.tools.list_ports.comports():
            ports.append(str(port.device or ""))
            details.append(
                {
                    "device": str(port.device or ""),
                    "description": str(port.description or ""),
                    "hwid": str(port.hwid or ""),
                    "vid": int(port.vid) if port.vid is not None else None,
                    "pid": int(port.pid) if port.pid is not None else None,
                    "serialNumber": str(port.serial_number or ""),
                    "location": str(port.location or ""),
                    "manufacturer": str(port.manufacturer or ""),
                    "product": str(port.product or ""),
                    "interface": str(port.interface or ""),
                }
            )
    except PermissionError as exc:
        raise AppException(
            ErrorCode.BOARD_DETECT_PERMISSION_DENIED,
            "串口扫描权限不足，请检查系统权限设置",
            status_code=403,
        ) from exc
    except OSError as exc:
        raise AppException(ErrorCode.BOARD_DETECT_SCAN_FAILED, f"串口扫描失败: {exc}", status_code=500) from exc
    return ports, details


def collect_probe_info(scan_usb_flag: bool, scan_ports_flag: bool) -> DeviceProbeResult:
    """按输入参数采集探针信息。"""
    usb_vid, usb_pid = "", ""
    serial_ports: list[str] = []
    serial_port_details: list[dict[str, Any]] = []
    usb_devices: list[dict[str, str]] = []

    if scan_usb_flag:
        usb_vid, usb_pid, usb_devices = scan_usb()
    if scan_ports_flag:
        serial_ports, serial_port_details = scan_serial_ports()
        if (not usb_vid or not usb_pid) and serial_port_details:
            first = serial_port_details[0]
            if first.get("vid") is not None:
                usb_vid = f"{int(first['vid']):04x}"
            if first.get("pid") is not None:
                usb_pid = f"{int(first['pid']):04x}"

    return DeviceProbeResult(
        usb_vid=usb_vid,
        usb_pid=usb_pid,
        serial_ports=serial_ports,
        serial_port_details=serial_port_details,
        usb_devices=usb_devices,
    )
