# ============================================
# Lumina 墨光 · AI 对话服务接口集成测试
# 需要 PostgreSQL + ai-gateway 在线（阶段三验证）
# ============================================
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import text

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.main import app

try:
    db = SessionLocal()
    db.execute(text("SELECT 1"))
    db.close()
    DB_READY = True
except Exception:
    DB_READY = False

pytestmark = pytest.mark.skipif(not DB_READY, reason="PostgreSQL 未就绪")

TAG = uuid.uuid4().hex[:8]


def make_token(user_id: str, role: str = "student") -> str:
    return jwt.encode(
        {"sub": str(user_id), "role": role, "type": "access",
         "exp": datetime.now(timezone.utc) + timedelta(minutes=15)},
        settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
    )


@pytest.fixture(scope="module", autouse=True)
def setup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    uid = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO users (id, student_id, name, email, password_hash, role)
        VALUES (:uid, 'CHT', '对话测试', :mail, 'x', 'student')
        ON CONFLICT (email) DO NOTHING
    """), {"uid": uid, "mail": f"chat-stu-{TAG}@lumina.edu"})
    db.commit()
    db.close()

    yield uid

    db = SessionLocal()
    db.execute(text("""
        DELETE FROM ai_messages WHERE conversation_id IN
            (SELECT id FROM ai_conversations WHERE user_id = :uid);
        DELETE FROM ai_conversations WHERE user_id = :uid;
        DELETE FROM event_tracking WHERE user_id = :uid;
        DELETE FROM api_logs WHERE user_id = :uid;
        DELETE FROM users WHERE id = :uid
    """), {"uid": uuid.UUID(uid)})
    db.commit()
    db.close()


@pytest.fixture()
def ctx():
    return TestClient(app)


class TestChatPost:
    def test_auth_required(self, ctx):
        r = ctx.post("/api/v1/ai/chat", json={"message": "你好"})
        assert r.status_code == 401

    def test_no_model_available(self, ctx, setup):
        """网关未配置模型 → 智能路由 400（可离线验证错误路径）"""
        r = ctx.post(
            "/api/v1/ai/chat",
            headers={"Authorization": f"Bearer {make_token(setup)}"},
            json={"message": "函数可导吗"},
        )
        # 网关不可达/无模型都归为 400，绝不应 500
        assert r.status_code in (400, 502), r.text

    def test_conversation_history_empty(self, ctx, setup):
        r = ctx.get(
            "/api/v1/ai/conversations",
            headers={"Authorization": f"Bearer {make_token(setup)}"},
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestConversationCRUD:
    def test_get_missing_conversation(self, ctx, setup):
        r = ctx.get(
            f"/api/v1/ai/conversations/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {make_token(setup)}"},
        )
        assert r.status_code == 404

    def test_delete_missing_conversation(self, ctx, setup):
        r = ctx.delete(
            f"/api/v1/ai/conversations/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {make_token(setup)}"},
        )
        assert r.status_code == 404