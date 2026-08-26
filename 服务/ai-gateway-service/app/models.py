# ============================================
# Lumina 墨光 · AI 网关数据模型
# ai_providers / ai_models / ai_call_logs
# ============================================
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey,
    Integer, JSON, Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AIProvider(Base):
    """模型供应商（API Key 不入库，存 env）"""
    __tablename__ = "ai_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(30), unique=True, nullable=False)     # qwen / glm / spark / doubao
    display_name = Column(String(50), nullable=False)
    description = Column(String(200), nullable=True)
    domain = Column(String(200), nullable=True)                # 供应商域名标识
    enabled = Column(Boolean, default=True)                    # 是否启用整家供应商
    monthly_quota = Column(Numeric(12, 2), default=0)          # 月度预算（元），0=不限
    used_quota = Column(Numeric(12, 2), default=0)             # 已用额度（元）
    created_at = Column(DateTime(timezone=True), default=_now)

    models = relationship("AIModel", back_populates="provider")


class AIModel(Base):
    """模型单"""
    __tablename__ = "ai_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("ai_providers.id"), nullable=False)
    model_name = Column(String(50), unique=True, nullable=False)   # qwen-max
    display_name = Column(String(50), nullable=False)              # 通义千问 Max
    task_types = Column(JSON, default=list)                        # ["chat","grade","generate","vl","speech"]
    description = Column(String(200), nullable=True)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=10)                         # 路由优先级（数值小优先）
    cost_per_1k_tokens = Column(Numeric(8, 4), default=0)          # 单价（元/千token）
    max_tokens = Column(Integer, default=4096)
    openai_compatible = Column(Boolean, default=True)              # 是否兼容 OpenAI SDK 格式
    created_at = Column(DateTime(timezone=True), default=_now)

    provider = relationship("AIProvider", back_populates="models")


class AICallLog(Base):
    """AI 调用用量日志"""
    __tablename__ = "ai_call_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey("ai_models.id"), nullable=False)
    model_name = Column(String(50), nullable=False)
    task_type = Column(String(20), nullable=False)           # chat/grade/generate/vl/speech
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    cost = Column(Numeric(10, 4), default=0)
    ok = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)


# ─── 监控共享表 ───
class APILog(Base):
    """API 访问日志"""
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
    """用户行为事件"""
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