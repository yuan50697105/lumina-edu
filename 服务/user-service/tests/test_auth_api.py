# ============================================
# Lumina 墨光 · 用户服务 认证接口集成测试
# 需要 PostgreSQL 已启动（docker-compose 提供）
# ============================================
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.main import app
from app.security import hash_password
from app.models import User

# 连接不上数据库则整组跳过
try:
    db = SessionLocal()
    db.execute(text("SELECT 1"))
    db.close()
    DB_READY = True
except Exception:
    DB_READY = False

pytestmark = pytest.mark.skipif(not DB_READY, reason="PostgreSQL 未就绪（docker-compose up -d postgres）")

TEST_USER = {
    "student_id": "20230001",
    "name": "测试学生",
    "email": "test-student@lumina.edu",
    "password": "Lumina@2026",
    "role": "student",
    "department": "计算机学院",
    "grade": "2023级",
}


@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    Base.metadata.create_all(bind=engine)
    yield
    # 清理测试数据
    db = SessionLocal()
    db.execute(text("DELETE FROM sessions; DELETE FROM event_tracking; DELETE FROM api_logs; DELETE FROM users WHERE email = :em"), {"em": TEST_USER["email"]})
    db.commit()
    db.close()


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def created_user():
    db = SessionLocal()
    user = db.query(User).filter(User.email == TEST_USER["email"]).first()
    if not user:
        user = User(
            student_id=TEST_USER["student_id"],
            name=TEST_USER["name"],
            email=TEST_USER["email"],
            password_hash=hash_password(TEST_USER["password"]),
            role=TEST_USER["role"],
            department=TEST_USER["department"],
            grade=TEST_USER["grade"],
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user


class TestLogin:
    def test_login_success(self, client, created_user):
        resp = client.post("/api/v1/auth/login", json={
            "username": TEST_USER["email"],
            "password": TEST_USER["password"],
            "device": "web",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "Bearer"
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["expires_in"] == 900
        assert body["user"]["email"] == TEST_USER["email"]

    def test_login_with_student_id(self, client, created_user):
        resp = client.post("/api/v1/auth/login", json={
            "username": TEST_USER["student_id"],
            "password": TEST_USER["password"],
            "device": "mobile",
        })
        assert resp.status_code == 200

    def test_login_wrong_password(self, client, created_user):
        resp = client.post("/api/v1/auth/login", json={
            "username": TEST_USER["email"],
            "password": "wrong-password",
            "device": "web",
        })
        assert resp.status_code == 401
        assert resp.json()["code"] == "AUTH_BAD_CREDENTIALS"


class TestAuthFlow:
    def test_me_requires_token(self, client):
        resp = client.get("/api/v1/users/me")
        assert resp.status_code == 401

    def test_login_me_refresh_logout_flow(self, client, created_user):
        # 登录
        login = client.post("/api/v1/auth/login", json={
            "username": TEST_USER["email"],
            "password": TEST_USER["password"],
            "device": "web",
        })
        tokens = login.json()

        # 访问 /users/me
        me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert me.status_code == 200
        assert me.json()["email"] == TEST_USER["email"]

        # 刷新令牌
        refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert refresh.status_code == 200
        new_access = refresh.json()["access_token"]

        # 新令牌可用
        me2 = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {new_access}"})
        assert me2.status_code == 200

        # 登出
        logout = client.post(
            "/api/v1/auth/logout",
            headers={
                "Authorization": f"Bearer {new_access}",
                "session_id": refresh.json().get("user") and refresh.json().get("user", {}).get("id", ""),
            },
        )
        assert logout.status_code in (200, 204)

    def test_profile_update(self, client, created_user):
        login = client.post("/api/v1/auth/login", json={
            "username": TEST_USER["email"],
            "password": TEST_USER["password"],
            "device": "web",
        })
        token = login.json()["access_token"]
        resp = client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "测试学生·新", "bio": "热爱学习"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "测试学生·新"


class TestMonitoring:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_login_event_recorded(self, client, created_user):
        """登录后 event_tracking 应新增 user.login 记录"""
        client.post("/api/v1/auth/login", json={
            "username": TEST_USER["email"],
            "password": TEST_USER["password"],
            "device": "web",
        })
        db = SessionLocal()
        row = db.execute(
            text("SELECT event_name FROM event_tracking WHERE event_name = 'user.login' ORDER BY id DESC LIMIT 1")
        ).first()
        db.close()
        assert row is not None

    def test_api_log_recorded(self, client):
        """任意请求后 api_logs 应有记录"""
        client.get("/health")
        db = SessionLocal()
        count = db.execute(text("SELECT count(*) FROM api_logs")).scalar()
        db.close()
        assert count > 0