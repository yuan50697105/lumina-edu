# ============================================
# Lumina 墨光 · 基础日志服务 Pydantic Schemas
# ============================================
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ─── 日志查询 ───
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


class LogQueryOut(BaseModel):
    records: list[LogRecordOut]
    total: int
    offset: int
    limit: int


class TopPath(BaseModel):
    path: str
    calls: int
    errors: int
    avg_duration_ms: float


class LogSummaryOut(BaseModel):
    total: int
    errors: int
    error_rate: float
    avg_duration_ms: float
    max_duration_ms: Optional[int]
    top_paths: list[TopPath]