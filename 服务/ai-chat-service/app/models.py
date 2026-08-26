# ============================================
# Lumina 墨光 · AI 对话服务数据模型
# ai_conversations / ai_messages / 共享埋点表
# ============================================
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Column, DateTime, ForeignKey, Integer, JSON, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AIConversation(Base):
    """AI 对话会话（对齐 init.sql / lumina-database 文档）"""
    __tablename__ = "ai_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)   # 分片键
    title = Column(String(200), nullable=True)                          # 自动生成（首条消息截断）
    model = Column(String(50), nullable=True)                           # 实际使用模型 qwen-max
    context_course_id = Column(UUID(as_uuid=True), nullable=True)       # 关联课程
    context_chapter_id = Column(UUID(as_uuid=True), nullable=True)      # 关联章节
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    messages = relationship("AIMessage", back_populates="conversation")


class AIMessage(Base):
    """AI 对话消息"""
    __tablename__ = "ai_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True),
                             ForeignKey("ai_conversations.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    role = Column(String(20), nullable=False)          # user / assistant / system
    content = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True)          # 图片/音频附件
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_now)

    conversation = relationship("AIConversation", back_populates="messages")


# ─── 监控共享表 ───
class APILog(Base):
    """API 访问日志（跨服务共享表 api_logs）"""
    __tablename__ = "api_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    status_code = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    request_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)


class EventTracking(Base):
    """用户行为事件（跨服务共享表 event_tracking）"""
    __tablename__ = "event_tracking"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_name = Column(String(100), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    session_id = Column(String(100), nullable=True)
    course_id = Column(UUID(as_uuid=True), nullable=True)
    properties = Column(JSON, nullable=True)
    page_url = Column(String(500), nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)