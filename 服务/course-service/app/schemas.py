# ============================================
# Lumina 墨光 · Pydantic Schemas（课程模块）
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


# ─── 课程 ───
class TeacherBrief(BaseModel):
    id: uuid.UUID
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class CourseCreate(BaseModel):
    code: str = Field(..., max_length=20, description="课程编号，如 CS201")
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    department: Optional[str] = None
    credits: Optional[Decimal] = Field(None, ge=0, le=20)
    semester: str = Field(..., max_length=20, description="学期，如 2026-1")
    schedule: Optional[list[dict[str, Any]]] = None


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    department: Optional[str] = None
    credits: Optional[Decimal] = None
    schedule: Optional[list[dict[str, Any]]] = None
    status: Optional[str] = Field(None, pattern="^(draft|published|archived)$")


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
class EnrollmentOut(BaseModel):
    course_id: uuid.UUID
    role: str
    status: str
    enrolled_at: datetime
    course: CourseOut

    class Config:
        from_attributes = True


class StudentOut(BaseModel):
    id: uuid.UUID
    name: str
    avatar_url: Optional[str]
    role: str
    enrolled_at: datetime
    status: str


# ─── 章节 ───
class ChapterCreate(BaseModel):
    title: str = Field(..., max_length=200)
    content: Optional[str] = None
    order_num: int = 0
    resources: Optional[list[dict[str, Any]]] = None


class ChapterUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    order_num: Optional[int] = None
    resources: Optional[list[dict[str, Any]]] = None


# ─── 公告 ───
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