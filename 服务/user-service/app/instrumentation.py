# ============================================
# Lumina 墨光 · 监控埋点模块
# 轻量方案：埋点写入 PostgreSQL（api_logs / event_tracking）
# 无需额外监控组件
# ============================================
import json
import logging
import time
import uuid
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from . import models

logger = logging.getLogger("lumina.instrumentation")

# 事件名称常量
EVENT_LOGIN = "user.login"
EVENT_LOGIN_FAIL = "user.login_fail"
EVENT_REGISTER = "user.register"
EVENT_LOGOUT = "user.logout"
EVENT_TOKEN_REFRESH = "user.token_refresh"
EVENT_PASSWORD_CHANGE = "user.password_change"
EVENT_PROFILE_UPDATE = "user.profile_update"
EVENT_USER_VIEW = "user.view"


class Instrumentation:
    """埋点记录器"""

    def __init__(self, db: Session, request: Request = None, user_id: str = None):
        self.db = db
        self.request = request
        self.user_id = user_id
        self.request_id = str(uuid.uuid4()) if request else None

    # ─── 业务事件埋点 ───
    def track(self, event_name: str, **properties: Any) -> None:
        """记录业务事件到 event_tracking 表"""
        try:
            event = models.EventTracking(
                event_name=event_name,
                user_id=properties.pop("user_id", self.user_id),
                session_id=properties.pop("session_id", self._session_id()),
                course_id=properties.pop("course_id", None),
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

    def _session_id(self) -> Optional[str]:
        if self.request and "session_id" in self.request.headers:
            return self.request.headers["session_id"]
        return None

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