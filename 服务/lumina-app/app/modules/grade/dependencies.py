# ============================================
# Lumina 墨光 · 成绩服务认证依赖
# 共享 JWT + 共享 users 表
# ============================================
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import UserBrief
from app.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserBrief:
    """JWT 认证依赖"""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"code": "AUTH_TOKEN_MISSING", "detail": "缺少访问令牌"},
                            headers={"WWW-Authenticate": "Bearer"})
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"code": "AUTH_TOKEN_INVALID", "detail": "访问令牌无效或已过期"},
                            headers={"WWW-Authenticate": "Bearer"})
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
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"需要角色: {', '.join(roles)}")
        return user
    return checker