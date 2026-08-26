# ============================================
# Lumina 墨光 · 课程服务入口
# ============================================
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import settings
from .database import Base, SessionLocal, engine
from .instrumentation import Instrumentation, Timer
from .routers import courses

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(process)d] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("lumina.course-service")

SERVICE_NAME = "course-service"
SERVICE_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时建表（开发环境）——announcements 等缺失表自动补齐"""
    import os
    if os.getenv("APP_ENV", "development") == "development":
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表已创建/补齐（development 模式）")
    yield


app = FastAPI(
    title="Lumina 墨光 · 课程服务 API",
    description="课程、章节、选课与公告服务",
    version=SERVICE_VERSION,
    lifespan=lifespan,
)

# CORS（网关层已配置，此处兜底）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_logging_middleware(request: Request, call_next):
    """全量请求日志中间件：写入 api_logs"""
    with Timer() as timer:
        response = await call_next(request)

    try:
        db = SessionLocal()
        Instrumentation(db, request).log_api(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=timer.duration_ms,
        )
        db.close()
    except Exception as exc:
        logger.warning(f"API 日志写入失败: {exc}")
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
app.include_router(courses.router, prefix="/api/v1")


# ─── 统一异常处理 ───
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("未处理异常: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "type": "https://api.lumina.edu/errors/internal",
            "title": "Internal Server Error",
            "code": "INTERNAL_ERROR",
            "detail": "服务器内部错误",
        },
    )