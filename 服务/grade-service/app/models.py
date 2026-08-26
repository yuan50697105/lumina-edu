# ============================================
# Lumina 墨光 · 成绩服务数据模型
# grade_records（学期成绩汇总）+ 只读引用表
# ============================================
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Column, DateTime, ForeignKey, Integer,
    JSON, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GradeRecord(Base):
    """学期成绩汇总（成绩单）"""
    __tablename__ = "grade_records"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "semester", name="uq_grade_record"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    semester = Column(String(20), nullable=False)
    final_score = Column(Numeric(5, 2), nullable=True)
    gpa_point = Column(Numeric(3, 2), nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class UserBrief(Base):
    """users 只读视图"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(50), nullable=False)
    student_id = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    role = Column(String(20), nullable=False)


class CourseBrief(Base):
    """courses 只读视图"""
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True)
    title = Column(String(200), nullable=False)
    teacher_id = Column(UUID(as_uuid=True), nullable=False)
    credits = Column(Numeric(3, 1), nullable=True)
    semester = Column(String(20), nullable=False)
    status = Column(String(20), default="draft")


# ─── 监控共享表 ───
class APILog(Base):
    """API 访问日志"""
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
    """用户行为事件"""
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