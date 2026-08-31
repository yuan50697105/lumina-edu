# ============================================
# Lumina 墨光 · 消息通知路由
# 只允许访问「我的」通知；已读状态由 is_read 标记
# ============================================
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.instrumentation import (
    EVENT_NOTIF_READ,
    EVENT_NOTIF_READ_ALL,
    EVENT_NOTIF_VIEW,
    Instrumentation,
)
from app.models import Notification, User
from app.schemas import NotificationOut, SuccessResponse, UnreadCountOut

router = APIRouter(prefix="/notifications", tags=["消息通知"])


def _owns(notification: Notification, user: User) -> bool:
    """是否属于当前用户"""
    return str(notification.user_id) == str(user.id)


def _get_mine(db: Session, user: User, notification_id: uuid.UUID) -> Notification:
    """取属于当前用户的单条通知（不存在/不属于 → 404）"""
    item = db.get(Notification, notification_id)
    if not item or not _owns(item, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")
    return item


@router.get("/my", response_model=list[NotificationOut], summary="我的通知列表")
def my_notifications(
    limit: int = 50,
    unread_only: bool = False,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按时间倒序返回我的通知（可选只看未读）"""
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    items = (
        query.order_by(Notification.created_at.desc()).limit(min(max(limit, 1), 100)).all()
    )
    Instrumentation(db, request, str(user.id)).track(
        EVENT_NOTIF_VIEW, unread_only=str(unread_only), count=str(len(items))
    )
    return [NotificationOut.model_validate(n) for n in items]


@router.get("/my/unread-count", response_model=UnreadCountOut, summary="未读通知数")
def my_unread_count(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """顶栏铃铛徽标轮询用；返回未读数"""
    count = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.is_read.is_(False))
        .count()
    )
    return UnreadCountOut(unread_count=count)


@router.post("/my/{notification_id}/read", response_model=SuccessResponse, summary="标记单条已读")
def mark_read(
    notification_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_mine(db, user, notification_id)
    if not item.is_read:
        item.is_read = True
        db.commit()
    Instrumentation(db, request, str(user.id)).track(
        EVENT_NOTIF_READ, notification_id=str(notification_id), type=item.type
    )
    return SuccessResponse()


@router.post("/my/read-all", response_model=SuccessResponse, summary="全部标记已读")
def mark_all_read(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.is_read.is_(False))
        .update({Notification.is_read: True}, synchronize_session=False)
    )
    db.commit()
    Instrumentation(db, request, str(user.id)).track(
        EVENT_NOTIF_READ_ALL, count=str(updated)
    )
    return SuccessResponse()