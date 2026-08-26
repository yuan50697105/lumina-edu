# ============================================
# Lumina 墨光 · 基础日志系统接口集成测试
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
        {"sub": user_id, "role": role, "type": "access",
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
        VALUES (:aid, '日志管理员', :amail, 'x', 'admin'),
               (:sid, '日志学生', :smail, 'x', 'student')
        ON CONFLICT (email) DO NOTHING
    """), {"aid": admin_id, "amail": f"logs-admin-{TAG}@lumina.edu",
           "sid": stu_id, "smail": f"logs-stu-{TAG}@lumina.edu"})
    # 预置日志：1 条成功 + 1 条 500（带 request_id）
    db.execute(text("""
        INSERT INTO api_logs (method, path, status_code, duration_ms, user_id, request_id, error_message)
        VALUES ('GET', '/api/v1/courses', 200, 42, :uid, :rid, NULL),
               ('GET', '/api/v1/grades', 500, 1200, NULL, :rid2, 'boom')
    """), {"uid": admin_id, "rid": f"log-{TAG}", "rid2": f"err-{TAG}"})
    db.commit()
    db.close()
    yield admin_id, stu_id

    db = SessionLocal()
    db.execute(text("DELETE FROM api_logs WHERE request_id IN (:r1, :r2)"),
               {"r1": f"log-{TAG}", "r2": f"err-{TAG}"})
    db.commit()
    db.close()


def _auth(uid: str, role: str):
    return {"Authorization": "Bearer " + make_token(uid, role)}


def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "logs-service"


def test_query_requires_auth():
    client = TestClient(app)
    assert client.get("/api/v1/logs/query").status_code == 401
    assert client.get("/api/v1/logs/summary").status_code == 401


def test_query_student_forbidden(setup):
    client = TestClient(app)
    _, stu_uid = setup
    assert client.get("/api/v1/logs/query", headers=_auth(stu_uid, "student")).status_code == 403


def test_query_by_request_id(setup):
    admin_uid, _ = setup
    client = TestClient(app)
    r = client.get("/api/v1/logs/query", headers=_auth(admin_uid, "admin"),
                   params={"request_id": f"log-{TAG}"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert all(rec["request_id"] == f"log-{TAG}" for rec in body["records"])


def test_query_by_status(setup):
    admin_uid, _ = setup
    client = TestClient(app)
    r = client.get("/api/v1/logs/query", headers=_auth(admin_uid, "admin"),
                   params={"status": 500})
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    assert all(rec["status_code"] == 500 for rec in r.json()["records"])


def test_summary_metrics(setup):
    admin_uid, _ = setup
    client = TestClient(app)
    r = client.get("/api/v1/logs/summary", headers=_auth(admin_uid, "admin"))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 2
    assert body["errors"] >= 1
    assert body["error_rate"] > 0
    assert body["avg_duration_ms"] >= 0


def test_openapi_mounts_logs():
    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    assert "/api/v1/logs/query" in spec["paths"]
    assert "/api/v1/logs/summary" in spec["paths"]