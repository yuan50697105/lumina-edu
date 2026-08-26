# ============================================
# Lumina 墨光 · Pydantic Schemas（成绩模块）
# ============================================
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ─── 通用 ───
class SuccessResponse(BaseModel):
    code: int = 0
    message: str = "success"


# ─── 成绩记录 ───
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


# ─── 学生成绩单 ───
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
class GradeStats(BaseModel):
    count: int = 0
    average: Optional[Decimal] = None
    highest: Optional[Decimal] = None
    lowest: Optional[Decimal] = None
    pass_rate: Optional[Decimal] = None          # 及格比例 0-1
    distribution: dict[str, int] = {}            # A/B/C/D/F 人数