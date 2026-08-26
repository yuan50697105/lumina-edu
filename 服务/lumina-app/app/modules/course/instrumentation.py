# ============================================
# Lumina 墨光 · 课程服务监控埋点
# 与 user-service 相同的轻量方案：写入 PostgreSQL
# event_tracking / api_logs 表为共享表
# ============================================
import json
import logging
import time
import uuid
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from . import models

logger = logging.getLogger("lumina.course-service")

# 课程事件名称常量
EVENT_COURSE_VIEW = "course.view"
EVENT_COURSE_CREATED = "course.created"
EVENT_COURSE_UPDATED = "course.updated"
EVENT_COURSE_ENROLL = "course.enroll"
EVENT_COURSE_DROP = "course.drop"
EVENT_CHAPTER_VIEW = "chapter.view"
EVENT_CHAPTER_CREATED = "chapter.created"
EVENT_ANNOUNCEMENT_CREATED = "announcement.created"


class Instrumentation:
    """埋点记录器（与 user-service 同构，直接复用共享表）"""

    def __init__(self, db: Session, request: Request = None, user_id: str = None):
        self.db = db
        self.request = request
        self.user_id = user_id
        self.request_id = str(uuid.uuid4()) if request else None

    # ─── 业务事件埋点 ───
    def track(self, event_name: str, **properties: Any) -> None:
        """记录业务事件到 event_tracking 表"""
        course_id = properties.pop("course_id", None)
        session_id = properties.pop("session_id", None)
        try:
            event = models.EventTracking(
                event_name=event_name,
                user_id=properties.pop("user_id", self.user_id),
                session_id=session_id,
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

    # ─── API 日志埋点 ───
    def log_api(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: int,
        error_message: Optional[str] = None,
    ) -> None:
        """记录 API 请求日志到 api_logs 表"""
        try:
            log = models.APILog(
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                user_id=self.user_id,
                request_id=self.request_id,
                error_message=error_message,
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.warning(f"API 日志写入失败: {e}")

    # ─── 请求辅助 ───
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


# ─── 计时上下文管理器 ───
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