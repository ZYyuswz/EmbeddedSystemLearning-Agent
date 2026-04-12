"""板卡候选融合匹配模块。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.models.schemas import MatchSignals


@dataclass(frozen=True)
class BoardFeature:
    """板卡特征库项。"""

    vendor: str
    model: str
    aliases: tuple[str, ...]
    vid_pid: tuple[tuple[str, str], ...]
    serial_keywords: tuple[str, ...]
    usb_keywords: tuple[str, ...]


@dataclass
class CandidateScore:
    """板卡候选评分结果。"""

    vendor: str
    model: str
    score: float
    signals: MatchSignals
    explain: str


BOARD_FEATURES: tuple[BoardFeature, ...] = (
    BoardFeature(
        vendor="ST",
        model="STM32F103C8T6-BluePill",
        aliases=("stm32", "bluepill", "f103", "stm32f103c8t6"),
        vid_pid=(("0483", "3748"),),
        serial_keywords=("stm32", "stlink", "usbmodem", "bluepill"),
        usb_keywords=("stm32", "stmicro", "st-link", "bluepill"),
    ),
    BoardFeature(
        vendor="Espressif",
        model="ESP32-DevKitC",
        aliases=("esp32", "devkitc", "esp32-devkitc"),
        vid_pid=(("10c4", "ea60"), ("1a86", "7523"), ("0403", "6001")),
        serial_keywords=("esp32", "usbserial", "cp210", "ch340", "devkit"),
        usb_keywords=("esp32", "cp210", "ch340", "espressif", "devkit"),
    ),
)


def score_candidates(
    user_input: str | None,
    manual_candidate: str | None,
    serial_ports: list[dict[str, Any]],
    usb_devices: list[dict[str, str]],
) -> list[CandidateScore]:
    """基于多信号为板卡候选打分。"""
    lowered_input = (user_input or "").strip().lower()
    lowered_manual = (manual_candidate or "").strip().lower()
    serial_text = _join_serial_text(serial_ports)
    usb_text = _join_usb_text(usb_devices)
    seen_vid_pids = _collect_vid_pid(serial_ports, usb_devices)

    candidates: list[CandidateScore] = []
    for feature in BOARD_FEATURES:
        signals = MatchSignals()

        if lowered_input and any(alias in lowered_input for alias in feature.aliases):
            signals.userInput = 0.45

        if seen_vid_pids and any(pair in seen_vid_pids for pair in feature.vid_pid):
            signals.vidPid = 0.35

        if serial_text and any(word in serial_text for word in feature.serial_keywords):
            signals.serialKeyword = 0.15

        if usb_text and any(word in usb_text for word in feature.usb_keywords):
            signals.usbKeyword = 0.12

        if lowered_manual and (lowered_manual == feature.model.lower() or lowered_manual in feature.aliases):
            signals.manualCandidate = 0.5

        score = min(1.0, signals.userInput + signals.vidPid + signals.serialKeyword + signals.usbKeyword + signals.manualCandidate)
        if score <= 0:
            continue

        candidates.append(
            CandidateScore(
                vendor=feature.vendor,
                model=feature.model,
                score=score,
                signals=signals,
                explain=_build_explain(feature.model, signals),
            )
        )

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates


def _join_serial_text(serial_ports: list[dict[str, Any]]) -> str:
    """拼接串口文本特征。"""
    pieces: list[str] = []
    for item in serial_ports:
        pieces.extend(
            [
                str(item.get("device", "")),
                str(item.get("description", "")),
                str(item.get("manufacturer", "")),
                str(item.get("product", "")),
                str(item.get("interface", "")),
            ]
        )
    return " ".join(pieces).lower()


def _join_usb_text(usb_devices: list[dict[str, str]]) -> str:
    """拼接 USB 文本特征。"""
    pieces: list[str] = []
    for item in usb_devices:
        pieces.extend([item.get("manufacturer", ""), item.get("product", ""), item.get("location", "")])
    return " ".join(pieces).lower()


def _collect_vid_pid(serial_ports: list[dict[str, Any]], usb_devices: list[dict[str, str]]) -> set[tuple[str, str]]:
    """提取探测到的 VID/PID 集合。"""
    pairs: set[tuple[str, str]] = set()
    for item in serial_ports:
        vid = item.get("vid")
        pid = item.get("pid")
        if vid is not None and pid is not None:
            pairs.add((f"{int(vid):04x}", f"{int(pid):04x}"))
    for item in usb_devices:
        vid = (item.get("vid") or "").lower()
        pid = (item.get("pid") or "").lower()
        if vid and pid:
            pairs.add((vid, pid))
    return pairs


def _build_explain(model: str, signals: MatchSignals) -> str:
    """构建候选解释文本。"""
    parts: list[str] = []
    if signals.userInput > 0:
        parts.append("用户输入别名命中")
    if signals.vidPid > 0:
        parts.append("VID/PID 命中")
    if signals.serialKeyword > 0:
        parts.append("串口描述关键字命中")
    if signals.usbKeyword > 0:
        parts.append("USB 关键字命中")
    if signals.manualCandidate > 0:
        parts.append("人工候选命中")
    if not parts:
        return f"{model} 未命中有效识别信号"
    return f"{model} 识别依据: {'、'.join(parts)}"
