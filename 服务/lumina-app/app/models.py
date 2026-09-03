# ============================================
# Lumina 墨光 · 统一数据模型（合并 9 微服务）
# ============================================
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float, Integer, String, Text, Numeric,
    JSON, ForeignKey, UniqueConstraint, Index, func
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
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now)

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
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)

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
    enrolled_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
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
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)

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
    submitted_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
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
    graded_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)

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
    recorded_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)

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
    updated_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now)

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


# ─── 直播 Live（V1.1 · D-01 · WBS-P 阶段 D）───

class LiveRoom(Base):
    """直播房间"""
    __tablename__ = "live_rooms"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(GUID, nullable=False)
    title = Column(String(200), nullable=False)
    status = Column(String(20), default="scheduled")   # scheduled | live | ended
    stream_key = Column(String(100), nullable=True)    # 推流唯一标识（媒体服务器/浏览器推流用）
    viewer_count = Column(Integer, default=0)          # 累计加入人次
    active_call = Column(JSON, nullable=True)          # 当前点名 {user_id,name,called_at}
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)

class LiveAttendee(Base):
    """直播参与记录（含举手状态）"""
    __tablename__ = "live_attendees"
    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_live_attendee"),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    room_id = Column(GUID, ForeignKey("live_rooms.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, nullable=False)
    role = Column(String(20), default="student")       # teacher | student
    joined_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    left_at = Column(DateTime(timezone=True), nullable=True)
    raise_hand = Column(Boolean, default=False)
    raised_at = Column(DateTime(timezone=True), nullable=True)

class LiveMessage(Base):
    """直播消息（聊天/点名/系统广播）"""
    __tablename__ = "live_messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    room_id = Column(GUID, ForeignKey("live_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID, nullable=True)
    msg_type = Column(String(20), default="chat")      # chat | system | call
    content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)

class LiveQuiz(Base):
    """直播答题"""
    __tablename__ = "live_quizzes"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    room_id = Column(GUID, ForeignKey("live_rooms.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(GUID, nullable=False)
    question = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)             # [{"key":"A","text":"…"}, …]
    answer = Column(String(10), nullable=True)         # 正确答案（教师设置，可选）
    status = Column(String(20), default="active")      # active | closed
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

class LiveQuizAnswer(Base):
    """直播答题作答（一题一次，覆盖改答）"""
    __tablename__ = "live_quiz_answers"
    __table_args__ = (
        UniqueConstraint("quiz_id", "user_id", name="uq_quiz_answer"),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    quiz_id = Column(GUID, ForeignKey("live_quizzes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, nullable=False)
    choice = Column(String(10), nullable=False)
    submitted_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)


# ─── 协作工具（V1.1 · D-02 · WBS-P 阶段 D）───
# 小组项目 / 看板 / 共享文件 / 组内讨论 —— 全部挂在课程（course）→ 小组（group）树上
class ProjectGroup(Base):
    """协作小组（所属课程）"""
    __tablename__ = "project_groups"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    leader_id = Column(GUID, nullable=False)          # 组长
    created_by = Column(GUID, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)


class GroupMember(Base):
    """小组成员（UNIQUE(group, user)）"""
    __tablename__ = "group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_member"),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    group_id = Column(GUID, ForeignKey("project_groups.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, nullable=False)
    joined_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)


class CollabProject(Base):
    """小组内的协作项目（含看板）"""
    __tablename__ = "projects"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    group_id = Column(GUID, ForeignKey("project_groups.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="not_started")  # not_started | in_progress | done
    deadline = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(GUID, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)


class KanbanColumn(Base):
    """看板列（属于项目）"""
    __tablename__ = "kanban_columns"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    project_id = Column(GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(50), nullable=False)
    order_num = Column(Integer, default=0)


class KanbanCard(Base):
    """看板卡片（任务卡，可拖拽换列/排位）"""
    __tablename__ = "kanban_cards"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    column_id = Column(GUID, ForeignKey("kanban_columns.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(GUID, nullable=True)
    order_num = Column(Integer, default=0)
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)


class SharedFile(Base):
    """小组共享文件（本地 uploads 目录，V1.1 简化存储）"""
    __tablename__ = "shared_files"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    group_id = Column(GUID, ForeignKey("project_groups.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    uploader_id = Column(GUID, nullable=False)
    filename = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=True)   # 空 = mock 占位
    size = Column(Integer, default=0)
    content_type = Column(String(100), default="application/octet-stream")
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)


class DiscussionTopic(Base):
    """组内讨论主题"""
    __tablename__ = "discussion_topics"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    group_id = Column(GUID, ForeignKey("project_groups.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(GUID, nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)


class DiscussionReply(Base):
    """讨论回复"""
    __tablename__ = "discussion_replies"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    topic_id = Column(GUID, ForeignKey("discussion_topics.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(GUID, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)


# ─── 消息通知（V1.1 · D-03 · WBS-P 阶段 D）───
class Notification(Base):
    """消息通知（欢迎引导 / 直播点名 / 作业批阅 / 公告等触发入栏）"""
    __tablename__ = "notifications"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, nullable=False, index=True)    # 接收者（无 FK，与 collab 成员同风格）
    type = Column(String(50), nullable=False)             # welcome | live_call | assignment_graded | course_announcement | system
    title = Column(String(120), nullable=False)
    content = Column(Text, nullable=True)
    ref_type = Column(String(50), nullable=True)          # 跳转引用：live_room / assignment / course / group
    ref_id = Column(GUID, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)


# ─── 题库与考试（V1.1 · D-04 · WBS-P 阶段 D）───
# 题库题目（课程归集） → 试卷（组卷明细） → 考试作答（每生每卷一次，自动评分）
class ExamQuestion(Base):
    """题库题目：题型 / 难度 / 标签 / 客观题 options+answer，主观题仅 title"""
    __tablename__ = "exam_questions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(GUID, nullable=True)             # 关联章节（可空）
    qtype = Column(String(20), default="single", nullable=False)  # single | multiple | true_false | short_answer
    title = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)                # [{"key":"A","text":"…"}, …] 客观题
    answer = Column(JSON, nullable=True)                 # 客观题选项数组 ["A"]；主观题为 null
    score = Column(Integer, default=5, nullable=False)
    difficulty = Column(String(10), default="medium", nullable=False)  # easy | medium | hard
    tags = Column(JSON, nullable=True)
    created_by = Column(GUID, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now)


class ExamPaper(Base):
    """试卷（组卷结果，题目经 exam_paper_questions 关联）"""
    __tablename__ = "exam_papers"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    start_at = Column(DateTime(timezone=True), nullable=True)
    end_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, default=60, nullable=False)
    total_score = Column(Integer, default=0, nullable=False)   # 随组卷自动累加
    status = Column(String(20), default="draft", nullable=False)  # draft | published | closed
    created_by = Column(GUID, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now)


class ExamPaperQuestion(Base):
    """试卷题目（组卷明细：单题分值可覆盖题库默认，排序）"""
    __tablename__ = "exam_paper_questions"
    __table_args__ = (
        UniqueConstraint("paper_id", "question_id", name="uq_paper_question"),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    paper_id = Column(GUID, ForeignKey("exam_papers.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(GUID, ForeignKey("exam_questions.id", ondelete="CASCADE"), nullable=False)
    order_num = Column(Integer, default=0)
    score = Column(Integer, default=5, nullable=False)


class ExamAttempt(Base):
    """考试作答（每生每卷一次；客观题提交自动评分，主观题等待教师人工补分）"""
    __tablename__ = "exam_attempts"
    __table_args__ = (
        UniqueConstraint("paper_id", "student_id", name="uq_exam_attempt"),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    paper_id = Column(GUID, ForeignKey("exam_papers.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(GUID, nullable=False)
    started_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="in_progress", nullable=False)  # in_progress | submitted
    answers = Column(JSON, nullable=True)    # [{question_id, answer, correct, manual_score}]
    auto_score = Column(Integer, default=0, nullable=False)   # 客观题得分
    manual_score = Column(Integer, default=0, nullable=False) # 主观题人工补分
    total_score = Column(Integer, default=0, nullable=False)


# ─── 学情分析 / 学生档案 / 辅导 / 预警（V1.1 · D-05 · WBS-P 阶段 D）───
# 教学分组（课程级，区分 collab.project_groups 协作小组）
class StudentGroup(Base):
    """教学分组：教师把选课学生分组便于管理/布置任务"""
    __tablename__ = "student_groups"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    teacher_id = Column(GUID, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now)


class StudentGroupMember(Base):
    """教学分组明细（UNIQUE(group, user)）"""
    __tablename__ = "student_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_student_group_member"),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    group_id = Column(GUID, ForeignKey("student_groups.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, nullable=False)
    joined_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)


class TutoringSession(Base):
    """辅导记录：教师/助教对学生的辅导纪要"""
    __tablename__ = "tutoring_sessions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    student_id = Column(GUID, nullable=False)
    tutor_id = Column(GUID, nullable=False)           # 辅导人（teacher/ta/admin）
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    mode = Column(String(20), default="online")       # online | offline
    topic = Column(String(200), nullable=False)
    notes = Column(Text, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), default=_now)
    duration_min = Column(Integer, default=30, nullable=False)
    outcome = Column(String(50), default="scheduled") # scheduled | completed | cancelled
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now)


class RiskAlert(Base):
    """风险预警记录：规则引擎自动生成，教师可标记处理"""
    __tablename__ = "risk_alerts"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    student_id = Column(GUID, nullable=False, index=True)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    level = Column(String(10), default="low", nullable=False)    # high | med | low
    reasons = Column(JSON, nullable=True)                        # ["absent_3", "score_drop_25"]
    metrics = Column(JSON, nullable=True)                        # 快照：当时成绩/出勤等
    resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(GUID, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now)


class LearningInsight(Base):
    """关键洞察（规则引擎按周生成，课程维度）"""
    __tablename__ = "learning_insights"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    week_start = Column(String(10), nullable=False)              # "2026-W08" 格式
    content = Column(Text, nullable=False)                       # 洞察文本
    suggestion = Column(String(200), nullable=True)              # 建议动作
    metrics = Column(JSON, nullable=True)                        # 触发数据
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)


# ─── 管理端（V1.1 · D-07/D-08 · WBS-P 阶段 D）───
# 课程审批 / 系统设置 / 审计日志 / 内容举报
class CourseApproval(Base):
    """课程审批记录：教师提交 → 管理员审核（通过/驳回）"""
    __tablename__ = "course_approvals"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, unique=True)
    submitted_by = Column(GUID, nullable=False)             # 提交教师
    reviewer_id = Column(GUID, nullable=True)               # 审核管理员
    status = Column(String(20), default="pending", nullable=False)  # pending | approved | rejected
    comment = Column(Text, nullable=True)                   # 审核意见
    submitted_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now)


class SystemSetting(Base):
    """系统设置（KV 结构，按 category 分组）"""
    __tablename__ = "system_settings"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    key = Column(String(100), unique=True, nullable=False)    # e.g. "site.name"
    value = Column(JSON, nullable=True)                       # 任意 JSON（字符串/数字/对象/数组）
    category = Column(String(50), default="general", nullable=False)  # general/security/notify/ai
    description = Column(String(300), nullable=True)
    updated_by = Column(GUID, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now)


class AuditLog(Base):
    """审计日志：记录业务操作（独立于 api_logs 的请求级日志）"""
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    actor_id = Column(GUID, nullable=True, index=True)        # 操作人（系统操作可空）
    action = Column(String(50), nullable=False, index=True)   # user.login / course.approve / setting.update ...
    target_type = Column(String(30), nullable=True)           # user / course / assignment / setting / report
    target_id = Column(GUID, nullable=True)
    details = Column(JSON, nullable=True)                     # 操作细节
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    status = Column(String(10), default="success")            # success | failed
    archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False, index=True)


class ContentReport(Base):
    """内容举报：用户对违规内容的举报（讨论/公告/文件等）"""
    __tablename__ = "content_reports"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    reporter_id = Column(GUID, nullable=False)                # 举报人
    target_type = Column(String(30), nullable=False)          # discussion / announcement / file / message
    target_id = Column(GUID, nullable=False)
    reason = Column(String(30), default="other", nullable=False)  # spam/abuse/harassment/copyright/other
    description = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending | reviewing | resolved | dismissed
    reviewer_id = Column(GUID, nullable=True)
    resolution = Column(Text, nullable=True)                  # 处理说明
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)


# ═══════════════════════════════════════════════════════════════════
# D-06 · 自主学习与闯关奖励
# ═══════════════════════════════════════════════════════════════════
class LearningPath(Base):
    """学习路径（闯关地图）"""
    __tablename__ = "learning_paths"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)            # 编程/设计/语言/数学 ...
    difficulty = Column(String(20), default="入门")           # 入门/进阶/硬核
    cover_emoji = Column(String(10), nullable=True)
    cover_gradient = Column(String(100), nullable=True)       # CSS gradient
    total_nodes = Column(Integer, default=0)                  # 关卡总数
    total_xp = Column(Integer, default=0)                     # 路径总 XP
    learner_count = Column(Integer, default=0)                # 在学人数
    published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now)


class LearningPathNode(Base):
    """路径节点（关卡）"""
    __tablename__ = "learning_path_nodes"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    path_id = Column(GUID, ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)                 # 顺序（1, 2, 3...）
    node_type = Column(String(20), nullable=False)             # reading / video / quiz / challenge
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    duration_min = Column(Integer, nullable=True)              # 预计时长
    xp_reward = Column(Integer, default=0)                     # 通关 XP
    content = Column(JSON, nullable=True)                      # 内容数据（视频 ID / 题目列表 / 文本）
    prerequisites = Column(JSON, nullable=True)                # 前置节点 ID 列表
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("path_id", "sequence", name="uq_path_node_seq"),
    )


class LearningPathProgress(Base):
    """路径学习进度（每用户每节点一行）"""
    __tablename__ = "learning_path_progress"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, nullable=False, index=True)
    path_id = Column(GUID, ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(GUID, ForeignKey("learning_path_nodes.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="locked")              # locked / current / done
    xp_earned = Column(Integer, default=0)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now)

    __table_args__ = (
        UniqueConstraint("user_id", "node_id", name="uq_user_node_progress"),
        Index("ix_progress_user_path", "user_id", "path_id"),
    )


class UserXP(Base):
    """用户经验值汇总（聚合表）"""
    __tablename__ = "user_xp"

    user_id = Column(GUID, primary_key=True)
    total_xp = Column(Integer, default=0, nullable=False)
    level = Column(Integer, default=1, nullable=False)
    streak_days = Column(Integer, default=0, nullable=False)   # 连续打卡天数
    last_checkin_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now)


class CheckInRecord(Base):
    """打卡记录（每日一次）"""
    __tablename__ = "check_in_records"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, nullable=False, index=True)
    checkin_date = Column(DateTime(timezone=True), nullable=False)    # 打卡日期（UTC 当天 00:00）
    xp_awarded = Column(Integer, default=10)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "checkin_date", name="uq_user_checkin_date"),
    )


class Badge(Base):
    """徽章定义（系统预置）"""
    __tablename__ = "badges"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)     # streak_7 / first_challenge / ...
    name = Column(String(100), nullable=False)
    description = Column(String(300), nullable=True)
    icon = Column(String(10), nullable=False)                  # emoji
    condition_type = Column(String(50), nullable=False)        # streak / xp / path_complete / ...
    condition_value = Column(Integer, default=0)               # 触发阈值
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)


class UserBadge(Base):
    """用户已获得徽章"""
    __tablename__ = "user_badges"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, nullable=False, index=True)
    badge_id = Column(GUID, ForeignKey("badges.id", ondelete="CASCADE"), nullable=False)
    earned_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
    )


class Challenge(Base):
    """闯关挑战（题目集合）"""
    __tablename__ = "challenges"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    node_id = Column(GUID, ForeignKey("learning_path_nodes.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    time_limit_min = Column(Integer, nullable=True)            # 限时（分钟）
    questions = Column(JSON, nullable=False)                   # 题目列表 [{q, options, answer}]
    max_attempts = Column(Integer, default=3)                  # 最大尝试次数
    pass_score = Column(Integer, default=60)                   # 及格分（百分制）
    xp_reward = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)


class ChallengeAttempt(Base):
    """闯关尝试记录"""
    __tablename__ = "challenge_attempts"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, nullable=False, index=True)
    challenge_id = Column(GUID, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False)
    answers = Column(JSON, nullable=True)                      # 用户答案
    score = Column(Integer, default=0)                         # 得分（百分制）
    passed = Column(Boolean, default=False)
    xp_earned = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)


# ═══════════════════════════════════════════════════════════════════
# D-08 · 教学视频与录播回放
# ═══════════════════════════════════════════════════════════════════
class Video(Base):
    """录播视频"""
    __tablename__ = "videos"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)               # 编程/数学/设计/语言 ...
    tags = Column(JSON, nullable=True)                         # 标签列表
    duration_sec = Column(Integer, default=0)                  # 时长（秒）
    video_url = Column(String(500), nullable=True)             # HLS/MP4 地址
    thumbnail_url = Column(String(500), nullable=True)
    cover_emoji = Column(String(10), nullable=True)
    cover_gradient = Column(String(100), nullable=True)
    view_count = Column(Integer, default=0)
    published = Column(Boolean, default=False)
    created_by = Column(GUID, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now)


class VideoChapter(Base):
    """视频章节（时间戳）"""
    __tablename__ = "video_chapters"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    video_id = Column(GUID, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    start_sec = Column(Integer, nullable=False)                # 章节起始秒数
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("video_id", "sequence", name="uq_video_chapter_seq"),
    )


class VideoNote(Base):
    """视频笔记（时间戳绑定）"""
    __tablename__ = "video_notes"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, nullable=False, index=True)
    video_id = Column(GUID, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    timestamp_sec = Column(Integer, nullable=False)            # 笔记绑定的时间点
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_video_notes_user_video", "user_id", "video_id"),
    )


class VideoWatchHistory(Base):
    """视频观看历史"""
    __tablename__ = "video_watch_history"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, nullable=False, index=True)
    video_id = Column(GUID, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    watched_sec = Column(Integer, default=0)                   # 已观看秒数
    total_sec = Column(Integer, default=0)                     # 视频总时长
    progress_pct = Column(Integer, default=0)                  # 进度百分比
    last_watched_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "video_id", name="uq_user_video_history"),
    )


# ═══════════════════════════════════════════════════════════════════
# D-09 · AI 基础设施（RAG / Agent / 内容审核）
# ═══════════════════════════════════════════════════════════════════

class KnowledgeBase(Base):
    """知识库（RAG 用）"""
    __tablename__ = "knowledge_bases"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    course_id = Column(GUID, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0)
    embedding_model = Column(String(100), default="text-embedding-v3")
    created_by = Column(GUID, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now)


class KnowledgeChunk(Base):
    """知识库分块（嵌入向量存储）"""
    __tablename__ = "knowledge_chunks"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    kb_id = Column(GUID, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)           # 来源/页码/章节等
    # 嵌入向量（MySQL 9.7 原生 VECTOR 类型，此处用 JSON 存储，Python 侧计算距离）
    embedding = Column(JSON, nullable=True)               # [0.1, 0.2, ...]
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_chunk_kb", "kb_id"),
    )


class AgentTool(Base):
    """Agent 工具定义（可供 Agent 调用）"""
    __tablename__ = "agent_tools"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)    # get_course_info / search_docs
    description = Column(Text, nullable=False)
    parameters_schema = Column(JSON, nullable=False)           # JSON Schema
    handler = Column(String(200), nullable=False)              # Python 函数路径
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)


class AgentSession(Base):
    """Agent 会话（多轮工具调用）"""
    __tablename__ = "agent_sessions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, nullable=False, index=True)
    title = Column(String(200), nullable=True)
    messages = Column(JSON, default=list)                      # 消息历史
    tool_calls = Column(JSON, default=list)                    # 工具调用记录
    status = Column(String(20), default="active")              # active / completed
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now)


class ModerationLog(Base):
    """内容审核日志"""
    __tablename__ = "moderation_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(GUID, nullable=True, index=True)
    content_type = Column(String(50), nullable=False)          # chat / note / discussion / file
    content_id = Column(GUID, nullable=True)
    content_text = Column(Text, nullable=True)
    flagged = Column(Boolean, default=False)                   # 是否触发审核
    reason = Column(String(100), nullable=True)                # 触发原因
    action = Column(String(20), default="pass")                # pass / flag / block
    created_at = Column(DateTime(timezone=True), default=_now, server_default=func.now(), nullable=False, index=True)


# ─── 监控共享表 ───
