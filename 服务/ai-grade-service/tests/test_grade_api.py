# ============================================
# Lumina 墨光 · AI 批阅服务接口集成测试
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


def make_token(user_id: str, role: str = "teacher") -> str:
    return jwt.encode(
        {"sub": str(user_id), "role": role, "type": "access",
         "exp": datetime.now(timezone.utc) + timedelta(minutes=15)},
        settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
    )


@pytest.fixture(scope="module", autouse=True)
def setup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    tid = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO users (id, student_id, name, email, password_hash, role)
        VALUES (:tid, 'GRD', '批阅教师', :mail, 'x', 'teacher')
        ON CONFLICT (email) DO NOTHING
    """), {"tid": tid, "mail": f"grade-teacher-{TAG}@lumina.edu"})
    db.commit()
    db.close()

    yield tid

    db = SessionLocal()
    db.execute(text("""
        DELETE FROM grades WHERE grader_id = :tid;
        DELETE FROM event_tracking WHERE user_id = :tid;
        DELETE FROM api_logs WHERE user_id = :tid;
        DELETE FROM users WHERE id = :tid
    """), {"tid": uuid.UUID(tid)})
    db.commit()
    db.close()


@pytest.fixture()
def ctx():
    return TestClient(app)


class TestGradePost:
    def test_auth_required(self, ctx):
        r = ctx.post("/api/v1/ai/grade", json={
            "assignment_id": str(uuid.uuid4()), "submission_id": str(uuid.uuid4()),
        })
        assert r.status_code == 401

    def test_student_forbidden(self, ctx, setup):
        r = ctx.post(
            "/api/v1/ai/grade",
            headers={"Authorization": f"Bearer {make_token(setup, 'student')}"},
            json={"assignment_id": str(uuid.uuid4()), "submission_id": str(uuid.uuid4())},
        )
        assert r.status_code == 403

    def test_assignment_not_found(self, ctx, setup):
        r = ctx.post(
            "/api/v1/ai/grade",
            headers={"Authorization": f"Bearer {make_token(setup)}"},
            json={"assignment_id": str(uuid.uuid4()), "submission_id": str(uuid.uuid4())},
        )
        assert r.status_code == 404, r.text

    def test_no_gateway_graceful(self, ctx, setup):
        """网关不可达/无模型 → 400 或 502，绝不 500（可离线验证错误路径）"""
        db = SessionLocal()
        acc = str(uuid.uuid4())
        db.execute(text("""
            INSERT INTO courses (id, code, title, semester, status)
            VALUES (:cid, :code, '批阅测试课', '2026-1', 'published') ON CONFLICT DO NOTHING
        """), {"cid": acc, "code": f"GRD{acc[:8]}"})
        db.execute(text("""
            INSERT INTO assignments (id, course_id, title, max_score, rubric)
            VALUES (:aid, :cid, '测试作业', 100, :rubric) ON CONFLICT DO NOTHING
        """), {"aid": acc, "cid": acc,
               "rubric": [{"criteria": "完整", "weight": 1.0, "max_score": 100}]})
        db.execute(text("""
            INSERT INTO submissions (id, assignment_id, student_id, text_answer)
            VALUES (:sid, :aid, :stu, '解：x=1') ON CONFLICT DO NOTHING
        """), {"sid": str(uuid.uuid4()), "aid": acc, "stu": setup})
        db.commit()
        db.close()

        r = ctx.post(
            "/api/v1/ai/grade",
            headers={"Authorization": f"Bearer {make_token(setup)}"},
            json={"assignment_id": acc, "submission_id": acc},
        )
        assert r.status_code in (400, 502), r.text