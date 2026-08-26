# ============================================
# Lumina 墨光 · 埋点收集服务 Pydantic Schemas
# ============================================
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── 事件上报（对齐 event_tracking 表）───
class EventIn(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=100)
    user_id: Optional[str] = Field(None, max_length=36, description="游客标识（登录用户由服务端 JWT 覆盖）")
    session_id: Optional[str] = Field(None, max_length=100)
    page_url: Optional[str] = Field(None, max_length=500)
    properties: Optional[dict] = None


class EventBatch(BaseModel):
    events: list[EventIn] = Field(..., min_length=1, max_length=100)


# ─── 统计查询 ───
class StatsOut(BaseModel):
    total: int = 0
    distinct_users: int = 0
    distinct_sessions: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None


class BreakdownRow(BaseModel):
    event_name: str
    count: int
    distinct_users: int


# ─── 通用 ───
class SuccessResponse(BaseModel):
    code: int = 0
    message: str = "success"