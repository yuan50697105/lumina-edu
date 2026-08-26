# ============================================
# Lumina 墨光 · AI 对话服务 Pydantic Schemas
# ============================================
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── 对话请求 ───
class ChatContext(BaseModel):
    course_id: Optional[uuid.UUID] = None
    chapter_id: Optional[uuid.UUID] = None


class ChatRequest(BaseModel):
    conversation_id: Optional[uuid.UUID] = None   # 传则续聊该会话
    message: str = Field(..., min_length=1, max_length=8000)
    context: Optional[ChatContext] = None         # 课程/章节上下文
    attachments: Optional[list[dict]] = None      # 图片/音频附件占位
    model_name: Optional[str] = Field(None, max_length=50)  # 指定模型，缺省走智能路由
    max_tokens: int = Field(2048, ge=64, le=16384)
    temperature: Optional[float] = Field(None, ge=0, le=2)


# ─── 对话历史 ───
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
class SuccessResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[dict] = None