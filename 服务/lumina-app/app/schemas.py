# ============================================
# Lumina 墨光 · 统一 Pydantic Schemas（合并 9 微服务）
# ============================================
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class SuccessResponse(BaseModel):
    code: int = 0
    message: str = "success"


# ─── 用户 ───

class Pagination(BaseModel):
    offset: int = 0
    limit: int = 20
    total: int
    has_more: bool


# ─── 课程 ───

class AnnouncementCreate(BaseModel):
    title: str = Field(..., max_length=200)
    content: Optional[str] = None
    pinned: bool = False

class AnnouncementOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    author_id: uuid.UUID
    title: str
    content: Optional[str]
    pinned: bool
    created_at: datetime

    class Config:
        from_attributes = True

class AssignmentCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    max_score: int = Field(100, ge=1, le=200)
    ai_grading: bool = False
    rubric: Optional[list[dict[str, Any]]] = None
    ai_model: Optional[str] = Field(None, max_length=50)

class AssignmentOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: Optional[str]
    due_at: Optional[datetime]
    max_score: int
    ai_grading: bool
    rubric: Optional[list[dict]]
    ai_model: Optional[str]
    status: str
    created_at: datetime
    # 扩展字段（列表/详情联查）
    course_title: Optional[str] = None
    submission_count: Optional[int] = None
    my_status: Optional[str] = None  # not_submitted | submitted | graded

    class Config:
        from_attributes = True


# ─── 提交 ───

class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    max_score: Optional[int] = None
    rubric: Optional[list[dict[str, Any]]] = None
    status: Optional[str] = Field(None, pattern="^(draft|published|closed)$")

class BreakdownRow(BaseModel):
    event_name: str
    count: int
    distinct_users: int


# ─── 通用 ───

class CallRecordRequest(BaseModel):
    model_id: uuid.UUID
    task_type: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    ok: bool = True
    error_message: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


# ─── 埋点 ───

class ChapterCreate(BaseModel):
    title: str = Field(..., max_length=200)
    content: Optional[str] = None
    order_num: int = 0
    resources: Optional[list[dict[str, Any]]] = None

class ChapterOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    content: Optional[str]
    order_num: int
    resources: Optional[list[dict]]
    created_at: datetime

    class Config:
        from_attributes = True

class ChapterUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    order_num: Optional[int] = None
    resources: Optional[list[dict[str, Any]]] = None


# ─── 公告 ───

class ChatContext(BaseModel):
    course_id: Optional[uuid.UUID] = None
    chapter_id: Optional[uuid.UUID] = None

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str

class ChatRequest(BaseModel):
    conversation_id: Optional[uuid.UUID] = None   # 传则续聊该会话
    message: str = Field(..., min_length=1, max_length=8000)
    context: Optional[ChatContext] = None         # 课程/章节上下文
    attachments: Optional[list[dict]] = None      # 图片/音频附件占位
    model_name: Optional[str] = Field(None, max_length=50)  # 指定模型，缺省走智能路由
    max_tokens: int = Field(2048, ge=64, le=16384)
    temperature: Optional[float] = Field(None, ge=0, le=2)


# ─── 对话历史 ───

class CompletionsOut(BaseModel):
    content: str
    model: Optional[str]
    finish_reason: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0


# ─── 对外模型列表 ───

class CompletionsRequest(BaseModel):
    model_id: Optional[uuid.UUID] = None          # 二选一
    model_name: Optional[str] = None              # 二选一
    messages: list[ChatMessage] = Field(..., min_length=1)
    task_type: str = Field("chat", pattern="^(chat|grade|generate)$")
    max_tokens: int = Field(2048, ge=64, le=16384)
    temperature: Optional[float] = Field(None, ge=0, le=2)
    stream: bool = False

class ConversationOut(BaseModel):
    id: uuid.UUID
    title: Optional[str]
    model: Optional[str]
    context_course_id: Optional[uuid.UUID]
    context_chapter_id: Optional[uuid.UUID]
    message_count: int
    total_tokens: int
    created_at: datetime
    updated_at: datetime

class CourseCreate(BaseModel):
    code: str = Field(..., max_length=20, description="课程编号，如 CS201")
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    department: Optional[str] = None
    credits: Optional[Decimal] = Field(None, ge=0, le=20)
    semester: str = Field(..., max_length=20, description="学期，如 2026-1")
    schedule: Optional[list[dict[str, Any]]] = None

class TeacherBrief(BaseModel):
    id: uuid.UUID
    name: Optional[str] = None
    avatar_url: Optional[str] = None

class CourseOut(BaseModel):
    id: uuid.UUID
    code: str
    title: str
    description: Optional[str]
    teacher: Optional[TeacherBrief]
    department: Optional[str]
    credits: Optional[Decimal]
    semester: str
    schedule: Optional[list[dict]]
    students_count: int
    status: str
    created_at: datetime


# ─── 选课 ───

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    department: Optional[str] = None
    credits: Optional[Decimal] = None
    schedule: Optional[list[dict[str, Any]]] = None
    status: Optional[str] = Field(None, pattern="^(draft|published|archived)$")

class EnrollmentOut(BaseModel):
    course_id: uuid.UUID
    role: str
    status: str
    enrolled_at: datetime
    course: CourseOut

    class Config:
        from_attributes = True

class EventBatch(BaseModel):
    events: list["EventIn"] = Field(..., min_length=1, max_length=100)


# ─── 统计查询 ───

class EventIn(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=100)
    user_id: Optional[str] = Field(None, max_length=36, description="游客标识（登录用户由服务端 JWT 覆盖）")
    session_id: Optional[str] = Field(None, max_length=100)
    page_url: Optional[str] = Field(None, max_length=500)
    properties: Optional[dict] = None

class EventTrackOut(BaseModel):
    event_name: str
    user_id: Optional[uuid.UUID]
    properties: Optional[dict]
    created_at: datetime

class EventTrackRequest(BaseModel):
    event_name: str
    properties: Optional[dict[str, Any]] = None
    course_id: Optional[uuid.UUID] = None
    page_url: Optional[str] = None

class GradeCreate(BaseModel):
    total_score: Decimal = Field(..., ge=0)
    grade_letter: Optional[str] = Field(None, pattern="^[A-F]?$")
    feedback: Optional[str] = None
    rubric_scores: Optional[dict[str, Any]] = None


class GradeOut(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    total_score: Optional[Decimal]
    grade_letter: Optional[str]
    feedback: Optional[str]
    rubric_scores: Optional[dict]
    graded_by: str
    grader_id: Optional[uuid.UUID]
    ai_model: Optional[str]
    confidence: Optional[Decimal]
    graded_at: datetime

    class Config:
        from_attributes = True


# ─── 批阅 ───

class GradeRecordCreate(BaseModel):
    student_id: uuid.UUID
    final_score: Decimal = Field(..., ge=0, le=100)
    semester: str = Field(..., max_length=20)
    gpa_point: Optional[Decimal] = Field(None, ge=0, le=4)

class GradeRecordOut(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    student_no: Optional[str] = None
    course_id: uuid.UUID
    semester: str
    final_score: Optional[Decimal]
    gpa_point: Optional[Decimal]
    grade_letter: Optional[str] = None
    recorded_at: datetime

    class Config:
        from_attributes = True


# ─── 学生成绩单 ───

class GradeRequest(BaseModel):
    assignment_id: uuid.UUID
    submission_id: uuid.UUID
    rubric: Optional[list["RubricItem"]] = None       # 缺省取作业 rubric
    file_urls: Optional[list[str]] = None           # 附件（PDF/图片，仅供上下文展示）
    model_name: Optional[str] = Field(None, max_length=50)  # 指定模型，缺省智能路由(grade)
    max_tokens: int = Field(2048, ge=512, le=8192)
    temperature: Optional[float] = Field(None, ge=0, le=2)


# ─── 批阅结果 ───

class GradeResult(BaseModel):
    code: int = 0
    data: "GradeResultData"

class GradeResultData(BaseModel):
    scores: list["ScoreItem"]
    total: int
    feedback: str
    model: str
    confidence: float

class GradeStats(BaseModel):
    count: int = 0
    average: Optional[Decimal] = None
    highest: Optional[Decimal] = None
    lowest: Optional[Decimal] = None
    pass_rate: Optional[Decimal] = None          # 及格比例 0-1
    distribution: dict[str, int] = {}            # A/B/C/D/F 人数

class LogQueryOut(BaseModel):
    records: list["LogRecordOut"]
    total: int
    offset: int
    limit: int

class LogRecordOut(BaseModel):
    id: int
    method: str
    path: str
    status_code: Optional[int]
    duration_ms: Optional[int]
    user_id: Optional[str]
    request_id: Optional[str]
    error_message: Optional[str]
    created_at: Optional[datetime]

class LogSummaryOut(BaseModel):
    total: int
    errors: int
    error_rate: float
    avg_duration_ms: float
    max_duration_ms: Optional[int]
    top_paths: list["TopPath"]

class LoginRequest(BaseModel):
    username: str = Field(..., description="学号/工号或邮箱")
    password: str
    device: str = Field("web", pattern="^(web|mobile|desktop)$")

class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: Optional[str]
    attachments: Optional[list[dict]]
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    created_at: datetime


# ─── 通用 ───

class ModelCreate(BaseModel):
    provider_name: str = Field(..., max_length=30, description="所属供应商 name")
    model_name: str = Field(..., max_length=50)
    display_name: str = Field(..., max_length=50)
    task_types: list[str] = Field(..., description="chat/grade/generate/vl/speech")
    description: Optional[str] = None
    priority: int = 10
    cost_per_1k_tokens: Decimal = Decimal("0")
    max_tokens: int = 4096
    openai_compatible: bool = True
    api_style: str = Field("openai", pattern="^(openai|anthropic|gemini)$",
                           description="协议风格：openai / anthropic / gemini")

class ModelOut(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    provider_name: Optional[str] = None
    model_name: str
    display_name: str
    task_types: list[Any]
    description: Optional[str]
    enabled: bool
    priority: int
    cost_per_1k_tokens: Optional[Decimal]
    max_tokens: int
    openai_compatible: bool
    api_style: Optional[str] = None


# ─── 智能路由 ───
CHAT = "chat"
GRADE = "grade"
GENERATE = "generate"
VL = "vl"
SPEECH = "speech"
TASK_TYPES = [CHAT, GRADE, GENERATE, VL, SPEECH]

class ModelUpdate(BaseModel):
    display_name: Optional[str] = None
    task_types: Optional[list[str]] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    cost_per_1k_tokens: Optional[Decimal] = None
    api_style: Optional[str] = Field(None, pattern="^(openai|anthropic|gemini)$",
                                     description="协议风格变更")

class MyCourseGrade(BaseModel):
    course_id: uuid.UUID
    title: str
    credit: Optional[Decimal]
    score: Optional[Decimal]
    grade: Optional[str]
    semester: str

class MyGrades(BaseModel):
    gpa: Optional[Decimal] = None
    total_credits: Optional[Decimal] = None
    course_count: int = 0
    courses: list[MyCourseGrade] = []


# ─── 统计 ───

class ProviderCreate(BaseModel):
    name: str = Field(..., max_length=30, pattern="^[a-z0-9_-]+$")
    display_name: str = Field(..., max_length=50)
    description: Optional[str] = None
    endpoint_base: Optional[str] = Field(None, max_length=300, description="API Base URL（如开箱即用：OpenAI 系列家用家 base/v1）")
    monthly_quota: Decimal = Field(Decimal("0"), ge=0)

class ProviderOut(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    description: Optional[str]
    domain: Optional[str]
    endpoint_base: Optional[str]
    enabled: bool
    monthly_quota: Optional[Decimal]
    used_quota: Optional[Decimal]
    created_at: datetime

class PublicModel(BaseModel):
    model_name: str
    display_name: str
    provider: str
    task_types: list[Any]
    description: Optional[str]
    cost_per_1k_tokens: Optional[Decimal]

class RefreshRequest(BaseModel):
    refresh_token: str

class RouteRequest(BaseModel):
    task_type: str = Field(..., pattern=f"^({'|'.join(TASK_TYPES)})$")

class RouteResult(BaseModel):
    task_type: str
    primary: Optional[ModelOut]
    fallback: Optional[ModelOut]
    note: str


# ─── 用量 ───

class RubricItem(BaseModel):
    criteria: str = Field(..., min_length=1, max_length=100, description="评分维度")
    weight: float = Field(0.0, ge=0, le=1, description="权重 0~1")
    max_score: int = Field(100, ge=1, le=1000, description="该维度满分")

class ScoreItem(BaseModel):
    criteria: str
    score: int
    max: int
    comment: str

class StatsOut(BaseModel):
    total: int = 0
    distinct_users: int = 0
    distinct_sessions: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

class StudentOut(BaseModel):
    id: uuid.UUID
    name: str
    avatar_url: Optional[str]
    role: str
    enrolled_at: datetime
    status: str


# ─── 章节 ───

class SubmissionCreate(BaseModel):
    text_answer: Optional[str] = None
    submission_note: Optional[str] = None
    file_urls: Optional[list[str]] = None

class SubmissionOut(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    file_urls: Optional[list[str]]
    text_answer: Optional[str]
    submission_note: Optional[str]
    submitted_at: datetime
    late: bool
    # 批阅结果联查
    graded: bool = False
    grade: Optional["GradeOut"] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: "UserOut"

class TopPath(BaseModel):
    path: str
    calls: int
    errors: int
    avg_duration_ms: float

class UsageStats(BaseModel):
    total_calls: int = 0
    total_tokens: int = 0
    total_cost: Decimal = Decimal("0")
    by_model: dict[str, dict] = {}
    by_user: dict[str, dict] = {}


# ─── 统一调用（completions）───

class UserBase(BaseModel):
    name: str
    email: EmailStr
    student_id: Optional[str] = None
    role: str = "student"
    department: Optional[str] = None
    grade: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="密码至少 8 位")

class UserOut(BaseModel):
    id: uuid.UUID
    student_id: Optional[str]
    name: str
    email: EmailStr
    role: str
    department: Optional[str]
    grade: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── 认证 ───

class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


# ─── 直播 Live（V1.1 · D-01 · WBS-P 阶段 D）───

class LiveRoomCreate(BaseModel):
    """创建直播房间（教师）"""
    course_id: uuid.UUID
    title: Optional[str] = None      # 缺省用课程名 + 日期

class LiveRoomOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    course_title: Optional[str] = None
    teacher_id: uuid.UUID
    teacher_name: Optional[str] = None
    title: str
    status: str                      # scheduled | live | ended
    stream_url: Optional[str] = None # HLS 播放地址（start 后由适配层注入；未接媒体服务器为 mock:// 占位）
    viewer_count: Optional[int] = 0  # 累计人次
    online_count: Optional[int] = 0  # 当前在线
    active_call: Optional[dict] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LiveRaiseRequest(BaseModel):
    """举手 / 取消举手"""
    active: bool = True

class LiveRaiseOut(BaseModel):
    """举手队列成员"""
    id: uuid.UUID
    user_id: uuid.UUID
    name: Optional[str] = None
    raised_at: Optional[datetime] = None

class LiveMessageCreate(BaseModel):
    """直播消息（聊天等）"""
    msg_type: str = "chat"           # chat | system | call
    content: str

class LiveMessageOut(BaseModel):
    id: int
    room_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    user_name: Optional[str] = None
    role: Optional[str] = None
    msg_type: str
    content: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class LiveQuizCreate(BaseModel):
    """发起答题（教师）"""
    question: str
    options: list[dict]              # [{"key":"A","text":"…"}, …]
    answer: Optional[str] = None     # 可选正确答案

class LiveQuizOut(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    teacher_id: uuid.UUID
    question: str
    options: list
    answer: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LiveQuizAnswerIn(BaseModel):
    """作答（学生）"""
    choice: str

class LiveQuizAnswerOut(BaseModel):
    quiz_id: uuid.UUID
    choice: str
    submitted_at: datetime

class LiveQuizResult(BaseModel):
    """答题统计（教师）"""
    quiz_id: uuid.UUID
    question: str
    total: int = 0
    distribution: dict[str, int] = {}
    correct_count: Optional[int] = None
    correct_rate: Optional[float] = None

class LiveCallIn(BaseModel):
    """点名（教师；不传 user_id 则随机在线学生）"""
    user_id: Optional[uuid.UUID] = None

class LiveCallOut(BaseModel):
    user_id: uuid.UUID
    name: str
    called_at: datetime


# ─── 协作工具（V1.1 · D-02）───
# 小组 / 成员 / 项目 / 看板（列·卡片）/ 共享文件 / 讨论（主题·回复）

class GroupCreate(BaseModel):
    """创建小组（教师）"""
    name: str
    description: Optional[str] = None
    leader_id: Optional[uuid.UUID] = None   # 缺省 = 创建人

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    leader_id: Optional[uuid.UUID] = None

class GroupMemberOut(BaseModel):
    id: uuid.UUID
    name: Optional[str] = None

    class Config:
        from_attributes = True

class GroupOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    course_title: Optional[str] = None
    name: str
    description: Optional[str] = None
    leader_id: uuid.UUID
    leader_name: Optional[str] = None
    member_count: int = 0
    project_count: int = 0
    created_at: datetime
    members: list[GroupMemberOut] = []
    is_member: bool = False

    class Config:
        from_attributes = True

class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[datetime] = None

class ProjectOut(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: Optional[str] = None
    status: str = "not_started"
    deadline: Optional[datetime] = None
    created_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

class CardCreate(BaseModel):
    """新建卡片（任务卡）"""
    title: str
    description: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None
    due_date: Optional[datetime] = None

class CardUpdate(BaseModel):
    """更新卡片（含拖拽换列：column_id / order_num）"""
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None
    order_num: Optional[int] = None
    column_id: Optional[uuid.UUID] = None
    due_date: Optional[datetime] = None

class CardOut(BaseModel):
    id: uuid.UUID
    column_id: uuid.UUID
    title: str
    description: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None
    assignee_name: Optional[str] = None
    order_num: int = 0
    due_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ColumnCreate(BaseModel):
    title: str

class ColumnUpdate(BaseModel):
    title: Optional[str] = None
    order_num: Optional[int] = None

class ColumnOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    order_num: int = 0
    cards: list[CardOut] = []

    class Config:
        from_attributes = True

class BoardOut(BaseModel):
    project_id: uuid.UUID
    columns: list[ColumnOut] = []

class FileOut(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    filename: str
    size: int = 0
    content_type: str = ""
    uploader_id: uuid.UUID
    uploader_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TopicCreate(BaseModel):
    title: str
    content: Optional[str] = None

class ReplyIn(BaseModel):
    content: str

class ReplyOut(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    author_id: uuid.UUID
    author_name: Optional[str] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class TopicOut(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    author_id: uuid.UUID
    author_name: Optional[str] = None
    title: str
    content: Optional[str] = None
    reply_count: int = 0
    created_at: datetime
    replies: list[ReplyOut] = []

    class Config:
        from_attributes = True


# ─── 消息通知（V1.1 · D-03）───

class NotificationOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    title: str
    content: Optional[str] = None
    ref_type: Optional[str] = None
    ref_id: Optional[uuid.UUID] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

    class Config:
        from_attributes = True


class UnreadCountOut(BaseModel):
    unread_count: int


# ─── 认证 · 注册（V1.1 · D-03）───

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="姓名")
    email: EmailStr
    password: str = Field(..., min_length=8, description="密码至少 8 位")
    student_id: Optional[str] = Field(None, max_length=20, description="学号/工号（可选）")
    role: str = Field("student", pattern="^(student|teacher)$", description="仅允许学生/教师自助注册")
    department: Optional[str] = None
    grade: Optional[str] = None
    device: str = Field("web", pattern="^(web|mobile|desktop)$")
