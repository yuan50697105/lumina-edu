# ============================================
# Lumina 墨光 · 课程服务数据模型
# 注：与 user-service 共享同一数据库，users 表为只读引用
# ============================================
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, BigInteger, Column, DateTime, ForeignKey, Integer,
    JSON, Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Course(Base):
    """课程主表"""
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    teacher_id = Column(UUID(as_uuid=True), nullable=False)
    department = Column(String(100), nullable=True)
    credits = Column(Numeric(3, 1), nullable=True)
    semester = Column(String(20), nullable=False)
    schedule = Column(JSON, nullable=True)
    students_count = Column(Integer, default=0)
    status = Column(String(20), default="draft")   # draft | published | archived
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    enrollments = relationship("Enrollment", back_populates="course")
    chapters = relationship("Chapter", back_populates="course")


class Enrollment(Base):
    """选课记录"""
    __tablename__ = "enrollments"
    __table_args__ = ({"comment": "选课记录，UNIQUE(user_id, course_id) 在外部索引保证"})

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), default="student")  # student | teacher | ta
    enrolled_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    status = Column(String(20), default="active")  # active | dropped | completed

    course = relationship("Course", back_populates="enrollments")


class Chapter(Base):
    """章节"""
    __tablename__ = "chapters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    order_num = Column(Integer, default=0)
    resources = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    course = relationship("Course", back_populates="chapters")


class Announcement(Base):
    """课程公告"""
    __tablename__ = "announcements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(UUID(as_uuid=True), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    pinned = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_now)


class UserBrief(Base):
    """users 只读视图（跨服务共享库获取教师/学生姓名）"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(50), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    role = Column(String(20), nullable=False)


# ─── 监控共享表（与 user-service 一致）───
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