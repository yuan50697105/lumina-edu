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
from app.schemas import (
    BatchImportIn,
    BatchImportRow,
    BatchResultOut,
    BatchToggleIn,
    BatchUpdateIn,
    SuccessResponse,
    UserOut,
    UserUpdate,
)
from app.security import hash_password

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


# ═══════════════════════════════════════════════════════════════════
# D-05 · 用户批量操作（管理员）
# ═══════════════════════════════════════════════════════════════════
@router.post("/batch/import", response_model=BatchResultOut, status_code=201,
             summary="批量导入用户（管理员 · ≤500）")
def batch_import_users(
    payload: BatchImportIn,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """批量导入：每行生成默认密码（或指定密码）的 hash，冲突邮箱/学号跳过并记录错误"""
    default_pwd = payload.default_password or "Lumina@2026"
    success = 0
    errors: list[dict] = []
    for row in payload.users:
        # 邮箱唯一
        existing_email = db.query(User.id).filter(User.email == row.email).first()
        if existing_email:
            errors.append({"email": row.email, "message": "邮箱已存在"})
            continue
        # 学号唯一（若提供）
        if row.student_id:
            existing_sid = db.query(User.id).filter(User.student_id == row.student_id).first()
            if existing_sid:
                errors.append({"email": row.email, "message": f"学号 {row.student_id} 已存在"})
                continue
        try:
            u = User(
                email=row.email,
                name=row.name,
                student_id=row.student_id,
                role=row.role,
                department=row.department,
                grade=row.grade,
                password_hash=hash_password(default_pwd),
            )
            db.add(u)
            success += 1
        except Exception as exc:
            errors.append({"email": row.email, "message": f"写入失败: {exc}"})
    db.commit()
    return BatchResultOut(
        total=len(payload.users),
        success=success,
        failed=len(errors),
        errors=errors,
    )


@router.post("/batch/update", response_model=BatchResultOut,
             summary="批量更新用户角色（管理员）")
def batch_update_users(
    payload: BatchUpdateIn,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """批量修改角色（不能把管理员降权为自己的依赖保护）"""
    if not payload.new_role:
        raise HTTPException(status_code=400, detail="至少指定一个更新字段（new_role）")
    success = 0
    errors: list[dict] = []
    for uid in payload.user_ids:
        u = db.get(User, uid)
        if not u:
            errors.append({"user_id": str(uid), "message": "用户不存在"})
            continue
        if u.role == "admin" and payload.new_role != "admin":
            errors.append({"user_id": str(uid), "message": "不允许直接降权管理员"})
            continue
        u.role = payload.new_role
        success += 1
    db.commit()
    return BatchResultOut(total=len(payload.user_ids), success=success,
                          failed=len(errors), errors=errors)


@router.post("/batch/toggle", response_model=BatchResultOut,
             summary="批量启用/禁用用户（管理员 · 注销会话）")
def batch_toggle_users(
    payload: BatchToggleIn,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """V1：通过清除 refresh token 实现禁用（sessions 表 CASCADE）。
    启用时仅允许登录时重新生成，无需额外状态字段。"""
    from app.models import Session as SessionModel
    success = 0
    errors: list[dict] = []
    for uid in payload.user_ids:
        u = db.get(User, uid)
        if not u:
            errors.append({"user_id": str(uid), "message": "用户不存在"})
            continue
        if payload.action == "disable":
            # 删除该用户所有 refresh session
            db.query(SessionModel).filter(SessionModel.user_id == uid).delete()
            success += 1
        else:
            # enable：V1 仅回显（下次登录正常生成）
            success += 1
    db.commit()
    return BatchResultOut(total=len(payload.user_ids), success=success,
                          failed=len(errors), errors=errors)