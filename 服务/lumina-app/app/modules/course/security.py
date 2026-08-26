# ============================================
# Lumina 墨光 · 课程服务安全模块（JWT 校验）
# 跨服务共享 JWT_SECRET_KEY，仅需解码验证
# ============================================
from typing import Optional

from jose import JWTError, jwt

from app.config import settings


def decode_token(token: str) -> Optional[dict]:
    """解析 Access Token，无效返回 None"""
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None