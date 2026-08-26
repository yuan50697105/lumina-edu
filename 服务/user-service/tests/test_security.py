# ============================================
# Lumina 墨光 · 用户服务 单元测试
# 纯逻辑测试：密码哈希 / JWT / Schema
# ============================================
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from jose import jwt as jose_jwt

from app.config import settings
from app.schemas import LoginRequest, UserCreate, UserOut
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


# ─── 密码哈希 ───
class TestPassword:
    def test_hash_and_verify(self):
        password = "Lumina@2026"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_verify_wrong_password(self):
        hashed = hash_password("correct-password")
        assert not verify_password("wrong-password", hashed)

    def test_hash_is_unique_salt(self):
        password = "same-password"
        assert hash_password(password) != hash_password(password)


# ─── JWT ───
class TestToken:
    def test_access_token_claims(self):
        token = create_access_token("user-123", "student")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "student"
        assert payload["type"] == "access"
        assert "jti" in payload and "exp" in payload

    def test_refresh_token_claims(self):
        token = create_refresh_token("user-123")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_access_lifetime_matches_config(self):
        token = create_access_token("u1", "student")
        payload = jose_jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        # 容差 30 秒
        assert expected - timedelta(seconds=30) <= exp <= expected + timedelta(seconds=30)

    def test_decode_expired_token_returns_none(self):
        from jose import jwt as j
        expired = j.encode(
            {"sub": "u1", "type": "access", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        assert decode_token(expired) is None

    def test_decode_tampered_token_returns_none(self):
        token = create_access_token("u1", "student")
        tampered = token[:-4] + "0000"
        assert decode_token(tampered) is None


# ─── Schema 校验 ───
class TestSchemas:
    def test_login_request_device_pattern(self):
        for ok in ["web", "mobile", "desktop"]:
            LoginRequest(username="20230001", password="x" * 8, device=ok)

        with pytest.raises(Exception):
            LoginRequest(username="u", password="x" * 8, device="watch")

    def test_user_create_password_min_length(self):
        with pytest.raises(Exception):
            UserCreate(name="测试", email="a@b.com", password="short")

    def test_user_out_from_attributes(self, tmp_path):
        class FakeUser:
            id = "00000000-0000-0000-0000-000000000001"
            student_id = "20230001"
            name = "张三"
            email = "zhangsan@lumina.edu"
            role = "student"
            department = "计算机学院"
            grade = "2023级"
            avatar_url = None
            bio = None
            created_at = datetime.now(timezone.utc)

        out = UserOut.model_validate(FakeUser())
        assert str(out.id) == "00000000-0000-0000-0000-000000000001"
        assert out.role == "student"