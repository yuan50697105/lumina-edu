# ============================================
# Lumina 墨光 · 单体应用入口（合并 9 微服务）
# ============================================
import asyncio
import logging
import time
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401
from app.logging_json import install_json_logging

# 模块路由
from app.modules.user import routers as user_routers
from app.modules.course import routers as course_routers
from app.modules.assignment import routers as assignment_routers
from app.modules.grade import routers as grade_routers
from app.modules.ai_gateway import routers as ai_gateway_routers
from app.modules.ai_chat import routers as ai_chat_routers
from app.modules.ai_grade import routers as ai_grade_routers
from app.modules.live import routers as live_routers
from app.modules.collab import routers as collab_routers
from app.media_proxy import router as media_router
from app.modules.analytics import routers as analytics_routers
from app.modules.logs import routers as logs_routers
from app.modules.notif import routers as notif_routers
from app.modules.exam import routers as exam_routers
from app.modules.tutoring import routers as tutoring_routers
from app.modules.admin import routers as admin_routers
from app.modules.settings import routers as settings_routers
from app.modules.learning import routers as learning_routers
from app.modules.video import routers as video_routers
from app.modules.ai_infra import routers as ai_infra_routers

install_json_logging()
logger = logging.getLogger("lumina.app")

SERVICE_NAME = "lumina-app"
SERVICE_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("APP_ENV", "development") == "development":
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表已创建（development 模式）")
    # 旧库迁移：AI 网关表结构补齐（endpoint_base / api_style），幂等可重复
    try:
        from app.modules.ai_gateway.migrations import migrate_schema
        migrate_schema()
    except Exception as exc:
        logger.warning("AI 网关表结构迁移跳过: %s", exc)
    yield


app = FastAPI(
    title="Lumina 墨光 · 跨端教学协作平台 API",
    description="用户·课程·作业·成绩·AI 对话·批阅·埋点·日志 全链路 API",
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
    t0 = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - t0) * 1000)
# 后台线程写日志，避免同步 DB 写入阻塞事件循环（高并发下曾将吞吐拖至 ~5 req/s）
    method, path, status_code = request.method, request.url.path, response.status_code

    def _persist_log():
        try:
            db = SessionLocal()
            db.add(models.APILog(
                method=method, path=path,
                status_code=status_code, duration_ms=duration_ms,
            ))
            db.commit()
            db.close()
        except Exception as exc:
            logger.warning("API 日志写入失败: %s", exc)

    asyncio.get_running_loop().create_task(asyncio.to_thread(_persist_log))
    return response


@app.get("/health", summary="健康检查")
def health():
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.get("/health/ready", summary="就绪检查")
def ready():
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception:
            db_status = "down"
        finally:
            db.close()
    except Exception:
        db_status = "down"
    return {"status": "ok" if db_status == "ok" else "degraded", "db": db_status}


# ─── 路由挂载（prefix 与原各服务一致）───
# 用户/认证
app.include_router(user_routers.auth_router, prefix="/api/v1")
app.include_router(user_routers.users_router, prefix="/api/v1")
# 课程
app.include_router(course_routers.router, prefix="/api/v1")
# 作业
app.include_router(assignment_routers.router, prefix="/api/v1")
app.include_router(assignment_routers.course_router, prefix="/api/v1")
# 成绩
app.include_router(grade_routers.router, prefix="/api/v1")
app.include_router(grade_routers.course_router, prefix="/api/v1")
# AI 网关
app.include_router(ai_gateway_routers.router, prefix="/api/v1")
# AI 对话
app.include_router(ai_chat_routers.router, prefix="/api/v1")
# AI 批阅
app.include_router(ai_grade_routers.router, prefix="/api/v1")
# 直播（V1.1 · D-01）
app.include_router(live_routers.router, prefix="/api/v1")
app.include_router(live_routers.course_router, prefix="/api/v1")
app.include_router(collab_routers.router, prefix="/api/v1")
# HLS 媒体反代（开发演示同源代理，见 app/media_proxy.py）
app.include_router(media_router)
# 埋点
app.include_router(analytics_routers.router, prefix="/api/v1")
# 日志
app.include_router(logs_routers.router, prefix="/api/v1")
# 消息通知（D-03）
app.include_router(notif_routers.router, prefix="/api/v1")
# 题库与考试（D-04）
app.include_router(exam_routers.router, prefix="/api/v1")
# 辅导记录（D-05）
app.include_router(tutoring_routers.router, prefix="/api/v1")
# 学情分析子路由（D-05）
if hasattr(analytics_routers, "analytics_router"):
    app.include_router(analytics_routers.analytics_router, prefix="/api/v1")
# 管理端（D-07/D-08）
app.include_router(admin_routers.router, prefix="/api/v1")
app.include_router(settings_routers.router, prefix="/api/v1")
# 审计日志子路由（D-07/D-08）
if hasattr(logs_routers, "audit_router"):
    app.include_router(logs_routers.audit_router, prefix="/api/v1")
# 自主学习（D-06）
app.include_router(learning_routers.router, prefix="/api/v1")
# 视频录播（D-08）
app.include_router(video_routers.router, prefix="/api/v1")
# AI 基础设施（D-09）
app.include_router(ai_infra_routers.router, prefix="/api/v1")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("未处理异常: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "detail": "服务器内部错误"},
    )
