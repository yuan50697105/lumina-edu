# ============================================
# Lumina 墨光 · AI 批阅服务 Pydantic Schemas
# ============================================
import uuid
from typing import Optional

from pydantic import BaseModel, Field


# ─── 批阅请求 ───
class RubricItem(BaseModel):
    criteria: str = Field(..., min_length=1, max_length=100, description="评分维度")
    weight: float = Field(0.0, ge=0, le=1, description="权重 0~1")
    max_score: int = Field(100, ge=1, le=1000, description="该维度满分")


class GradeRequest(BaseModel):
    assignment_id: uuid.UUID
    submission_id: uuid.UUID
    rubric: Optional[list[RubricItem]] = None       # 缺省取作业 rubric
    file_urls: Optional[list[str]] = None           # 附件（PDF/图片，仅供上下文展示）
    model_name: Optional[str] = Field(None, max_length=50)  # 指定模型，缺省智能路由(grade)
    max_tokens: int = Field(2048, ge=512, le=8192)
    temperature: Optional[float] = Field(None, ge=0, le=2)


# ─── 批阅结果 ───
class ScoreItem(BaseModel):
    criteria: str
    score: int
    max: int
    comment: str


class GradeResultData(BaseModel):
    scores: list[ScoreItem]
    total: int
    feedback: str
    model: str
    confidence: float


class GradeResult(BaseModel):
    code: int = 0
    data: GradeResultData