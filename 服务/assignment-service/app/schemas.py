# ============================================
# Lumina 墨光 · Pydantic Schemas（作业模块）
# ============================================
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─── 通用 ───
class SuccessResponse(BaseModel):
    code: int = 0
    message: str = "success"


class Pagination(BaseModel):
    offset: int = 0
    limit: int = 20
    total: int
    has_more: bool


# ─── 作业 ───
class AssignmentCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    max_score: int = Field(100, ge=1, le=200)
    ai_grading: bool = False
    rubric: Optional[list[dict[str, Any]]] = None
    ai_model: Optional[str] = Field(None, max_length=50)


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    max_score: Optional[int] = None
    rubric: Optional[list[dict[str, Any]]] = None
    status: Optional[str] = Field(None, pattern="^(draft|published|closed)$")


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


# ─── 提交 ───
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


# ─── 批阅 ───
class GradeCreate(BaseModel):
    total_score: Decimal = Field(..., ge=0)
    grade_letter: Optional[str] = Field(None, pattern="^[A-F]?$")
    feedback: Optional[str] = None
    rubric_scores: Optional[dict[str, Any]] = None


SubmissionOut.model_rebuild()