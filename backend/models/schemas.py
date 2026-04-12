"""API 请求与响应模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class BoardCandidate(BaseModel):
    """板卡候选模型。"""

    vendor: str
    model: str
    confidence: float = Field(ge=0, le=1)


class SerialPortInfo(BaseModel):
    """串口探测明细。"""

    device: str
    description: str = ""
    hwid: str = ""
    vid: int | None = None
    pid: int | None = None
    serialNumber: str = ""
    location: str = ""
    manufacturer: str = ""
    product: str = ""
    interface: str = ""


class UsbDeviceInfo(BaseModel):
    """USB 设备探测明细。"""

    vid: str = ""
    pid: str = ""
    manufacturer: str = ""
    product: str = ""
    serialNumber: str = ""
    location: str = ""


class ProbeInfo(BaseModel):
    """探针信息。"""

    usbVid: str = ""
    usbPid: str = ""
    serialPorts: list[str] = Field(default_factory=list)
    serialPortDetails: list[SerialPortInfo] = Field(default_factory=list)
    usbDevices: list[UsbDeviceInfo] = Field(default_factory=list)


class MatchSignals(BaseModel):
    """候选匹配信号拆分。"""

    userInput: float = 0.0
    vidPid: float = 0.0
    serialKeyword: float = 0.0
    usbKeyword: float = 0.0
    manualCandidate: float = 0.0


class DetectBoardRequest(BaseModel):
    """识别板卡请求。"""

    userProvidedModel: str | None = None
    scanPorts: bool = True
    scanUsb: bool = True


class DetectBoardResponse(BaseModel):
    """识别板卡响应。"""

    requestId: str
    resolvedBoard: BoardCandidate | None = None
    candidates: list[BoardCandidate] = Field(default_factory=list)
    needConfirm: bool = False
    matchSignals: MatchSignals = Field(default_factory=MatchSignals)
    probeInfo: ProbeInfo


class IdentifyBoardRequest(BaseModel):
    """二次识别请求。"""

    requestId: str
    userProvidedModel: str | None = None
    manualCandidateModel: str | None = None


class IdentifyBoardResponse(BaseModel):
    """二次识别响应。"""

    requestId: str
    resolvedBoard: BoardCandidate | None = None
    candidates: list[BoardCandidate] = Field(default_factory=list)
    needConfirm: bool = False
    matchSignals: MatchSignals = Field(default_factory=MatchSignals)
    explain: str = ""


class SourcePolicy(BaseModel):
    """资料抓取策略。"""

    allowApi: bool = True
    allowWeb: bool = True
    allowPdfIndex: bool = True


class KnowledgeSyncRequest(BaseModel):
    """资料同步请求。"""

    boardModel: str
    vendorHint: str | None = None
    forceRefresh: bool = False
    sourcePolicy: SourcePolicy = Field(default_factory=SourcePolicy)


class SourceRefResponse(BaseModel):
    """资料来源信息。"""

    url: str
    sourceType: Literal["official_site", "official_docs", "official_repo"]
    fetchedAt: datetime


class SpecSummary(BaseModel):
    """板卡规格摘要。"""

    mcu: str
    flashKB: int | None = None
    ramKB: int | None = None
    supportedProgrammers: list[str] = Field(default_factory=list)


class KnowledgeCacheInfo(BaseModel):
    """资料缓存命中信息。"""

    cacheHit: bool
    expiresAt: datetime
    ttlSec: int


class KnowledgeSyncResponse(BaseModel):
    """资料同步响应。"""

    knowledgeId: str
    sources: list[SourceRefResponse] = Field(default_factory=list)
    specSummary: SpecSummary
    cache: KnowledgeCacheInfo


class GenerateProjectRequest(BaseModel):
    """工程生成请求。"""

    boardModel: str
    knowledgeId: str
    requirementText: str
    language: str = "c"
    frameworkPreference: str = "auto"
    framework: str = "auto"
    toolchain: str = "auto"
    templateOptions: dict[str, Any] = Field(default_factory=dict)


class GenerateProjectResponse(BaseModel):
    """工程生成响应。"""

    projectId: str
    workspacePath: str
    buildCommand: str
    flashCommand: str
    runCheckCommand: str
    templateId: str
    generatedFiles: list[str] = Field(default_factory=list)
    flashPlanId: str | None = None


class FlashPlanRequest(BaseModel):
    """烧录规划请求。"""

    preferredTool: str | None = None
    artifactPath: str | None = None
    port: str = ""
    baudrate: int = 115200
    programmer: str = ""
    eraseMode: str = "chip"


class FlashPlanResponse(BaseModel):
    """烧录规划响应。"""

    flashPlanId: str
    tool: str
    command: str
    explain: str
    parameterSources: dict[str, str] = Field(default_factory=dict)
    requiresConfirm: bool = True


class FlashProjectRequest(BaseModel):
    """烧录请求。"""

    port: str
    programmer: str
    eraseMode: str = "chip"
    dryRun: bool = False
    userConfirmedRisk: bool = False
    flashPlanId: str | None = None


class SerialConfig(BaseModel):
    """串口连接参数。"""

    port: str
    baudrate: int = 115200
    bytesize: Literal[5, 6, 7, 8] = 8
    parity: Literal["N", "E", "O", "M", "S"] = "N"
    stopbits: Literal[1, 2] = 1
    writeTimeoutSec: float = Field(default=1.0, ge=0.1, le=30.0)


class RunCheckRequest(BaseModel):
    """运行验证请求。"""

    checkProfile: str = "serial_keyword_assert"
    timeoutSec: int = Field(default=20, ge=1, le=300)
    serial_keyword_assert: bool = True
    serialConfig: SerialConfig | None = None
    probeCommand: str = ""
    expectKeywords: list[str] = Field(default_factory=list)
    assertMode: Literal["all", "any"] = "all"


class TaskStartResponse(BaseModel):
    """任务启动响应。"""

    taskId: str
    status: str
    startedAt: datetime


class TaskDetailResponse(BaseModel):
    """任务详情响应。"""

    taskId: str
    status: str
    logs: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    command: str = ""
    errorCode: str | None = None
    startedAt: datetime | None = None
    endedAt: datetime | None = None


class EvalRunRequest(BaseModel):
    """评估任务请求。"""

    projectId: str
    boardPlatform: Literal["huawei", "phytium", "other"]
    scenarioName: str
    acceptanceChecklist: list[str] = Field(default_factory=list)


class EvalRunResponse(BaseModel):
    """评估任务响应。"""

    evaluationTaskId: str
    status: str


class EvalReportRequest(BaseModel):
    """评估报告请求。"""

    evaluationTaskId: str
    includeImprovementProposal: bool = True


class EvalReportResponse(BaseModel):
    """评估报告响应。"""

    reportId: str
    feasibility: Literal["high", "medium", "low"]
    agentScore: int
    improvements: list[str] = Field(default_factory=list)
