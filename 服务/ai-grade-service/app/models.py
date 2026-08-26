# ============================================
# Lumina 墨光 · AI 批阅服务数据模型
# grades（提交级批阅结果）+ 共享埋点表
# ============================================
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric,
    String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Grade(Base):
    """提交批阅结果（对齐 init.sql grades 表 / assignment-service 批阅）"""
    __tablename__ = "grades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True),
                           ForeignKey("submissions.id", ondelete="CASCADE"),
                           nullable=False, unique=True, index=True)   # 一个提交一条成绩
    total_score = Column(Numeric(5, 2), nullable=True)
    grade_letter = Column(String(2), nullable=True)
    feedback = Column(Text, nullable=True)
    rubric_scores = Column(JSON, nullable=True)                        # [{criteria,score,max,comment}]
    graded_by = Column(String(10), default="teacher")                  # teacher / ai
    grader_id = Column(UUID(as_uuid=True), nullable=True)              # 触发批阅的教师
    ai_model = Column(String(50), nullable=True)
    confidence = Column(Numeric(3, 2), nullable=True)
    graded_at = Column(DateTime(timezone=True), default=_now)

    # 为 SQLAlchemy 定义 submission 关系（只读，不建 submission ORM 完整模型）
    # 注：submission 表由 assignment-service 管理，此处仅声明外键


# ─── 监控共享表 ───
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