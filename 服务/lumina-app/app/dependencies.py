# ============================================
# Lumina 墨光 · 认证依赖
# ============================================
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Session as SessionModel
from app.models import User
from app.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


# AuthUser 类型别名 —— ai-gateway/ai-chat/ai-grade 使用轻量类型
AuthUser = User  # 兼容 ai 模块的类型提示（User 有 id + role 属性）


def get_request_id(request: Request) -> str:
    """获取或生成请求 ID（用于追踪）"""
    rid = request.headers.get("X-Request-ID")
    if not rid:
        rid = str(uuid.uuid4())
    return rid


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """JWT 认证依赖：从 Access Token 获取当前用户"""
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌类型错误")

    user = db.get(User, uuid.UUID(payload["sub"]))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

    return user


def require_role(*roles: str):
    """角色权限依赖"""
    def checker(user: User = Depends(get_current_user)) -> User:
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


def create_session(
    db: Session,
    user_id: str,
    refresh_token: str,
    device: str = "web",
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SessionModel:
    """创建登录会话"""
    from datetime import timedelta
    from app.config import settings
    from app.models import Session as SessionModel
    from app.security import decode_token

    payload = decode_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的刷新令牌")

    # 计算过期时间（来自 JWT exp 或默认 7 天）
    import datetime as dt
    expires_at = dt.datetime.fromtimestamp(payload["exp"], tz=dt.timezone.utc)

    session = SessionModel(
        user_id=user_id,
        refresh_token=refresh_token,
        device=device,
        ip_address=ip,
        user_agent=user_agent,
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session