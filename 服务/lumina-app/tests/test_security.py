# ============================================
# Lumina 墨光 · 安全模块单元测试
# JWT 令牌 + 密码哈希
# ============================================
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.config import settings
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


# bcrypt 哈希可用性检查
try:
    _test_hash = hash_password("test")
    BCRYPT_WORKS = True
except (ValueError, Exception):
    BCRYPT_WORKS = False


@pytest.mark.skipif(not BCRYPT_WORKS, reason="bcrypt 库不可用（缺少 C 扩展）")
class TestPasswordHash:
    """密码哈希测试"""

    def test_hash_and_verify(self):
        """哈希后能正确验证"""
        password = "SecurePass123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_wrong_password_fails(self):
        """错误密码验证失败"""
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_hash_not_plain(self):
        """哈希不等于明文"""
        password = "test123"
        hashed = hash_password(password)
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt 前缀

    def test_different_hashes(self):
        """同一密码产生不同哈希（盐值随机）"""
        password = "same_password"
        h1 = hash_password(password)
        h2 = hash_password(password)
        assert h1 != h2  # 不同盐值


class TestAccessToken:
    """访问令牌测试"""

    def test_create_and_decode(self):
        """创建后能正确解码"""
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id, "student")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["role"] == "student"
        assert payload["type"] == "access"

    def test_token_has_jti(self):
        """令牌包含唯一 ID"""
        token = create_access_token(str(uuid.uuid4()), "teacher")
        payload = decode_token(token)
        assert "jti" in payload
        assert len(payload["jti"]) == 36  # UUID 格式

    def test_token_expiry(self):
        """令牌过期时间正确"""
        token = create_access_token(str(uuid.uuid4()), "admin")
        payload = decode_token(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = exp - now
        # 应在 14-16 分钟内
        assert 14 * 60 < diff.total_seconds() < 16 * 60


class TestRefreshToken:
    """刷新令牌测试"""

    def test_create_and_decode(self):
        """创建后能正确解码"""
        user_id = str(uuid.uuid4())
        token = create_refresh_token(user_id)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"

    def test_refresh_expiry(self):
        """刷新令牌过期时间为 7 天"""
        token = create_refresh_token(str(uuid.uuid4()))
        payload = decode_token(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = exp - now
        # 应在 6-8 天内
        assert 6 * 86400 < diff.total_seconds() < 8 * 86400


class TestDecodeToken:
    """令牌解码测试"""

    def test_invalid_token_returns_none(self):
        """无效令牌返回 None"""
        assert decode_token("invalid.token.here") is None

    def test_expired_token_returns_none(self):
        """过期令牌返回 None"""
        # 创建一个已过期的令牌
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": str(uuid.uuid4()),
            "type": "access",
            "exp": expire,
            "jti": str(uuid.uuid4()),
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        assert decode_token(token) is None

    def test_wrong_secret_returns_none(self):
        """错误密钥返回 None"""
        payload = {
            "sub": str(uuid.uuid4()),
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "jti": str(uuid.uuid4()),
        }
        token = jwt.encode(payload, "wrong_secret", algorithm="HS256")
        assert decode_token(token) is None
