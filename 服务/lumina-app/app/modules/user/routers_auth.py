# ============================================
# Lumina 墨光 · 认证路由
# /auth/login /auth/refresh /auth/logout /auth/password
# ============================================
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import create_session, get_current_user
from app.instrumentation import (
    EVENT_LOGIN,
    EVENT_LOGIN_FAIL,
    EVENT_LOGOUT,
    EVENT_PASSWORD_CHANGE,
    EVENT_REGISTER,
    EVENT_TOKEN_REFRESH,
    Instrumentation,
)
from app.models import Session as SessionModel
from app.models import User
from app.notifications import notify
from app.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    SuccessResponse,
    TokenResponse,
    UserOut,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=TokenResponse, status_code=201, summary="注册（学生/教师自助开户）")
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """学生/教师自助注册并自动登录；管理员角色禁止自助开通"""
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已被注册")

    student_id = payload.student_id.strip() if payload.student_id else None
    if student_id:
        if db.query(User).filter(User.student_id == student_id).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该学号/工号已被使用")

    user = User(
        name=payload.name.strip(),
        email=email,
        student_id=student_id,
        password_hash=hash_password(payload.password),
        role=payload.role,
        department=payload.department,
        grade=payload.grade,
    )
    db.add(user)
    db.flush()  # 生成 user.id 供欢迎通知引用

    # 最后登录时间 + 欢迎通知
    from app.models import _now
    user.last_login_at = _now()
    notify(
        db,
        user.id,
        "welcome",
        "欢迎加入 Lumina 墨光 🎉",
        content="完成选课后即可加入直播课堂与协作小组；课程公告与批阅结果也会出现在这里。",
        ref_type="course",
    )

    # 自动登录：建会话（create_session 内 commit 将用户/通知/会话一并落库）
    session = create_session(
        db,
        str(user.id),
        create_refresh_token(str(user.id)),
        device=payload.device,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    Instrumentation(db, request, str(user.id)).track(
        EVENT_REGISTER,
        role=payload.role,
        session_id=str(session.id),
    )
    return _build_token_response(user)


def _build_token_response(user: User) -> TokenResponse:
    """生成双令牌响应"""
    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id))
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse, summary="登录")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """用户名密码登录，发放双令牌并记录会话"""
    user = db.query(User).filter(
        or_(User.student_id == payload.username, User.email == payload.username)
    ).first()

    if not user or not verify_password(payload.password, user.password_hash):
        # 登录失败埋点
        Instrumentation(db, request).track(
            EVENT_LOGIN_FAIL,
            username=payload.username,
            reason="invalid_credentials",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://api.lumina.edu/errors/unauthorized",
                "title": "Unauthorized",
                "code": "AUTH_BAD_CREDENTIALS",
                "detail": "用户名或密码错误",
            },
        )

    # 更新最后登录时间
    from app.models import _now
    user.last_login_at = _now()
    db.commit()

    # 建会话 + 登录埋点
    session = create_session(
        db,
        str(user.id),
        create_refresh_token(str(user.id)),
        device=payload.device,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    Instrumentation(db, request, str(user.id)).track(
        EVENT_LOGIN,
        device=payload.device,
        session_id=str(session.id),
    )

    resp = _build_token_response(user)
    return resp


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌")
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    """用刷新令牌换取新的双令牌"""
    parsed = decode_token(payload.refresh_token)
    if not parsed or parsed.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌")

    # 校验会话存在且未过期
    db_session = (
        db.query(SessionModel)
        .filter(SessionModel.refresh_token == payload.refresh_token)
        .first()
    )
    if not db_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="会话不存在，请重新登录")

    user = db.get(User, db_session.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

    # 刷新后删除旧会话，建立新会话
    db.delete(db_session)
    session = create_session(
        db,
        str(user.id),
        create_refresh_token(str(user.id)),
        device=db_session.device,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    Instrumentation(db, request, str(user.id)).track(
        EVENT_TOKEN_REFRESH,
        session_id=str(session.id),
    )

    resp = _build_token_response(user)
    db.commit()
    return resp


@router.post("/logout", response_model=SuccessResponse, summary="退出登录")
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除当前会话并记录退出埋点"""
    session_id = request.headers.get("session_id")
    if session_id:
        try:
            db.query(SessionModel).filter(
                SessionModel.id == uuid.UUID(session_id)
            ).delete()
        except ValueError:
            pass
    # 若未携带 session_id，则删除当前用户全部会话
    else:
        db.query(SessionModel).filter(SessionModel.user_id == current_user.id).delete()
    db.commit()

    Instrumentation(db, request, str(current_user.id)).track(EVENT_LOGOUT)
    return SuccessResponse()


@router.post("/password", response_model=SuccessResponse, summary="修改密码")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改当前用户密码"""
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误")

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()

    # 修改密码后使所有会话失效
    db.query(SessionModel).filter(SessionModel.user_id == current_user.id).delete()
    db.commit()

    Instrumentation(db, request, str(current_user.id)).track(EVENT_PASSWORD_CHANGE)
    return SuccessResponse()