# ============================================
# Lumina 墨光 · 基础日志服务 查询构建
# 纯函数，便于单元测试
# ============================================
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import ColumnElement

from app.models import APILog


def clamp_limit(limit: int | None, default: int = 50, max_limit: int = 200) -> int:
    """limit 参数钳制：默认 50，上限 200"""
    if limit is None:
        return default
    return max(1, min(int(limit), max_limit))


def clamp_offset(offset: int | None) -> int:
    """offset 参数钳制：非负"""
    if not offset:
        return 0
    return max(0, int(offset))


@dataclass
class LogFilters:
    """日志查询过滤条件"""
    since: datetime
    conditions: list


def parse_user_id(value: str | None) -> uuid.UUID | None:
    """解析 user_id 过滤参数；非法返回 None（等价于不按用户过滤）"""
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def build_filters(
    days: int,
    method: str | None = None,
    path_contains: str | None = None,
    status: int | None = None,
    request_id: str | None = None,
    user_id: str | None = None,
) -> LogFilters:
    """构建 SQLAlchemy 过滤条件列表"""
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(int(days), 365)))
    conds: list[ColumnElement] = [APILog.created_at >= since]
    if method:
        conds.append(APILog.method == method.upper().strip())
    if path_contains:
        conds.append(APILog.path.contains(path_contains.strip()))
    if status is not None:
        conds.append(APILog.status_code == status)
    if request_id:
        conds.append(APILog.request_id == request_id.strip())
    uid = parse_user_id(user_id)
    if uid is not None:
        conds.append(APILog.user_id == uid)
    return LogFilters(since=since, conditions=conds)