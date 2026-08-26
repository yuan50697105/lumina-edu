# ============================================
# Lumina 墨光 · 埋点收集服务路由
# POST /events 收集（游客/登录） · GET 统计（admin）
# ============================================
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, require_role
from app.models import EventTracking
from app.schemas import (
    BreakdownRow,
    EventBatch,
    EventIn,
    StatsOut,
    SuccessResponse,
)

logger = logging.getLogger("lumina.analytics")

router = APIRouter(tags=["埋点收集与统计"])


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()[:45]
    if request.client:
        return request.client.host
    return None


def _cell_uuid(value) -> uuid.UUID | None:
    """把可能的 UUID 字符串转 UUID；非法返回 None"""
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _resolve_user(request: Request, payload: EventIn) -> uuid.UUID | None:
    """身份解析：登录用户以 JWT 为准，游客用客户端 user_id（需合法 UUID）"""
    token = request.headers.get("authorization", "")
    if token.startswith("Bearer "):
        from app.security import decode_token
        data = decode_token(token[7:])
        if data and data.get("type") == "access" and data.get("sub"):
            try:
                return uuid.UUID(data["sub"])
            except ValueError:
                pass
    return _cell_uuid(payload.user_id)


def _to_row(request: Request, payload: EventIn, user_id: uuid.UUID | None) -> EventTracking:
    props = dict(payload.properties or {})
    course_id = _cell_uuid(props.get("course_id"))
    if course_id is not None:
        props.pop("course_id", None)   # 仅提升合法 UUID，非法保留在 properties
    return EventTracking(
        event_name=payload.event_name,
        user_id=user_id,
        session_id=payload.session_id,
        course_id=course_id,
        properties=props or None,
        page_url=payload.page_url,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )


# ─── 事件收集（游客可访问，fire-and-forget）───
@router.post("/events", response_model=SuccessResponse, status_code=202, summary="上报单条事件")
def ingest_event(
    payload: EventIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """上报埋点事件。登录用户由 JWT 覆盖身份；游客信任客户端 user_id。返回 202 不保证落库。"""
    user_id = _resolve_user(request, payload)
    db.add(_to_row(request, payload, user_id))
    db.commit()
    return SuccessResponse()


@router.post("/events/batch", response_model=SuccessResponse, status_code=202, summary="批量上报事件（≤100）")
def ingest_batch(
    payload: EventBatch,
    request: Request,
    db: Session = Depends(get_db),
):
    """批量落库，单事务。任一事件含 properties.course_id 会提升为列。"""
    rows = []
    for ev in payload.events:
        rows.append(_to_row(request, ev, _resolve_user(request, ev)))
    db.add_all(rows)
    db.commit()
    return SuccessResponse()


# ─── 统计查询（admin）───
@router.get("/events/stats", response_model=StatsOut, summary="事件统计概览（管理员）")
def stats(
    request: Request,
    admin: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    event_name: str | None = None,
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = db.query(
        func.count(EventTracking.id),
        func.count(func.distinct(EventTracking.user_id)),
        func.count(func.distinct(EventTracking.session_id)),
        func.min(EventTracking.created_at),
        func.max(EventTracking.created_at),
    ).filter(EventTracking.created_at >= since)
    if event_name:
        q = q.filter(EventTracking.event_name == event_name)
    (total, users, sessions, first_seen, last_seen) = q.first()
    return StatsOut(
        total=total or 0,
        distinct_users=users or 0,
        distinct_sessions=sessions or 0,
        first_seen=first_seen,
        last_seen=last_seen,
    )


@router.get("/events/breakdown", response_model=list[BreakdownRow], summary="事件类型分布（管理员）")
def breakdown(
    request: Request,
    admin: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(
            EventTracking.event_name,
            func.count(EventTracking.id).label("cnt"),
            func.count(func.distinct(EventTracking.user_id)).label("users"),
        )
        .filter(EventTracking.created_at >= since)
        .group_by(EventTracking.event_name)
        .order_by(func.count(EventTracking.id).desc())
        .limit(limit)
        .all()
    )
    return [BreakdownRow(event_name=r[0], count=r[1], distinct_users=r[2]) for r in rows]