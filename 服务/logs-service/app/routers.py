# ============================================
# Lumina 墨光 · 基础日志服务路由
# GET /logs/query 日志检索 · GET /logs/summary 统计概览
# 面向 admin，只读 api_logs
# ============================================
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from .database import get_db
from .dependencies import AuthUser, require_role
from .models import APILog
from .queries import build_filters, clamp_limit, clamp_offset
from .schemas import LogQueryOut, LogRecordOut, LogSummaryOut, TopPath

logger = logging.getLogger("lumina.logs")

router = APIRouter(tags=["基础日志系统"])

# 错误状态码认定：≥400
_ERROR_COND = case((APILog.status_code >= 400, 1), else_=0)


def _record(row) -> LogRecordOut:
    return LogRecordOut(
        id=row.id, method=row.method, path=row.path,
        status_code=row.status_code, duration_ms=row.duration_ms,
        user_id=str(row.user_id) if row.user_id else None,
        request_id=row.request_id, error_message=row.error_message,
        created_at=row.created_at,
    )


@router.get("/logs/query", response_model=LogQueryOut, summary="日志检索（管理员）")
def query_logs(
    admin: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=365, description="回溯天数"),
    method: str | None = Query(None, description="HTTP 方法，如 GET"),
    path_contains: str | None = Query(None, description="路径包含关键字"),
    status: int | None = Query(None, ge=100, le=599, description="状态码精确过滤"),
    request_id: str | None = Query(None, description="请求链路 ID"),
    user_id: str | None = Query(None, description="用户 UUID"),
    limit: int | None = Query(None, description="每页条数（默认 50，上限 200）"),
    offset: int | None = Query(None, description="偏移量"),
):
    """按条件检索 API 日志，按时间倒序分页返回"""
    limit = clamp_limit(limit)
    offset = clamp_offset(offset)
    flt = build_filters(days, method=method, path_contains=path_contains,
                        status=status, request_id=request_id, user_id=user_id)

    base = db.query(APILog).filter(*flt.conditions)
    total = base.count()
    rows = (
        base.order_by(APILog.created_at.desc(), APILog.id.desc())
        .offset(offset).limit(limit).all()
    )
    return LogQueryOut(
        records=[_record(r) for r in rows],
        total=total, offset=offset, limit=limit,
    )


@router.get("/logs/summary", response_model=LogSummaryOut, summary="日志统计概览（管理员）")
def logs_summary(
    admin: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=365, description="回溯天数"),
    method: str | None = Query(None),
    path_contains: str | None = Query(None),
    status: int | None = Query(None, ge=100, le=599),
):
    """总体指标 + TOP 路径（调用量/错误/平均耗时）"""
    flt = build_filters(days, method=method, path_contains=path_contains, status=status)

    agg = (
        db.query(
            func.count(APILog.id),
            func.sum(_ERROR_COND),
            func.avg(APILog.duration_ms),
            func.max(APILog.duration_ms),
        )
        .filter(*flt.conditions)
        .one()
    )
    total = agg[0] or 0
    errors = int(agg[1] or 0)
    avg_ms = float(agg[2] or 0)
    max_ms = int(agg[3]) if agg[3] is not None else None

    top = (
        db.query(
            APILog.path,
            func.count(APILog.id).label("calls"),
            func.sum(_ERROR_COND).label("errs"),
            func.avg(APILog.duration_ms).label("avg"),
        )
        .filter(*flt.conditions)
        .group_by(APILog.path)
        .order_by(func.count(APILog.id).desc())
        .limit(10)
        .all()
    )
    top_paths = [
        TopPath(path=r[0], calls=r[1], errors=int(r[2] or 0), avg_duration_ms=round(float(r[3] or 0), 1))
        for r in top
    ]
    return LogSummaryOut(
        total=total, errors=errors,
        error_rate=round(errors / total, 4) if total else 0.0,
        avg_duration_ms=round(avg_ms, 1), max_duration_ms=max_ms,
        top_paths=top_paths,
    )