# ============================================
# Lumina 墨光 · 埋点收集服务数据模型
# event_tracking / api_logs（对齐 init.sql 共享表）
# ============================================
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Column, DateTime, Integer, JSON, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class EventTracking(Base):
    """用户行为事件（跨服务共享表 event_tracking）"""
    __tablename__ = "event_tracking"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_name = Column(String(100), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    session_id = Column(String(100), nullable=True)
    course_id = Column(UUID(as_uuid=True), nullable=True)
    properties = Column(JSON, nullable=True)
    page_url = Column(String(500), nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)


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
    created_at = Column(DateTime(timezone=True), default=_now)