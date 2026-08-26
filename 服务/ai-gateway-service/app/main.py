# ============================================
# Lumina 墨光 · AI 网关服务入口
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
from .models import AIModel, AIProvider
from .routers import ai_gateway

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(process)d] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("lumina.ai-gateway")

SERVICE_NAME = "ai-gateway-service"
SERVICE_VERSION = "0.3.0"


def migrate_schema() -> None:
    """轻量迁移：为旧库补 endpoint_base / api_style 列（幂等）"""
    from sqlalchemy import text
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE ai_providers ADD COLUMN IF NOT EXISTS endpoint_base VARCHAR(300)"))
        db.execute(text("ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS api_style VARCHAR(20) DEFAULT 'openai'"))
        db.execute(text("""
            UPDATE ai_models SET api_style = 'openai' WHERE api_style IS NULL OR api_style = ''
        """))
        db.commit()
        logger.info("AI 网关表结构已同步（endpoint_base / api_style）")
    except Exception as exc:
        db.rollback()
        logger.warning(f"表结构同步跳过: {exc}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时建表 + 迁移（不预置模型，由运营端通过管理 API 自定义配置）"""
    import os
    if os.getenv("APP_ENV", "development") == "development":
        Base.metadata.create_all(bind=engine)
    migrate_schema()
    yield


app = FastAPI(
    title="Lumina 墨光 · AI 网关服务 API",
    description="模型池管理、智能路由与用量统计",
    version=SERVICE_VERSION,
    lifespan=lifespan,
)

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
app.include_router(ai_gateway.router, prefix="/api/v1")


# ─── 统一异常处理 ───
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("未处理异常: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "detail": "服务器内部错误"},
    )