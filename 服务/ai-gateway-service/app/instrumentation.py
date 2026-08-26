# ============================================
# Lumina 墨光 · AI 网关服务监控埋点
# ============================================
import logging
import time
import uuid
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from . import models

logger = logging.getLogger("lumina.ai-gateway")

# 事件名称常量
EVENT_AI_MODELS = "ai.models_view"
EVENT_AI_ROUTE = "ai.route"
EVENT_AI_USAGE = "ai.usage_view"
EVENT_AI_MODEL_REGISTERED = "ai.model_registered"
EVENT_AI_MODEL_UPDATED = "ai.model_updated"
EVENT_AI_CALL_RECORDED = "ai.call_recorded"


class Instrumentation:
    """埋点记录器"""

    def __init__(self, db: Session, request: Request = None, user_id: str = None):
        self.db = db
        self.request = request
        self.user_id = user_id
        self.request_id = str(uuid.uuid4()) if request else None

    def track(self, event_name: str, **properties: Any) -> None:
        course_id = properties.pop("course_id", None)
        try:
            self.db.add(models.EventTracking(
                event_name=event_name,
                user_id=properties.pop("user_id", self.user_id),
                session_id=properties.pop("session_id", None),
                course_id=course_id,
                properties=properties if properties else None,
                page_url=self._page_url(),
                user_agent=self._user_agent(),
                ip_address=self._ip(),
            ))
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.warning(f"埋点写入失败 [{event_name}]: {e}")

    def log_api(self, method: str, path: str, status_code: int, duration_ms: int,
                error_message: Optional[str] = None) -> None:
        try:
            self.db.add(models.APILog(
                method=method, path=path, status_code=status_code, duration_ms=duration_ms,
                user_id=self.user_id, request_id=self.request_id, error_message=error_message,
            ))
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.warning(f"API 日志写入失败: {e}")

    def _ip(self) -> Optional[str]:
        if not self.request:
            return None
        return self.request.client.host if self.request.client else None

    def _user_agent(self) -> Optional[str]:
        if not self.request:
            return None
        return self.request.headers.get("user-agent")

    def _page_url(self) -> Optional[str]:
        if not self.request:
            return None
        return str(self.request.url)


class Timer:
    """API 请求计时器"""

    def __init__(self):
        self.start = 0.0
        self.duration_ms = 0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.duration_ms = int((time.perf_counter() - self.start) * 1000)