# ============================================
# Lumina 墨光 · 基础日志服务路由
# GET /logs/query 日志检索 · GET /logs/summary 统计概览
# 面向 admin，只读 api_logs
#
# D-07/D-08 扩展：审计日志 /admin/audit/*
# ============================================
import csv
import io
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, require_role
from app.models import APILog, AuditLog, User
from app.modules.logs.queries import build_filters, clamp_limit, clamp_offset
from app.schemas import AuditExportOut, AuditLogOut, LogQueryOut, LogRecordOut, LogSummaryOut, TopPath

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


# ═══════════════════════════════════════════════════════════════════
# D-07/D-08 · 审计日志
# ═══════════════════════════════════════════════════════════════════
audit_router = APIRouter(prefix="/admin/audit", tags=["审计日志（D-07/D-08）"])


def _require_admin(user: AuthUser) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可访问审计日志")
    return user


def _to_audit_out(row: AuditLog, actor_name: str | None = None) -> AuditLogOut:
    return AuditLogOut(
        id=row.id,
        actor_id=row.actor_id,
        actor_name=actor_name,
        action=row.action,
        target_type=row.target_type,
        target_id=row.target_id,
        details=row.details,
        ip_address=row.ip_address,
        status=row.status,
        archived=row.archived,
        created_at=row.created_at,
    )


@audit_router.get("", response_model=list[AuditLogOut], summary="审计日志列表（管理员）")
def list_audit_logs(
    action: str | None = Query(None, description="动作精确过滤，如 course.approve"),
    action_prefix: str | None = Query(None, description="动作前缀，如 course."),
    actor_id: str | None = Query(None, description="操作人 UUID"),
    target_type: str | None = Query(None, description="目标类型 user/course/setting/..."),
    target_id: str | None = Query(None, description="目标 ID"),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = db.query(AuditLog).filter(AuditLog.created_at >= since, AuditLog.archived == False)  # noqa: E712
    if action:
        q = q.filter(AuditLog.action == action)
    if action_prefix:
        q = q.filter(AuditLog.action.like(f"{action_prefix}%"))
    if actor_id:
        q = q.filter(AuditLog.actor_id == actor_id)
    if target_type:
        q = q.filter(AuditLog.target_type == target_type)
    if target_id:
        q = q.filter(AuditLog.target_id == target_id)
    rows = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    out = []
    for r in rows:
        actor = db.get(User, r.actor_id) if r.actor_id else None
        out.append(_to_audit_out(r, actor.name if actor else ("系统" if r.actor_id is None else None)))
    return out


@audit_router.get("/{log_id}", response_model=AuditLogOut, summary="审计日志详情（管理员）")
def get_audit_log(
    log_id: int,
    user: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    row = db.get(AuditLog, log_id)
    if not row:
        raise HTTPException(status_code=404, detail="审计记录不存在")
    actor = db.get(User, row.actor_id) if row.actor_id else None
    return _to_audit_out(row, actor.name if actor else None)


@audit_router.post("/export", summary="导出审计日志 CSV（管理员）")
def export_audit_logs(
    action_prefix: str | None = Query(None),
    target_type: str | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    user: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = db.query(AuditLog).filter(AuditLog.created_at >= since, AuditLog.archived == False)  # noqa: E712
    if action_prefix:
        q = q.filter(AuditLog.action.like(f"{action_prefix}%"))
    if target_type:
        q = q.filter(AuditLog.target_type == target_type)
    rows = q.order_by(AuditLog.created_at.desc()).limit(10000).all()

    # 写 CSV 到内存
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "actor_id", "actor_name", "action", "target_type",
                     "target_id", "details", "ip", "status", "created_at"])
    for r in rows:
        actor = db.get(User, r.actor_id) if r.actor_id else None
        writer.writerow([
            r.id,
            str(r.actor_id) if r.actor_id else "",
            actor.name if actor else "",
            r.action,
            r.target_type or "",
            str(r.target_id) if r.target_id else "",
            (str(r.details) if r.details else ""),
            r.ip_address or "",
            r.status,
            r.created_at.isoformat(),
        ])
    output.seek(0)
    filename = f"audit_logs_{since.strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@audit_router.post("/archive", response_model=dict, summary="归档旧审计日志（管理员）")
def archive_audit_logs(
    older_than_days: int = Query(180, ge=30, le=730),
    user: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """软归档：标记 archived=true，不物理删除。返回归档数量。"""
    _require_admin(user)
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    updated = (
        db.query(AuditLog)
        .filter(AuditLog.created_at < cutoff, AuditLog.archived == False)  # noqa: E712
        .update({AuditLog.archived: True}, synchronize_session=False)
    )
    db.commit()
    return {"archived_count": updated, "cutoff": cutoff.isoformat()}
