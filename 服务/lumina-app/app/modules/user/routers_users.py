# ============================================
# Lumina 墨光 · 用户路由
# /users/me /users/{id} /users
# ============================================
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.instrumentation import EVENT_PROFILE_UPDATE, EVENT_USER_VIEW, Instrumentation
from app.models import User
from app.schemas import SuccessResponse, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/me", response_model=UserOut, summary="获取当前用户资料")
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut, summary="更新当前用户资料")
def update_me(
    payload: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新昵称 / 头像 / 简介"""
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return current_user

    for key, value in data.items():
        setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)

    Instrumentation(db, request, str(current_user.id)).track(
        EVENT_PROFILE_UPDATE, fields=list(data.keys())
    )
    return current_user


@router.get("/{user_id}", response_model=UserOut, summary="获取用户公开资料")
def get_user(
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取其他用户资料（学生可见，用于协作）"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    Instrumentation(db, request, str(current_user.id)).track(EVENT_USER_VIEW, target_user_id=str(user_id))
    return user


# ─── 管理端：仅 admin ───
@router.get("", response_model=list[UserOut], summary="用户列表（管理员）")
def list_users(
    request: Request,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """管理员分页获取用户列表"""
    users = db.query(User).order_by(User.created_at.desc()).limit(limit).offset(offset).all()
    return users


@router.delete("/{user_id}", response_model=SuccessResponse, summary="删除用户（管理员）")
def delete_user(
    user_id: uuid.UUID,
    request: Request,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """管理员删除用户"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    db.delete(user)
    db.commit()
    return SuccessResponse()