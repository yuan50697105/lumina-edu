# ============================================
# Lumina 墨光 · 基础日志服务数据模型
# api_logs（对齐 init.sql 共享表，只读）
# ============================================
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Column, DateTime, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID

from .database import Base


class APILog(Base):
    """API 访问日志（跨服务共享表 api_logs）"""
    __tablename__ = "api_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    status_code = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    request_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))