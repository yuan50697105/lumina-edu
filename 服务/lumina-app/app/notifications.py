# ============================================
# Lumina 墨光 · 消息通知写入工具（D-03）
# 各业务模块在关键动作后调用 notify() 入栏；
# 只 add 不 commit，由调用方统一提交（与 Instrumentation.track 相配合）
# ============================================
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Notification


def notify(
    db: Session,
    user_id,
    type_: str,
    title: str,
    content: Optional[str] = None,
    ref_type: Optional[str] = None,
    ref_id=None,
) -> Notification:
    """给指定用户写入一条通知（未提交，随调用方事务一并 commit）

    Args:
        db: 数据库会话
        user_id: 接收者 user_id
        type_: 通知类别（welcome / live_call / assignment_graded / course_announcement / system）
        title: 通知标题
        content: 通知正文
        ref_type: 跳转引用类型（live_room / assignment / course / group）
        ref_id: 跳转引用 id
    """
    item = Notification(
        user_id=user_id,
        type=type_,
        title=title,
        content=content,
        ref_type=ref_type,
        ref_id=ref_id,
    )
    db.add(item)
    return item