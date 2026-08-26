# ============================================
# Lumina 墨光 · Pydantic Schemas（AI 网关）
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


# ─── 模型池管理 ───
class ProviderCreate(BaseModel):
    name: str = Field(..., max_length=30, pattern="^[a-z0-9_-]+$")
    display_name: str = Field(..., max_length=50)
    description: Optional[str] = None
    monthly_quota: Decimal = Field(Decimal("0"), ge=0)


class ProviderOut(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    description: Optional[str]
    domain: Optional[str]
    enabled: bool
    monthly_quota: Optional[Decimal]
    used_quota: Optional[Decimal]
    created_at: datetime


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


class ModelUpdate(BaseModel):
    display_name: Optional[str] = None
    task_types: Optional[list[str]] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    cost_per_1k_tokens: Optional[Decimal] = None


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


# ─── 智能路由 ───
CHAT = "chat"
GRADE = "grade"
GENERATE = "generate"
VL = "vl"
SPEECH = "speech"
TASK_TYPES = [CHAT, GRADE, GENERATE, VL, SPEECH]


class RouteRequest(BaseModel):
    task_type: str = Field(..., pattern=f"^({'|'.join(TASK_TYPES)})$")


class RouteResult(BaseModel):
    task_type: str
    primary: Optional[ModelOut]
    fallback: Optional[ModelOut]
    note: str


# ─── 用量 ───
class CallRecordRequest(BaseModel):
    model_id: uuid.UUID
    task_type: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    ok: bool = True
    error_message: Optional[str] = None


class UsageStats(BaseModel):
    total_calls: int = 0
    total_tokens: int = 0
    total_cost: Decimal = Decimal("0")
    by_model: dict[str, dict] = {}
    by_user: dict[str, dict] = {}


# ─── 对外模型列表 ───
class PublicModel(BaseModel):
    model_name: str
    display_name: str
    provider: str
    task_types: list[Any]
    description: Optional[str]
    cost_per_1k_tokens: Optional[Decimal]