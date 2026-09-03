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


# ─── 题库与考试（V1.1 · D-04）───
# 题型：single 单选 / multiple 多选 / true_false 判断 / short_answer 简答
class QuestionCreate(BaseModel):
    qtype: str = Field("single", pattern="^(single|multiple|true_false|short_answer)$")
    title: str = Field(..., description="题干")
    options: Optional[list[dict[str, Any]]] = None   # 客观题 [{"key":"A","text":"…"}]
    answer: Optional[list] = None                    # 客观题答案数组 ["A"]；主观题为空/None
    score: int = Field(5, ge=1, le=100)
    difficulty: str = Field("medium", pattern="^(easy|medium|hard)$")
    tags: Optional[list[str]] = None
    chapter_id: Optional[uuid.UUID] = None

class QuestionUpdate(BaseModel):
    qtype: Optional[str] = Field(None, pattern="^(single|multiple|true_false|short_answer)$")
    title: Optional[str] = None
    options: Optional[list[dict[str, Any]]] = None
    answer: Optional[list] = None
    score: Optional[int] = Field(None, ge=1, le=100)
    difficulty: Optional[str] = Field(None, pattern="^(easy|medium|hard)$")
    tags: Optional[list[str]] = None
    chapter_id: Optional[uuid.UUID] = None

class QuestionOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    chapter_id: Optional[uuid.UUID] = None
    qtype: str
    title: str
    options: Optional[list[dict]] = None
    answer: Optional[list] = None                    # 仅教师/本人答卷场景可见
    score: int
    difficulty: str
    tags: Optional[list] = None
    created_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

class PaperCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    duration_minutes: int = Field(60, ge=5, le=480)

class PaperUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=5, le=480)
    status: Optional[str] = Field(None, pattern="^(draft|published|closed)$")

class PaperQuestionIn(BaseModel):
    """加题：指定题目（缺省分值用题目自身）"""
    question_id: uuid.UUID
    score: Optional[int] = Field(None, ge=1, le=100)

class AutoGenerateIn(BaseModel):
    """智能组卷条件（从课程题库按条件抽题）"""
    count: int = Field(10, ge=1, le=100)
    difficulty: Optional[str] = Field(None, pattern="^(easy|medium|hard)$")
    qtype_filter: Optional[str] = Field(None, pattern="^(single|multiple|true_false|short_answer)$")
    tag: Optional[str] = None
    score: Optional[int] = Field(None, ge=1, le=100)   # 单题分值（缺省用题目自身）

class PaperQuestionOut(BaseModel):
    id: uuid.UUID            # exam_paper_questions.id
    question_id: uuid.UUID
    order_num: int
    score: int
    qtype: str
    title: str
    difficulty: str
    options: Optional[list[dict]] = None
    answer: Optional[list] = None   # 仅教师侧序列化填充

    class Config:
        from_attributes = True

class PaperOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    course_title: Optional[str] = None
    title: str
    description: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    duration_minutes: int
    total_score: int
    status: str
    created_by: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    question_count: int = 0
    questions: list[PaperQuestionOut] = []     # 教师含 answer；学生剔除 answer
    my_attempt: Optional[dict] = None          # 学生侧：我的考试记录摘要

    class Config:
        from_attributes = True

class AttemptAnswerIn(BaseModel):
    """单题作答：客观题 answer=[选项…]；主观题 answer=[{"text":"…"}]"""
    question_id: uuid.UUID
    answer: list = []

class AttemptSubmitIn(BaseModel):
    answers: list[AttemptAnswerIn]

class ManualGradeIn(BaseModel):
    """主观题人工补分"""
    question_id: uuid.UUID
    score: int = Field(..., ge=0, le=200)

class AttemptOut(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    started_at: datetime
    submitted_at: Optional[datetime] = None
    status: str                          # in_progress | submitted
    auto_score: int
    manual_score: int
    total_score: int
    answers: Optional[list[dict]] = None
    paper_title: Optional[str] = None
    question_count: int = 0

    class Config:
        from_attributes = True

class PaperStatsOut(BaseModel):
    paper_id: uuid.UUID
    submitted_count: int
    average_score: float
    highest_score: int
    lowest_score: int
    question_stats: list[dict] = []      # [{question_id,title,qtype,correct_count,answered_count,accuracy}]

class StartAttemptOut(BaseModel):
    attempt_id: uuid.UUID
    started_at: datetime
    end_at: Optional[datetime] = None    # 提交截止（start + 时长 / 试卷截止早者）
    duration_minutes: int
    questions: list[PaperQuestionOut] = []   # 不含答案


# ═══════════════════════════════════════════════════════════════════
# D-05 · 学情分析 / 学生档案 / 辅导 / 教学分组 / 批量操作
# ═══════════════════════════════════════════════════════════════════

# ─── 学情分析 ───
class CourseOverviewOut(BaseModel):
    """课程学情概览"""
    course_id: uuid.UUID
    course_title: str
    semester: str
    student_count: int                   # 选课人数
    average_score: Optional[float] = None
    attendance_rate: Optional[float] = None     # 0~1
    submission_rate: Optional[float] = None     # 作业完成率 0~1
    risk_count: int = 0                  # 风险学生数
    risk_high: int = 0
    risk_med: int = 0
    risk_low: int = 0
    vs_previous: Optional[dict] = None   # {"average_score": +3, "attendance": +0.02}

class TrendPoint(BaseModel):
    week: str                            # "2026-W08"
    average_score: Optional[float] = None
    submission_rate: Optional[float] = None
    attendance_rate: Optional[float] = None

class CourseTrendOut(BaseModel):
    course_id: uuid.UUID
    weeks: list[TrendPoint]

class DistributionBucket(BaseModel):
    range_label: str                     # "90-100" / "80-89" / "70-79" / "60-69" / "<60"
    count: int
    percentage: float                    # 0~1

class CourseDistributionOut(BaseModel):
    course_id: uuid.UUID
    assessment_type: str                 # midterm / final / overall / assignment
    total_students: int
    buckets: list[DistributionBucket]

class InsightOut(BaseModel):
    id: uuid.UUID
    week_start: str
    content: str
    suggestion: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class CourseInsightsOut(BaseModel):
    course_id: uuid.UUID
    insights: list[InsightOut]

class ProgressStudent(BaseModel):
    student_id: uuid.UUID
    student_name: str
    student_student_id: Optional[str] = None
    delta: float                         # 进步分值
    from_score: Optional[float] = None
    to_score: Optional[float] = None
    highlights: list[str] = []           # 亮点（主动提问/作业完成率等）

class CourseProgressOut(BaseModel):
    course_id: uuid.UUID
    top_improved: list[ProgressStudent]  # 本周进步前 N

class RiskStudent(BaseModel):
    student_id: uuid.UUID
    student_name: str
    student_student_id: Optional[str] = None
    level: str                           # high | med | low
    reasons: list[str] = []
    score_trend: Optional[float] = None  # 最近一次成绩/均分

class CourseRisksOut(BaseModel):
    course_id: uuid.UUID
    total: int
    risks: list[RiskStudent]

class RiskAlertOut(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    student_student_id: Optional[str] = None
    course_id: uuid.UUID
    level: str
    reasons: Optional[list[str]] = None
    resolved: bool
    resolved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AlertRuleIn(BaseModel):
    """预警规则阈值（管理员配置）"""
    absent_threshold: int = Field(3, ge=1, le=10)       # 连续缺席次数触发高风险
    submission_low: float = Field(0.5, ge=0, le=1)      # 作业完成率低于该值触发高风险
    submission_mid: float = Field(0.7, ge=0, le=1)      # 作业完成率低于该值触发中风险
    score_drop_high: float = Field(0.2, ge=0, le=1)     # 成绩下降超过该比例触发高风险
    score_drop_mid: float = Field(0.1, ge=0, le=1)      # 成绩下降超过该比例触发中风险
    inactive_days_high: int = Field(14, ge=1, le=60)    # 连续未登录天数触发高风险
    inactive_days_mid: int = Field(7, ge=1, le=60)      # 连续未登录天数触发中风险

# ─── 学生档案 ───
class StudentProfileOut(BaseModel):
    """学生档案：基本信息 + 选课 + 成绩趋势 + 预警 + 辅导"""
    student_id: uuid.UUID
    student_name: str
    student_student_id: Optional[str] = None
    department: Optional[str] = None
    grade: Optional[str] = None
    avatar_url: Optional[str] = None
    email: Optional[str] = None
    enrolled_courses: list[dict] = []    # [{course_id, title, semester, final_score, gpa_point}]
    overall_gpa: Optional[float] = None
    score_trend: list[TrendPoint] = []   # 各学期/各课程成绩曲线
    active_alerts: list[RiskAlertOut] = []
    recent_tutoring: list[dict] = []     # 近 5 次辅导

# ─── 辅导记录 ───
class TutoringSessionCreate(BaseModel):
    student_id: uuid.UUID
    course_id: Optional[uuid.UUID] = None
    mode: str = Field("online", pattern="^(online|offline)$")
    topic: str = Field(..., min_length=1, max_length=200)
    notes: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_min: int = Field(30, ge=5, le=480)

class TutoringSessionUpdate(BaseModel):
    mode: Optional[str] = Field(None, pattern="^(online|offline)$")
    topic: Optional[str] = None
    notes: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_min: Optional[int] = Field(None, ge=5, le=480)
    outcome: Optional[str] = None        # scheduled | completed | cancelled

class TutoringSessionOut(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    tutor_id: uuid.UUID
    tutor_name: Optional[str] = None
    course_id: Optional[uuid.UUID] = None
    course_title: Optional[str] = None
    mode: str
    topic: str
    notes: Optional[str] = None
    scheduled_at: datetime
    duration_min: int
    outcome: str
    created_at: datetime

    class Config:
        from_attributes = True

# ─── 教学分组 ───
class StudentGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    member_ids: list[uuid.UUID] = Field(default_factory=list)

class StudentGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None

class StudentGroupMemberOut(BaseModel):
    user_id: uuid.UUID
    name: str
    student_id: Optional[str] = None
    joined_at: datetime

    class Config:
        from_attributes = True

class StudentGroupOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    name: str
    description: Optional[str] = None
    teacher_id: uuid.UUID
    teacher_name: Optional[str] = None
    member_count: int = 0
    members: list[StudentGroupMemberOut] = []
    created_at: datetime

    class Config:
        from_attributes = True

# ─── 批量操作 ───
class BatchImportRow(BaseModel):
    """单行导入"""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=50)
    student_id: Optional[str] = Field(None, max_length=20)
    role: str = Field("student", pattern="^(student|teacher|admin)$")
    department: Optional[str] = Field(None, max_length=100)
    grade: Optional[str] = Field(None, max_length=10)

class BatchImportIn(BaseModel):
    """批量导入"""
    users: list[BatchImportRow] = Field(..., min_length=1, max_length=500)
    default_password: Optional[str] = Field(None, min_length=8, max_length=64)

class BatchUpdateIn(BaseModel):
    """批量更新（角色/状态）"""
    user_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=200)
    new_role: Optional[str] = Field(None, pattern="^(student|teacher|admin)$")
    # 注：V1 不支持 status 字段（users 表无 status），预留

class BatchToggleIn(BaseModel):
    """批量启用/禁用：V1 通过删除/重建 refresh token 模拟"""
    user_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=200)
    action: str = Field(..., pattern="^(enable|disable)$")

class BatchResultOut(BaseModel):
    """批量操作结果"""
    total: int
    success: int
    failed: int
    errors: list[dict] = []              # [{user_id/email, message}]


# ═══════════════════════════════════════════════════════════════════
# D-07/D-08 · 管理端补齐 · 监控大盘 / 课程审批 / 系统设置 / 审计 / 举报
# ═══════════════════════════════════════════════════════════════════

# ─── 监控大盘 ───
class DashboardOverview(BaseModel):
    """监控大盘总览"""
    total_users: int
    total_students: int
    total_teachers: int
    total_courses: int
    active_courses: int                  # 近 30 天有活动
    dau: int                             # 日活跃用户
    mau: int                             # 月活跃用户
    pending_approvals: int
    pending_reports: int
    today_registrations: int

class GrowthPoint(BaseModel):
    month: str                           # "2026-01"
    new_users: int
    new_courses: int
    active_users: int

class DashboardGrowth(BaseModel):
    months: list[GrowthPoint]

class HealthMetric(BaseModel):
    name: str                            # "api" / "db" / "ai"
    status: str                          # healthy / degraded / down
    uptime_pct: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    error_rate: Optional[float] = None

class DashboardHealth(BaseModel):
    metrics: list[HealthMetric]
    sla_target: float = 99.9             # 目标 SLA %
    overall_status: str                  # healthy / degraded / down

class RecentActivityItem(BaseModel):
    id: uuid.UUID
    type: str                            # audit / report / approval
    action: str
    actor_name: Optional[str] = None
    target: Optional[str] = None
    created_at: datetime

class DashboardRecentActivity(BaseModel):
    items: list[RecentActivityItem]

# ─── 课程审批 ───
class CourseApprovalSubmit(BaseModel):
    """教师提交课程审批（可带备注）"""
    note: Optional[str] = Field(None, max_length=500)

class CourseApprovalReview(BaseModel):
    """管理员审核（通过/驳回）"""
    comment: Optional[str] = Field(None, max_length=1000)

class CourseApprovalOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    course_title: Optional[str] = None
    course_code: Optional[str] = None
    submitted_by: uuid.UUID
    submitter_name: Optional[str] = None
    reviewer_id: Optional[uuid.UUID] = None
    reviewer_name: Optional[str] = None
    status: str                          # pending | approved | rejected
    comment: Optional[str] = None
    note: Optional[str] = None           # 提交时的备注（存 details 或单独字段）
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CourseApprovalStatusOut(BaseModel):
    """课程当前审批状态"""
    course_id: uuid.UUID
    has_approval: bool
    status: Optional[str] = None         # pending | approved | rejected
    approval_id: Optional[uuid.UUID] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    comment: Optional[str] = None

# ─── 系统设置 ───
class SettingOut(BaseModel):
    key: str
    value: Optional[Any] = None
    category: str
    description: Optional[str] = None
    updated_by: Optional[uuid.UUID] = None
    updater_name: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True

class SettingUpdate(BaseModel):
    value: Any
    description: Optional[str] = None

class SettingBatchItem(BaseModel):
    key: str
    value: Any

class SettingBatchIn(BaseModel):
    items: list[SettingBatchItem] = Field(..., min_length=1, max_length=100)

class SettingCategoryOut(BaseModel):
    category: str
    count: int
    keys: list[str]

# ─── 审计日志 ───
class AuditLogOut(BaseModel):
    id: int
    actor_id: Optional[uuid.UUID] = None
    actor_name: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[uuid.UUID] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    status: str
    archived: bool
    created_at: datetime

    class Config:
        from_attributes = True

class AuditExportOut(BaseModel):
    """审计导出结果"""
    total: int
    exported: int
    download_url: Optional[str] = None   # V1 直接返回 CSV 内容，此字段保留

# ─── 内容举报 ───
class ReportCreate(BaseModel):
    target_type: str = Field(..., pattern="^(discussion|announcement|file|message|course|user)$")
    target_id: uuid.UUID
    reason: str = Field("other", pattern="^(spam|abuse|harassment|copyright|nsfw|other)$")
    description: Optional[str] = Field(None, max_length=1000)

class ReportResolve(BaseModel):
    status: str = Field(..., pattern="^(resolved|dismissed)$")
    resolution: Optional[str] = Field(None, max_length=1000)

class ReportOut(BaseModel):
    id: uuid.UUID
    reporter_id: uuid.UUID
    reporter_name: Optional[str] = None
    target_type: str
    target_id: uuid.UUID
    reason: str
    description: Optional[str] = None
    status: str                          # pending | reviewing | resolved | dismissed
    reviewer_id: Optional[uuid.UUID] = None
    reviewer_name: Optional[str] = None
    resolution: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


