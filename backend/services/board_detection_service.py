"""板卡识别服务。"""
from __future__ import annotations

from uuid import uuid4

from backend.core.errors import AppException, ErrorCode
from backend.infrastructure.device_scanner import collect_probe_info
from backend.models.schemas import (
    BoardCandidate,
    DetectBoardResponse,
    IdentifyBoardResponse,
    MatchSignals,
    ProbeInfo,
)
from backend.repositories.sqlite_repo import SQLiteRepo
from backend.services.board_matcher import score_candidates


def detect(
    repo: SQLiteRepo,
    user_model: str | None,
    scan_usb: bool,
    scan_ports: bool,
    detect_confidence_threshold: float,
) -> DetectBoardResponse:
    """执行板卡识别并返回候选。"""
    probe = collect_probe_info(scan_usb, scan_ports)
    if not probe.serial_ports and not probe.usb_devices and not user_model:
        raise AppException(ErrorCode.BOARD_DETECT_EMPTY, "未扫描到可识别设备", status_code=404)

    request_id = f"req_{uuid4().hex[:12]}"
    repo.save_probe_snapshot(
        {
            "request_id": request_id,
            "serial_ports": probe.serial_port_details,
            "usb_devices": probe.usb_devices,
        }
    )

    ranked = score_candidates(user_model, None, probe.serial_port_details, probe.usb_devices)
    if not ranked and user_model:
        ranked = [
            _candidate_fallback(user_model),
        ]

    if not ranked:
        raise AppException(ErrorCode.BOARD_DETECT_EMPTY, "未识别到板卡候选", status_code=404)

    need_confirm = _need_confirm(ranked, detect_confidence_threshold, margin=0.08)
    repo.save_match_trace(request_id, ranked, need_confirm=need_confirm, decision="detect")

    resolved = ranked[0]
    return DetectBoardResponse(
        requestId=request_id,
        resolvedBoard=BoardCandidate(vendor=resolved.vendor, model=resolved.model, confidence=resolved.score),
        candidates=[BoardCandidate(vendor=item.vendor, model=item.model, confidence=item.score) for item in ranked],
        needConfirm=need_confirm,
        matchSignals=resolved.signals,
        probeInfo=ProbeInfo(
            usbVid=probe.usb_vid,
            usbPid=probe.usb_pid,
            serialPorts=probe.serial_ports,
            serialPortDetails=probe.serial_port_details,
            usbDevices=probe.usb_devices,
        ),
    )


def identify(
    repo: SQLiteRepo,
    request_id: str,
    user_model: str | None,
    manual_candidate_model: str | None,
    detect_confidence_threshold: float,
) -> IdentifyBoardResponse:
    """基于快照与人工候选执行二次识别。"""
    snapshot = repo.get_probe_snapshot(request_id)
    if not snapshot:
        raise AppException(ErrorCode.NOT_FOUND, "未找到对应的识别快照", status_code=404)

    ranked = score_candidates(
        user_model,
        manual_candidate_model,
        snapshot.get("serialPorts", []),
        snapshot.get("usbDevices", []),
    )
    if not ranked and manual_candidate_model:
        ranked = [_candidate_fallback(manual_candidate_model)]

    if not ranked:
        raise AppException(ErrorCode.BOARD_DETECT_AMBIGUOUS, "当前探测信息不足以完成识别", status_code=422)

    need_confirm = _need_confirm(ranked, detect_confidence_threshold, margin=0.05)
    repo.save_match_trace(request_id, ranked, need_confirm=need_confirm, decision="identify")
    resolved = ranked[0]

    return IdentifyBoardResponse(
        requestId=request_id,
        resolvedBoard=BoardCandidate(vendor=resolved.vendor, model=resolved.model, confidence=resolved.score),
        candidates=[BoardCandidate(vendor=item.vendor, model=item.model, confidence=item.score) for item in ranked],
        needConfirm=need_confirm,
        matchSignals=resolved.signals,
        explain=resolved.explain,
    )


def _need_confirm(candidates: list, threshold: float, margin: float) -> bool:
    """根据分数阈值与差值门限判断是否需要确认。"""
    top1 = candidates[0]
    if top1.score < threshold:
        return True
    if len(candidates) < 2:
        return False
    return (top1.score - candidates[1].score) < margin


def _candidate_fallback(model: str):
    """在未命中特征库时构造兜底候选。"""
    return type(
        "FallbackCandidate",
        (),
        {
            "vendor": "Unknown",
            "model": model,
            "score": 0.55,
            "signals": MatchSignals(userInput=0.55),
            "explain": f"{model} 仅命中用户输入，缺少设备侧证据",
        },
    )()
