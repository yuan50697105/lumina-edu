# ============================================
# Lumina 墨光 · 课程服务认证依赖
# 轻量方案：共享数据库，直接查 users 表验证当前用户
# ============================================
import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import UserBrief
from .security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserBrief:
    """JWT 认证依赖：解析令牌并从共享 users 表取当前用户"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://api.lumina.edu/errors/unauthorized",
                "title": "Unauthorized",
                "code": "AUTH_TOKEN_MISSING",
                "detail": "缺少访问令牌",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://api.lumina.edu/errors/unauthorized",
                "title": "Unauthorized",
                "code": "AUTH_TOKEN_INVALID",
                "detail": "访问令牌无效或已过期",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="令牌类型错误")

    user = db.get(UserBrief, uuid.UUID(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user


def require_role(*roles: str):
    """角色权限依赖"""
    def checker(user: UserBrief = Depends(get_current_user)) -> UserBrief:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "type": "https://api.lumina.edu/errors/forbidden",
                    "title": "Forbidden",
                    "code": "FORBIDDEN",
                    "detail": f"需要角色: {', '.join(roles)}",
                },
            )
        return user
    return checker