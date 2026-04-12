"""评估路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.auth import require_bearer_token
from backend.core.config import get_settings
from backend.models.schemas import (
    EvalReportRequest,
    EvalReportResponse,
    EvalRunRequest,
    EvalRunResponse,
)
from backend.repositories.sqlite_repo import SQLiteRepo
from backend.services.evaluation_service import generate_report, run_prototype

router = APIRouter(prefix="/evaluations", tags=["evaluations"], dependencies=[Depends(require_bearer_token)])


@router.post("/prototype/run", response_model=EvalRunResponse)
def run_prototype_eval(payload: EvalRunRequest) -> EvalRunResponse:
    """启动原型评估。"""
    repo = SQLiteRepo(get_settings().db_path)
    result = run_prototype(repo, payload.projectId, payload.boardPlatform, payload.scenarioName, payload.acceptanceChecklist)
    return EvalRunResponse(evaluationTaskId=result["evaluationTaskId"], status=result["status"])


@router.post("/reports/generate", response_model=EvalReportResponse)
def generate_eval_report(payload: EvalReportRequest) -> EvalReportResponse:
    """生成评估报告。"""
    repo = SQLiteRepo(get_settings().db_path)
    result = generate_report(repo, payload.evaluationTaskId, payload.includeImprovementProposal)
    return EvalReportResponse(**result)
