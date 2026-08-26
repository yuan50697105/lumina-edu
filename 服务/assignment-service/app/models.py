# ============================================
# Lumina 墨光 · 作业服务数据模型
# assignments / submissions / grades（共享表）
# ============================================
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey, Integer,
    JSON, Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Assignment(Base):
    """作业"""
    __tablename__ = "assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    max_score = Column(Integer, default=100)
    ai_grading = Column(Boolean, default=False)
    rubric = Column(JSON, nullable=True)
    ai_model = Column(String(50), nullable=True)
    status = Column(String(20), default="draft")   # draft | published | closed
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    submissions = relationship("Submission", back_populates="assignment")


class Submission(Base):
    """作业提交"""
    __tablename__ = "submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), nullable=False)
    file_urls = Column(JSON, nullable=True)
    text_answer = Column(Text, nullable=True)
    submission_note = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    late = Column(Boolean, default=False)

    assignment = relationship("Assignment", back_populates="submissions")


class Grade(Base):
    """作业成绩（批阅结果）"""
    __tablename__ = "grades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, unique=True)
    total_score = Column(Numeric(5, 2), nullable=True)
    grade_letter = Column(String(2), nullable=True)
    feedback = Column(Text, nullable=True)
    rubric_scores = Column(JSON, nullable=True)
    graded_by = Column(String(20), default="teacher")  # teacher | ai
    grader_id = Column(UUID(as_uuid=True), nullable=True)
    ai_model = Column(String(50), nullable=True)
    confidence = Column(Numeric(3, 2), nullable=True)
    graded_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class UserBrief(Base):
    """users 只读视图"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(50), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    role = Column(String(20), nullable=False)


class CourseBrief(Base):
    """courses 只读视图（校验/联查）"""
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True)
    title = Column(String(200), nullable=False)
    teacher_id = Column(UUID(as_uuid=True), nullable=False)
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