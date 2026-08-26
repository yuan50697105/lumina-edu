# ============================================
# Lumina 墨光 · AI 批阅服务认证依赖
# 共享 JWT + 共享 users 表
# ============================================
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


class AuthUser:
    """认证用户"""
    def __init__(self, id: uuid.UUID, role: str):
        self.id = id
        self.role = role


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthUser:
    """JWT 认证依赖：校验令牌并确认用户存在"""
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

    user_id = uuid.UUID(payload["sub"])
    row = db.execute(
        text("SELECT role FROM users WHERE id = :uid"), {"uid": str(user_id)}
    ).first()
    if not row:
        raise HTTPException(status_code=401, detail="用户不存在")
    return AuthUser(id=user_id, role=row[0])


def require_role(*roles: str):
    """角色权限依赖"""
    def checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"需要角色: {', '.join(roles)}")
        return user
    return checker