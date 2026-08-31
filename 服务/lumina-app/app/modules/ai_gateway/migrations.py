# ============================================
# Lumina 墨光 · AI 网关表结构迁移
# 为旧库补 endpoint_base / api_style 列（幂等，兼容 MySQL）
# ============================================
import logging

from sqlalchemy import inspect, text

from app.database import SessionLocal

logger = logging.getLogger("lumina.ai-gateway")


def migrate_schema() -> None:
    """轻量迁移：为旧库补 endpoint_base / api_style 列（幂等，兼容 MySQL）"""
    db = SessionLocal()
    try:
        inspector = inspect(db.bind)
        provider_cols = {c["name"] for c in inspector.get_columns("ai_providers")}
        if "endpoint_base" not in provider_cols:
            db.execute(text("ALTER TABLE ai_providers ADD COLUMN endpoint_base VARCHAR(300)"))
        model_cols = {c["name"] for c in inspector.get_columns("ai_models")}
        if "api_style" not in model_cols:
            db.execute(text("ALTER TABLE ai_models ADD COLUMN api_style VARCHAR(20) DEFAULT 'openai'"))
        db.execute(text("""
            UPDATE ai_models SET api_style = 'openai' WHERE api_style IS NULL OR api_style = ''
        """))
        db.commit()
        logger.info("AI 网关表结构已同步（endpoint_base / api_style）")
    except Exception as exc:
        db.rollback()
        logger.warning("表结构同步跳过: %s", exc)
    finally:
        db.close()