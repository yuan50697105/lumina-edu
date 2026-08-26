# ============================================
# Lumina 墨光 · 数据模型
# ============================================
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Column, String, Text, Integer, Boolean,
    ForeignKey, BigInteger,
    DateTime, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(String(20), unique=True, nullable=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="student")
    department = Column(String(100), nullable=True)
    grade = Column(String(10), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)


class Session(Base):
    """登录会话表"""
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token = Column(String(500), unique=True, nullable=False)
    device = Column(String(20), default="web")
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)


class APILog(Base):
    """API 访问日志（监控埋点）"""
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


class EventTracking(Base):
    """用户行为事件（监控埋点）"""
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