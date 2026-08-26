# ============================================
# Lumina 墨光 · 埋点收集服务接口集成测试
# 需要 PostgreSQL（阶段三验证）
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


def make_token(user_id: str, role: str) -> str:
    return jwt.encode(
        {"sub": str(user_id), "role": role, "type": "access",
         "exp": datetime.now(timezone.utc) + timedelta(minutes=15)},
        settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
    )


@pytest.fixture(scope="module", autouse=True)
def setup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    admin_id = str(uuid.uuid4())
    stu_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO users (id, name, email, password_hash, role)
        VALUES (:aid, '埋点管理员', :amail, 'x', 'admin'),
               (:sid, '埋点学生', :smail, 'x', 'student')
        ON CONFLICT (email) DO NOTHING
    """), {"aid": admin_id, "amail": f"analytics-admin-{TAG}@lumina.edu",
           "sid": stu_id, "smail": f"analytics-stu-{TAG}@lumina.edu"})
    db.commit()
    db.close()
    yield {"admin": admin_id, "stu": stu_id}

    db = SessionLocal()
    db.execute(text("""
        DELETE FROM event_tracking WHERE session_id LIKE 'test-%' OR user_id IN (:aid, :sid);
        DELETE FROM api_logs WHERE user_id IN (:aid, :sid);
        DELETE FROM users WHERE email IN (:amail, :smail)
    """), {"aid": uuid.UUID(admin_id), "sid": uuid.UUID(stu_id),
           "amail": f"analytics-admin-{TAG}@lumina.edu", "smail": f"analytics-stu-{TAG}@lumina.edu"})
    db.commit()
    db.close()


@pytest.fixture()
def ctx():
    return TestClient(app)


class TestIngest:
    def test_guest_event_accepted(self, ctx):
        r = ctx.post("/api/v1/events", json={
            "event_name": "page.view",
            "session_id": f"test-{TAG}",
            "page_url": "http://localhost/",
            "properties": {"anon": True},
        })
        assert r.status_code == 202, r.text

    def test_batch_accepted(self, ctx):
        r = ctx.post("/api/v1/events/batch", json={
            "events": [
                {"event_name": "page.view", "session_id": f"test-{TAG}"},
                {"event_name": "element.click", "session_id": f"test-{TAG}", "properties": {"label": "登录"}},
            ]
        })
        assert r.status_code == 202

    def test_logged_user_event(self, ctx, setup):
        r = ctx.post(
            "/api/v1/events",
            headers={"Authorization": f"Bearer {make_token(setup['stu'], 'student')}"},
            json={"event_name": "course.view", "session_id": f"test-{TAG}"},
        )
        assert r.status_code == 202


class TestStats:
    def test_stats_require_admin(self, ctx, setup):
        # 无 token → 401
        assert ctx.get("/api/v1/events/stats").status_code == 401
        # 学生 → 403
        r = ctx.get("/api/v1/events/stats",
                    headers={"Authorization": f"Bearer {make_token(setup['stu'], 'student')}"})
        assert r.status_code == 403

    def test_stats_and_breakdown(self, ctx, setup):
        headers = {"Authorization": f"Bearer {make_token(setup['admin'], 'admin')}"}
        stats = ctx.get("/api/v1/events/stats?days=7", headers=headers)
        assert stats.status_code == 200
        assert stats.json()["total"] >= 1

        bd = ctx.get("/api/v1/events/breakdown?days=7", headers=headers)
        assert bd.status_code == 200
        names = [row["event_name"] for row in bd.json()]
        assert "page.view" in names
        assert all(row["count"] >= 1 for row in bd.json())