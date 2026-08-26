# ============================================
# Lumina 墨光 · 基础日志服务入口
# 日志检索统计（api_logs 只读）
# ============================================
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.modules.logs.logging_json import install_json_logging
from app.database import Base, SessionLocal, engine
from . import models  # noqa: F401  注册表结构到 Base.metadata
from .routers import router as logs_router

install_json_logging()
logger = logging.getLogger("lumina.logs")

SERVICE_NAME = "logs-service"
SERVICE_VERSION = "0.1.0"


app = FastAPI(
    title="Lumina 墨光 · 基础日志系统 API",
    description="结构化 JSON 日志规范 + api_logs 检索统计",
    version=SERVICE_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def api_logging_middleware(request: Request, call_next):
    """全量请求日志中间件：写入 api_logs"""
    t0 = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - t0) * 1000)
    try:
        db = SessionLocal()
        db.add(models.APILog(
            method=request.method, path=request.url.path,
            status_code=response.status_code, duration_ms=duration_ms,
        ))
        db.commit()
        db.close()
    except Exception as exc:
        logger.warning("API 日志写入失败", extra={"request_id": request.headers.get("x-request-id", "")})
    return response


# ─── 健康检查 ───
@app.get("/health", summary="健康检查")
def health():
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.get("/health/ready", summary="就绪检查")
def ready():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "ok"
    except Exception:
        db_status = "down"
    return {"status": "ok" if db_status == "ok" else "degraded", "db": db_status}


# ─── 路由挂载 ───
app.include_router(logs_router, prefix="/api/v1")


# ─── 统一异常处理 ───
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("未处理异常: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "detail": "服务器内部错误"},
    )