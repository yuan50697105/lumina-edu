# ============================================
# Lumina 墨光 · 系统设置路由（V1.1 · D-07/D-08）
# KV 结构系统配置（category 分组）
# 权限：admin 全读写；teacher/student 只读部分（预留）
# ============================================
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, get_current_user, require_role
from app.models import AuditLog, SystemSetting, User
from app.schemas import (
    SettingBatchIn,
    SettingCategoryOut,
    SettingOut,
    SettingUpdate,
    SuccessResponse,
)

router = APIRouter(prefix="/admin/settings", tags=["系统设置（D-07/D-08）"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_admin(user: AuthUser) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可访问")
    return user


def _to_out(setting: SystemSetting, updater_name: str | None = None) -> SettingOut:
    return SettingOut(
        key=setting.key,
        value=setting.value,
        category=setting.category,
        description=setting.description,
        updated_by=setting.updated_by,
        updater_name=updater_name,
        updated_at=setting.updated_at,
    )


@router.get("", response_model=list[SettingOut], summary="设置列表（管理员）")
def list_settings(
    category: str | None = Query(None),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    q = db.query(SystemSetting)
    if category:
        q = q.filter(SystemSetting.category == category)
    settings = q.order_by(SystemSetting.category, SystemSetting.key).all()
    out = []
    for s in settings:
        updater = db.get(User, s.updated_by) if s.updated_by else None
        out.append(_to_out(s, updater.name if updater else None))
    return out


@router.get("/categories", response_model=list[SettingCategoryOut],
            summary="设置分类枚举（管理员）")
def list_categories(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    rows = (
        db.query(
            SystemSetting.category,
            func.count(SystemSetting.id),
        )
        .group_by(SystemSetting.category)
        .all()
    )
    out = []
    for cat, cnt in rows:
        keys = [
            r[0] for r in db.query(SystemSetting.key)
            .filter(SystemSetting.category == cat).all()
        ]
        out.append(SettingCategoryOut(category=cat, count=cnt, keys=keys))
    return out


@router.get("/{key}", response_model=SettingOut, summary="获取单个设置（管理员）")
def get_setting(
    key: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    s = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not s:
        raise HTTPException(status_code=404, detail="设置项不存在")
    updater = db.get(User, s.updated_by) if s.updated_by else None
    return _to_out(s, updater.name if updater else None)


@router.put("/{key}", response_model=SettingOut, summary="更新单个设置（管理员）")
def update_setting(
    key: str,
    payload: SettingUpdate,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    admin = _require_admin(user)
    s = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not s:
        # 新建
        s = SystemSetting(
            key=key,
            value=payload.value,
            description=payload.description,
            updated_by=admin.id,
        )
        db.add(s)
        action = "setting.create"
    else:
        s.value = payload.value
        if payload.description is not None:
            s.description = payload.description
        s.updated_by = admin.id
        action = "setting.update"
    db.add(AuditLog(
        actor_id=admin.id,
        action=action,
        target_type="setting",
        details={"key": key, "value": str(payload.value)[:200]},
    ))
    db.commit()
    db.refresh(s)
    return _to_out(s, admin.name)


@router.post("/batch", response_model=list[SettingOut], summary="批量更新设置（管理员）")
def batch_update_settings(
    payload: SettingBatchIn,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    admin = _require_admin(user)
    updated = []
    for item in payload.items:
        s = db.query(SystemSetting).filter(SystemSetting.key == item.key).first()
        if not s:
            s = SystemSetting(key=item.key, value=item.value, updated_by=admin.id)
            db.add(s)
            action = "setting.create"
        else:
            s.value = item.value
            s.updated_by = admin.id
            action = "setting.update"
        db.add(AuditLog(
            actor_id=admin.id,
            action=action,
            target_type="setting",
            details={"key": item.key},
        ))
        updated.append(s)
    db.commit()
    for s in updated:
        db.refresh(s)
    return [_to_out(s, admin.name) for s in updated]
