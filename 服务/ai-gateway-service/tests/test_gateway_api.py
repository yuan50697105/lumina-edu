# ============================================
# Lumina 墨光 · AI 网关 接口集成测试
# 需要 PostgreSQL 已启动（seed 模型池后验证）
# ============================================
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.main import app, seed_model_pool

try:
    db = SessionLocal()
    db.execute(text("SELECT 1"))
    db.close()
    DB_READY = True
except Exception:
    DB_READY = False

pytestmark = pytest.mark.skipif(not DB_READY, reason="PostgreSQL 未就绪")

from app.config import settings  # noqa: E402

TAG = uuid.uuid4().hex[:8]


def make_token(user_id: str, role: str) -> str:
    return jwt.encode(
        {"sub": str(user_id), "role": role, "type": "access",
         "exp": datetime.now(timezone.utc) + timedelta(minutes=15)},
        settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
    )


@pytest.fixture(scope="module", autouse=True)
def setup():
    Base.metadata.create_all(bind=engine)
    seed_model_pool()  # 幂等：表空才写入

    db = SessionLocal()
    admin_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO users (id, student_id, name, email, password_hash, role)
        VALUES (:aid, 'AID', '网关管理员', :amail, 'x', 'admin'),
               (:sid, 'SID', '网关学生', :smail, 'x', 'student')
        ON CONFLICT (email) DO NOTHING
    """), {"aid": admin_id, "amail": f"gw-admin-{TAG}@lumina.edu",
           "sid": student_id, "smail": f"gw-stu-{TAG}@lumina.edu"})
    db.commit()
    db.close()

    yield {"admin_id": uuid.UUID(admin_id), "student_id": uuid.UUID(student_id)}

    db = SessionLocal()
    # 清理测试注册的模型/调用日志（保留 seed）
    db.execute(text("""
        DELETE FROM ai_call_logs
        WHERE model_name LIKE 'test-%' OR user_id IN (:sid, :aid);
        DELETE FROM ai_models WHERE model_name LIKE 'test-%';
        DELETE FROM event_tracking WHERE user_id IN (:sid, :aid);
        DELETE FROM api_logs WHERE user_id IN (:sid, :aid);
        DELETE FROM users WHERE email IN (:amail, :smail)
    """), {"sid": setup["student_id"], "aid": setup["admin_id"],
           "amail": f"gw-admin-{TAG}@lumina.edu", "smail": f"gw-stu-{TAG}@lumina.edu"})
    db.commit()
    db.close()


@pytest.fixture()
def ctx():
    return TestClient(app)


class TestPublicModels:
    def test_models_list_seeded(self, ctx, setup):
        resp = ctx.get("/api/v1/ai/models", headers={"Authorization": f"Bearer {make_token(str(setup['student_id']), 'student')}"})
        assert resp.status_code == 200
        names = [m["model_name"] for m in resp.json()]
        assert "qwen-max" in names
        assert "glm-4" in names

    def test_models_filter_by_task(self, ctx, setup):
        resp = ctx.get("/api/v1/ai/models?task_type=vl",
                       headers={"Authorization": f"Bearer {make_token(str(setup['student_id']), 'student')}"})
        names = [m["model_name"] for m in resp.json()]
        assert "qwen-vl" in names
        assert "qwen-max" not in names

    def test_auth_required(self, ctx):
        assert ctx.get("/api/v1/ai/models").status_code == 401


class TestRouting:
    def test_route_chat_returns_priority(self, ctx, setup):
        resp = ctx.post("/api/v1/ai/gateway/route",
                        headers={"Authorization": f"Bearer {make_token(str(setup['student_id']), 'student')}"},
                        json={"task_type": "chat"})
        assert resp.status_code == 200
        body = resp.json()
        # qwen-max (prio 10) 应为主选，glm-4/... 备选
        assert body["primary"]["model_name"] == "qwen-max"
        assert body["fallback"] is not None
        assert body["note"] == "OK"

    def test_route_grade_returns_glm(self, ctx, setup):
        resp = ctx.post("/api/v1/ai/gateway/route",
                        headers={"Authorization": f"Bearer {make_token(str(setup['student_id']), 'student')}"},
                        json={"task_type": "grade"})
        body = resp.json()
        assert body["primary"]["model_name"] == "glm-4"  # grade 唯一 prio 20

    def test_route_speech(self, ctx, setup):
        resp = ctx.post("/api/v1/ai/gateway/route",
                        headers={"Authorization": f"Bearer {make_token(str(setup['student_id']), 'student')}"},
                        json={"task_type": "speech"})
        body = resp.json()
        assert body["primary"]["model_name"] == "spark-v3"

    def test_route_invalid_task(self, ctx, setup):
        resp = ctx.post("/api/v1/ai/gateway/route",
                        headers={"Authorization": f"Bearer {make_token(str(setup['student_id']), 'student')}"},
                        json={"task_type": "bogus"})
        assert resp.status_code == 422


class TestAdminModelPool:
    def test_register_and_toggle(self, ctx, setup):
        headers = {"Authorization": f"Bearer {make_token(str(setup['admin_id']), 'admin')}"}
        # 注册测试模型
        resp = ctx.post("/api/v1/ai/gateway/models", headers=headers, json={
            "provider_name": "qwen", "model_name": f"test-{TAG}", "display_name": "测试模型",
            "task_types": ["chat"], "priority": 99, "cost_per_1k_tokens": "0.01"})
        assert resp.status_code == 201, resp.text
        mid = resp.json()["id"]

        # 停用
        resp = ctx.patch(f"/api/v1/ai/gateway/models/{mid}", headers=headers, json={"enabled": False})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

        # 停用后不进 public 列表
        pub = ctx.get("/api/v1/ai/models",
                      headers={"Authorization": f"Bearer {make_token(str(setup['student_id']), 'student')}"})
        assert f"test-{TAG}" not in [m["model_name"] for m in pub.json()]

    def test_student_cannot_admin(self, ctx, setup):
        resp = ctx.get("/api/v1/ai/gateway/models",
                       headers={"Authorization": f"Bearer {make_token(str(setup['student_id']), 'student')}"})
        assert resp.status_code == 403

    def test_provider_register_conflict(self, ctx, setup):
        headers = {"Authorization": f"Bearer {make_token(str(setup['admin_id']), 'admin')}"}
        resp = ctx.post("/api/v1/ai/gateway/providers", headers=headers,
                        json={"name": "qwen", "display_name": "重复"})
        assert resp.status_code == 409


class TestUsage:
    def test_record_and_stats(self, ctx, setup):
        # 从管理面拿 glm-4 模型 ID
        model_id = db_model_id(ctx, setup)

        rec = ctx.post("/api/v1/ai/gateway/calls/record",
                       headers={"Authorization": f"Bearer {make_token(str(setup['student_id']), 'student')}"},
                       json={"model_id": model_id, "task_type": "grade",
                             "prompt_tokens": 500, "completion_tokens": 300, "latency_ms": 1200})
        assert rec.status_code == 200, rec.text

        # 用量统计
        stats = ctx.get("/api/v1/ai/gateway/usage?days=7",
                        headers={"Authorization": f"Bearer {make_token(str(setup['admin_id']), 'admin')}"})
        assert stats.status_code == 200
        assert stats.json()["total_calls"] >= 1
        assert stats.json()["by_model"]["glm-4"]["tokens"] >= 800


def db_model_id(ctx, setup):
    """管理面取 glm-4 的 UUID"""
    resp = ctx.get("/api/v1/ai/gateway/models",
                   headers={"Authorization": f"Bearer {make_token(str(setup['admin_id']), 'admin')}"})
    return next(m["id"] for m in resp.json() if m["model_name"] == "glm-4")