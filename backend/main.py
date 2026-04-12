"""FastAPI 应用入口。"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.api.routes.boards import router as boards_router
from backend.api.routes.evaluations import router as evaluations_router
from backend.api.routes.projects import router as projects_router
from backend.api.routes.tasks import router as tasks_router
from backend.core.errors import AppException, ErrorCode

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Board Assistant API", version="0.1.0")
app.include_router(boards_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(evaluations_router, prefix="/api/v1")


@app.middleware("http")
async def request_log_middleware(request: Request, call_next):
    """记录请求日志。"""
    logger.info("收到请求: %s %s", request.method, request.url.path)
    response = await call_next(request)
    logger.info("请求完成: %s %s -> %s", request.method, request.url.path, response.status_code)
    return response


@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    """处理业务异常。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"errorCode": exc.code.value, "message": exc.message},
    )


@app.exception_handler(Exception)
async def unknown_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """处理未知异常。"""
    logger.exception("后端发生未捕获异常: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"errorCode": ErrorCode.INTERNAL_FAILED.value, "message": "系统内部错误"},
    )
