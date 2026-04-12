"""板卡相关路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.auth import require_bearer_token
from backend.core.config import get_settings
from backend.models.schemas import (
    DetectBoardRequest,
    DetectBoardResponse,
    IdentifyBoardRequest,
    IdentifyBoardResponse,
    KnowledgeSyncRequest,
    KnowledgeSyncResponse,
)
from backend.repositories.sqlite_repo import SQLiteRepo
from backend.services.board_detection_service import detect, identify
from backend.services.knowledge_sync_service import sync_official_sources

router = APIRouter(prefix="/boards", tags=["boards"], dependencies=[Depends(require_bearer_token)])


def _repo() -> SQLiteRepo:
    """创建仓储实例。"""
    return SQLiteRepo(get_settings().db_path)


@router.post("/detect", response_model=DetectBoardResponse)
def detect_board(payload: DetectBoardRequest) -> DetectBoardResponse:
    """识别板卡。"""
    settings = get_settings()
    return detect(
        _repo(),
        payload.userProvidedModel,
        payload.scanUsb,
        payload.scanPorts,
        settings.detect_confidence_threshold,
    )


@router.post("/identify", response_model=IdentifyBoardResponse)
def identify_board(payload: IdentifyBoardRequest) -> IdentifyBoardResponse:
    """执行板卡二次识别。"""
    settings = get_settings()
    return identify(
        _repo(),
        payload.requestId,
        payload.userProvidedModel,
        payload.manualCandidateModel,
        settings.detect_confidence_threshold,
    )


@router.post("/knowledge/sync", response_model=KnowledgeSyncResponse)
def sync_board_knowledge(payload: KnowledgeSyncRequest) -> KnowledgeSyncResponse:
    """同步板卡官方资料。"""
    return sync_official_sources(_repo(), payload.boardModel, payload.vendorHint, payload.forceRefresh, payload.sourcePolicy)
