# ============================================
# Lumina 墨光 · 作业服务监控埋点
# ============================================
import logging
import time
import uuid
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from . import models

logger = logging.getLogger("lumina.assignment-service")

# 事件名称常量
EVENT_ASSIGNMENT_VIEW = "assignment.view"
EVENT_ASSIGNMENT_CREATED = "assignment.created"
EVENT_ASSIGNMENT_UPDATED = "assignment.updated"
EVENT_ASSIGNMENT_SUBMITTED = "assignment.submitted"
EVENT_ASSIGNMENT_GRADED = "assignment.graded"


class Instrumentation:
    """埋点记录器（共享 event_tracking / api_logs 表）"""

    def __init__(self, db: Session, request: Request = None, user_id: str = None):
        self.db = db
        self.request = request
        self.user_id = user_id
        self.request_id = str(uuid.uuid4()) if request else None

    def track(self, event_name: str, **properties: Any) -> None:
        """记录业务事件"""
        course_id = properties.pop("course_id", None)
        try:
            event = models.EventTracking(
                event_name=event_name,
                user_id=properties.pop("user_id", self.user_id),
                session_id=properties.pop("session_id", None),
                course_id=course_id,
                properties=properties if properties else None,
                page_url=self._page_url(),
                user_agent=self._user_agent(),
                ip_address=self._ip(),
            )
            self.db.add(event)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.warning(f"埋点写入失败 [{event_name}]: {e}")

    def log_api(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: int,
        error_message: Optional[str] = None,
    ) -> None:
        """记录 API 请求日志"""
        try:
            self.db.add(models.APILog(
                method=method, path=path, status_code=status_code,
                duration_ms=duration_ms, user_id=self.user_id,
                request_id=self.request_id, error_message=error_message,
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