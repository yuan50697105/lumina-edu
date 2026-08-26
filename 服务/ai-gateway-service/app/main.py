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
SERVICE_VERSION = "0.1.0"


def seed_model_pool() -> None:
    """首次启动时预置国产生态模型池（幂等：表空才写入）"""
    db = SessionLocal()
    try:
        if db.query(AIProvider).count() > 0:
            return

        providers = {
            "qwen": ("通义千问", "阿里云 · 100%兼容 OpenAI"),
            "glm": ("智谱 GLM", "智谱 AI · 教育专用"),
            "spark": ("讯飞星火", "科大讯飞 · 语音/教育"),
            "doubao": ("豆包", "字节跳动 · 轻量快速"),
            "bce": ("百川", "百川智能 · 文本嵌入"),
            "moonshot": ("月之暗面", "Kimi · 长文本"),
        }
        p_objs = {}
        for name, (display, desc) in providers.items():
            p = AIProvider(name=name, display_name=display, description=desc)
            db.add(p)
            p_objs[name] = p
        db.flush()

        models = [
            # (provider, model_name, display, task_types, priority, cost_per_1k, max_tokens)
            ("qwen", "qwen-max", "通义千问 Max", ["chat", "generate"], 10, 0.0200, 8192),
            ("qwen", "qwen-vl", "通义千问-VL", ["vl"], 10, 0.0800, 4096),
            ("glm", "glm-4", "智谱 GLM-4", ["chat", "grade", "generate"], 20, 0.0500, 8192),
            ("spark", "spark-v4", "讯飞星火 V4", ["chat"], 30, 0.0300, 4096),
            ("spark", "spark-v3", "讯飞语音 V3", ["speech"], 10, 0.0000, 4096),
            ("doubao", "doubao-lite", "豆包 Lite", ["chat"], 40, 0.0050, 4096),
            ("bce", "bce-embedding", "百川 Embedding", ["generate"], 10, 0.0007, 2048),
            ("moonshot", "kimi", "Kimi", ["chat", "grade"], 50, 0.0600, 16384),
        ]
        for provider_name, model_name, display, task_types, priority, cost, max_tokens in models:
            db.add(AIModel(
                provider_id=p_objs[provider_name].id,
                model_name=model_name,
                display_name=display,
                task_types=task_types,
                priority=priority,
                cost_per_1k_tokens=str(cost),
                max_tokens=max_tokens,
            ))
        db.commit()
        logger.info(f"AI 模型池种子数据已写入（{len(models)} 个模型 / {len(providers)} 家供应商）")
    except Exception as exc:
        db.rollback()
        logger.warning(f"种子数据写入失败: {exc}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时建表 + 预置模型池"""
    import os
    if os.getenv("APP_ENV", "development") == "development":
        Base.metadata.create_all(bind=engine)
    seed_model_pool()
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