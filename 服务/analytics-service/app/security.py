# ============================================
# Lumina 墨光 · 埋点收集服务安全模块（JWT 校验）
# 仅用于 admin 统计端点鉴权；事件上报接受游客
# ============================================
from typing import Optional

from jose import JWTError, jwt

from .config import settings


def decode_token(token: str) -> Optional[dict]:
    """解析 Access Token，无效返回 None"""
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None