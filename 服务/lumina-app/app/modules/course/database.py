# ============================================
# Lumina 墨光 · 课程服务数据库连接
# 与 user-service 共享同一 MySQL 库（轻量一期单库方案）
# ============================================
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # 连接健康检查
    pool_size=10,            # 连接池大小
    max_overflow=20,         # 最大溢出连接
    echo=settings.APP_DEBUG, # SQL 日志（仅开发）
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依赖：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()