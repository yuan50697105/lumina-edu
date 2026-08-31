# ============================================
# Lumina 墨光 · 统一数据模型（合并 9 微服务）
# ============================================
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float, Integer, String, Text, Numeric,
    JSON, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import CHAR, TypeDecorator

from app.database import Base


class GUID(TypeDecorator):
    """跨数据库 UUID：MySQL 存 CHAR(36)（标准连字符格式），随时可迁移回 PostgreSQL
    原生 text SQL 以 str(uuid) 绑参（36 位连字符）可直接匹配。"""
    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return str(value) if value is not None else None

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return uuid.UUID(value)
        except (ValueError, TypeError):
            return value


def _now():
    """当前 UTC 时间（timezone-aware）"""
    return datetime.now(timezone.utc)


class APILog(Base):
    """API 访问日志（监控埋点）"""
    __tablename__ = "api_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    status_code = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    user_id = Column(GUID, nullable=True)
    request_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

class EventTracking(Base):
    """用户行为事件（监控埋点）"""
    __tablename__ = "event_tracking"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_name = Column(String(100), nullable=False)
    user_id = Column(GUID, nullable=True)
    session_id = Column(String(100), nullable=True)
    course_id = Column(GUID, nullable=True)
    properties = Column(JSON, nullable=True)
    page_url = Column(String(500), nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

class UserBrief(Base):
    """users 只读视图"""
    __tablename__ = "users"

    id = Column(GUID, primary_key=True)
    name = Column(String(50), nullable=False)
    student_id = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    role = Column(String(20), nullable=False)

class CourseBrief(Base):
    """courses 只读视图"""
    __tablename__ = "courses"

    id = Column(GUID, primary_key=True)
    title = Column(String(200), nullable=False)
    teacher_id = Column(GUID, nullable=False)
    credits = Column(Numeric(3, 1), nullable=True)
    semester = Column(String(20), nullable=False)
    status = Column(String(20), default="draft")


# ─── 监控共享表 ───

class User(Base):
    """用户表"""
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
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

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token = Column(String(500), unique=True, nullable=False)
    device = Column(String(20), default="web")
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

class Course(Base):
    """课程主表"""
    __tablename__ = "courses"
    __table_args__ = {"extend_existing": True}

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    code = Column(String(20), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    teacher_id = Column(GUID, nullable=False)
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

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, nullable=False)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), default="student")  # student | teacher | ta
    enrolled_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    status = Column(String(20), default="active")  # active | dropped | completed

    course = relationship("Course", back_populates="enrollments")

class Chapter(Base):
    """章节"""
    __tablename__ = "chapters"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    order_num = Column(Integer, default=0)
    resources = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    course = relationship("Course", back_populates="chapters")

class Announcement(Base):
    """课程公告"""
    __tablename__ = "announcements"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(GUID, nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    pinned = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_now)

class Assignment(Base):
    """作业"""
    __tablename__ = "assignments"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
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

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    assignment_id = Column(GUID, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(GUID, nullable=False)
    file_urls = Column(JSON, nullable=True)
    text_answer = Column(Text, nullable=True)
    submission_note = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    late = Column(Boolean, default=False)

    assignment = relationship("Assignment", back_populates="submissions")

class Grade(Base):
    """作业成绩（批阅结果）"""
    __tablename__ = "grades"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    submission_id = Column(GUID, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, unique=True)
    total_score = Column(Numeric(5, 2), nullable=True)
    grade_letter = Column(String(2), nullable=True)
    feedback = Column(Text, nullable=True)
    rubric_scores = Column(JSON, nullable=True)
    graded_by = Column(String(20), default="teacher")  # teacher | ai
    grader_id = Column(GUID, nullable=True)
    ai_model = Column(String(50), nullable=True)
    confidence = Column(Numeric(3, 2), nullable=True)
    graded_at = Column(DateTime(timezone=True), default=_now, nullable=False)

class GradeRecord(Base):
    """学期成绩汇总（成绩单）"""
    __tablename__ = "grade_records"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "semester", name="uq_grade_record"),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    student_id = Column(GUID, nullable=False)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    semester = Column(String(20), nullable=False)
    final_score = Column(Numeric(5, 2), nullable=True)
    gpa_point = Column(Numeric(3, 2), nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=_now, nullable=False)

class AIProvider(Base):
    """模型供应商（API Key 不入库，存 env）"""
    __tablename__ = "ai_providers"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(30), unique=True, nullable=False)     # qwen / glm / spark / doubao / anthropic / gemini
    display_name = Column(String(50), nullable=False)
    description = Column(String(200), nullable=True)
    domain = Column(String(200), nullable=True)                # 供应商域名标识
    endpoint_base = Column(String(300), nullable=True)         # API Base URL（OpenAI 兼容风格 / Anthropic / Gemini）
    enabled = Column(Boolean, default=True)                    # 是否启用整家供应商
    monthly_quota = Column(Numeric(12, 2), default=0)          # 月度预算（元），0=不限
    used_quota = Column(Numeric(12, 2), default=0)             # 已用额度（元）
    created_at = Column(DateTime(timezone=True), default=_now)

    models = relationship("AIModel", back_populates="provider")

class AIModel(Base):
    """模型单"""
    __tablename__ = "ai_models"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    provider_id = Column(GUID, ForeignKey("ai_providers.id"), nullable=False)
    model_name = Column(String(50), unique=True, nullable=False)   # qwen-max / claude-3-5-sonnet / gemini-2.0-flash
    display_name = Column(String(50), nullable=False)              # 通义千问 Max
    task_types = Column(JSON, default=list)                        # ["chat","grade","generate","vl","speech"]
    description = Column(String(200), nullable=True)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=10)                         # 路由优先级（数值小优先）
    cost_per_1k_tokens = Column(Numeric(8, 4), default=0)          # 单价（元/千token）
    max_tokens = Column(Integer, default=4096)
    api_style = Column(String(20), default="openai")               # openai / anthropic / gemini
    openai_compatible = Column(Boolean, default=True)              # 兼容保留：历史字段，等同(api_style=='openai')
    created_at = Column(DateTime(timezone=True), default=_now)

    provider = relationship("AIProvider", back_populates="models")

class AICallLog(Base):
    """AI 调用用量日志"""
    __tablename__ = "ai_call_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(GUID, nullable=True)
    model_id = Column(GUID, ForeignKey("ai_models.id"), nullable=False)
    model_name = Column(String(50), nullable=False)
    task_type = Column(String(20), nullable=False)           # chat/grade/generate/vl/speech
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    cost = Column(Numeric(10, 4), default=0)
    ok = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)


# ─── 监控共享表 ───

class AIConversation(Base):
    """AI 对话会话（对齐 init.sql / lumina-database 文档）"""
    __tablename__ = "ai_conversations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, nullable=False, index=True)   # 分片键
    title = Column(String(200), nullable=True)                          # 自动生成（首条消息截断）
    model = Column(String(50), nullable=True)                           # 实际使用模型 qwen-max
    context_course_id = Column(GUID, nullable=True)       # 关联课程
    context_chapter_id = Column(GUID, nullable=True)      # 关联章节
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    messages = relationship("AIMessage", back_populates="conversation")

class AIMessage(Base):
    """AI 对话消息"""
    __tablename__ = "ai_messages"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(GUID,
                             ForeignKey("ai_conversations.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    role = Column(String(20), nullable=False)          # user / assistant / system
    content = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True)          # 图片/音频附件
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_now)

    conversation = relationship("AIConversation", back_populates="messages")


# ─── 监控共享表 ───
