"""评估服务。"""
from __future__ import annotations

from uuid import uuid4

from backend.core.errors import AppException, ErrorCode
from backend.repositories.sqlite_repo import SQLiteRepo, now_iso


def run_prototype(
    repo: SQLiteRepo,
    project_id: str,
    board_platform: str,
    scenario_name: str,
    checklist: list[str],
) -> dict[str, str]:
    """启动原型评估任务。"""
    if not scenario_name.strip():
        raise AppException(ErrorCode.EVAL_SCENARIO_INVALID, "场景名称不能为空", status_code=422)
    evaluation_task_id = f"eval_{uuid4().hex[:12]}"
    repo.create_evaluation_task(
        {
            "evaluation_task_id": evaluation_task_id,
            "project_id": project_id,
            "board_platform": board_platform,
            "scenario_name": scenario_name,
            "checklist": checklist,
            "status": "running",
            "created_at": now_iso(),
        }
    )
    return {
        "evaluationTaskId": evaluation_task_id,
        "status": "running",
        "projectId": project_id,
        "boardPlatform": board_platform,
    }


def generate_report(repo: SQLiteRepo, evaluation_task_id: str, include_improvement: bool) -> dict[str, object]:
    """生成并持久化评估报告。"""
    eval_task = repo.get_evaluation_task(evaluation_task_id)
    if not eval_task:
        raise AppException(ErrorCode.NOT_FOUND, "评估任务不存在", status_code=404)

    report_id = f"report_{uuid4().hex[:12]}"
    improvements = ["增加板卡候选消歧步骤", "优化烧录失败自动诊断策略"] if include_improvement else []
    metrics = {
        "taskSuccessRate": 0.86,
        "avgLeadTimeSec": 95,
        "manualInterventionCount": 1,
        "specAccuracyScore": 0.88,
    }
    feasibility = _calc_feasibility(metrics["taskSuccessRate"], metrics["avgLeadTimeSec"])
    report = {
        "report_id": report_id,
        "evaluation_task_id": evaluation_task_id,
        "project_id": eval_task["projectId"],
        "board_platform": eval_task["boardPlatform"],
        "feasibility_level": feasibility,
        "metrics": metrics,
        "findings": ["流程可完成生成和验证", "部分板卡仍需人工确认"],
        "improvement_proposals": improvements,
        "created_at": now_iso(),
    }
    repo.save_evaluation_report(report)
    return {
        "reportId": report_id,
        "feasibility": feasibility,
        "agentScore": _compute_agent_score(metrics),
        "improvements": improvements,
    }


def _calc_feasibility(success_rate: float, avg_lead_time: int) -> str:
    """根据指标计算可行性等级。"""
    if success_rate >= 0.8 and avg_lead_time <= 120:
        return "high"
    if success_rate >= 0.6:
        return "medium"
    return "low"


def _compute_agent_score(metrics: dict[str, float | int]) -> int:
    """计算代理评分。"""
    base = int(metrics["taskSuccessRate"] * 100)
    penalty = int(metrics["manualInterventionCount"]) * 6
    lead_time_penalty = 8 if int(metrics["avgLeadTimeSec"]) > 120 else 0
    return max(0, min(100, base - penalty - lead_time_penalty))
