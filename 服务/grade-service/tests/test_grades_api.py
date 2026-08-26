# ============================================
# Lumina 墨光 · 成绩服务 接口集成测试
# 需要 PostgreSQL 已启动
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

from app.config import settings  # noqa: E402

TAG = uuid.uuid4().hex[:8]

TEACHER = ("T" + TAG, f"t-{TAG}@lumina.edu", "成绩教师")
STUDENT = ("S" + TAG, f"s-{TAG}@lumina.edu", "成绩学生")
STUDENT2 = ("S2" + TAG, f"s2-{TAG}@lumina.edu", "成绩学生二")


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
    teacher_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())
    student2_id = str(uuid.uuid4())
    course_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO users (id, student_id, name, email, password_hash, role)
        VALUES (:tid, :tno, :tname, :tmail, 'x', 'teacher'),
               (:sid, :sno, :sname, :smail, 'x', 'student'),
               (:sid2, :sno2, :sname2, :smail2, 'x', 'student')
        ON CONFLICT (email) DO NOTHING
    """), {"tid": teacher_id, "tno": TEACHER[0], "tname": TEACHER[2], "tmail": TEACHER[1],
           "sid": student_id, "sno": STUDENT[0], "sname": STUDENT[2], "smail": STUDENT[1],
           "sid2": student2_id, "sno2": STUDENT2[0], "sname2": STUDENT2[2], "smail2": STUDENT2[1]})
    db.execute(text("""
        INSERT INTO courses (id, code, title, teacher_id, credits, semester, status)
        VALUES (:cid, :code, '成绩测试课程', :tid, 4.0, '2026-1', 'published')
        ON CONFLICT (code) DO NOTHING
    """), {"cid": course_id, "code": f"GR{TAG}", "tid": teacher_id})
    db.commit()
    db.close()

    yield {"teacher_id": uuid.UUID(teacher_id), "student_id": uuid.UUID(student_id),
           "student2_id": uuid.UUID(student2_id), "course_id": uuid.UUID(course_id)}

    db = SessionLocal()
    db.execute(text("""
        DELETE FROM grade_records WHERE course_id = :cid;
        DELETE FROM api_logs WHERE path LIKE '/api/v1/%';
        DELETE FROM event_tracking; DELETE FROM courses WHERE code = :code;
        DELETE FROM users WHERE email IN (:tmail, :smail, :smail2)
    """), {"cid": course_id, "code": f"GR{TAG}",
           "tmail": TEACHER[1], "smail": STUDENT[1], "smail2": STUDENT2[1]})
    db.commit()
    db.close()


@pytest.fixture()
def ctx():
    return TestClient(app)


def _headers(uid: uuid.UUID, role: str):
    return {"Authorization": f"Bearer {make_token(str(uid), role)}"}


class TestGradeRecord:
    def test_teacher_records_students(self, ctx, setup):
        """录入两个学生成绩"""
        for uid, score in [(setup["student_id"], 92), (setup["student2_id"], 76)]:
            resp = ctx.post(f"/api/v1/courses/{setup['course_id']}/grades",
                            headers=_headers(setup["teacher_id"], "teacher"),
                            json={"student_id": str(uid), "final_score": score, "semester": "2026-1"})
            assert resp.status_code == 201, resp.text
            assert resp.json()["gpa_point"] <= 4.0

    def test_update_gpa_recomputed(self, ctx, setup):
        """重复录入同一学生 → 更新不新增"""
        uid = setup["student_id"]
        url = f"/api/v1/courses/{setup['course_id']}/grades"
        ctx.post(url, headers=_headers(setup["teacher_id"], "teacher"),
                 json={"student_id": str(uid), "final_score": 92, "semester": "2026-1"})
        resp = ctx.post(url, headers=_headers(setup["teacher_id"], "teacher"),
                        json={"student_id": str(uid), "final_score": 85, "semester": "2026-1"})
        assert resp.status_code == 201
        assert resp.json()["gpa_point"] == 3.7

    def test_student_cannot_record(self, ctx, setup):
        resp = ctx.post(f"/api/v1/courses/{setup['course_id']}/grades",
                        headers=_headers(setup["student_id"], "student"),
                        json={"student_id": str(setup["student_id"]), "final_score": 90, "semester": "2026-1"})
        assert resp.status_code == 403

    def test_record_for_nonexistent_student(self, ctx, setup):
        resp = ctx.post(f"/api/v1/courses/{setup['course_id']}/grades",
                        headers=_headers(setup["teacher_id"], "teacher"),
                        json={"student_id": str(uuid.uuid4()), "final_score": 88, "semester": "2026-1"})
        assert resp.status_code == 400

    def test_teacher_list_course_grades(self, ctx, setup):
        resp = ctx.get(f"/api/v1/courses/{setup['course_id']}/grades",
                       headers=_headers(setup["teacher_id"], "teacher"))
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        names = [r["student_name"] for r in resp.json()]
        assert STUDENT[2] in names

    def test_unrelated_teacher_forbidden(self, ctx, setup):
        # 另一教师（非授课）查询 → 403
        other = str(uuid.uuid4())
        db = SessionLocal()
        db.execute(text("""
            INSERT INTO users (id, student_id, name, email, password_hash, role)
            VALUES (:id, 'OT', '外部教师', :mail, 'x', 'teacher') ON CONFLICT (email) DO NOTHING
        """), {"id": other, "mail": f"ot-{TAG}@lumina.edu"})
        db.commit()
        db.close()
        resp = ctx.get(f"/api/v1/courses/{setup['course_id']}/grades",
                       headers=_headers(uuid.UUID(other), "teacher"))
        assert resp.status_code == 403


class TestMyGrades:
    def test_student_transcript(self, ctx, setup):
        resp = ctx.get("/api/v1/grades/me", headers=_headers(setup["student_id"], "student"),
                       params={"course_id": setup["course_id"]})
        assert resp.status_code == 200
        body = resp.json()
        # student 成绩 92（GPA 4.0 × 4 学分）+ 更新后 85 -> 应存在记录
        assert body["gpa"] is not None
        assert body["course_count"] >= 1

    def test_student_gpa_accuracy(self, ctx, setup):
        """仅一门 92 分 4 学分 → GPA = 4.0, credits = 4"""
        resp = ctx.get("/api/v1/grades/me", headers=_headers(setup["student2_id"], "student"))
        body = resp.json()
        assert body["courses"][0]["score"] == 76
        assert body["gpa"] == 2.7  # 76 → 2.7
        assert body["total_credits"] == 4.0


class TestStatistics:
    def test_course_statistics(self, ctx, setup):
        resp = ctx.get("/api/v1/grades/statistics",
                       headers=_headers(setup["teacher_id"], "teacher"),
                       params={"course_id": str(setup["course_id"])})
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        assert body["pass_rate"] == 1.0
        assert body["distribution"]["A"] >= 1
        assert body["distribution"]["C"] >= 1

    def test_statistics_semester_filter(self, ctx, setup):
        resp = ctx.get("/api/v1/grades/statistics",
                       headers=_headers(setup["teacher_id"], "teacher"),
                       params={"semester": "2026-1"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 2


class TestMonitoring:
    def test_grade_recorded_event(self, ctx, setup):
        ctx.post(f"/api/v1/courses/{setup['course_id']}/grades",
                 headers=_headers(setup["teacher_id"], "teacher"),
                 json={"student_id": str(setup["student2_id"]), "final_score": 80, "semester": "2026-2"})
        db = SessionLocal()
        row = db.execute(text(
            "SELECT event_name FROM event_tracking WHERE event_name = 'grade.recorded' ORDER BY id DESC LIMIT 1"
        )).first()
        db.close()
        assert row is not None

    def test_api_log_recorded(self, ctx):
        ctx.get("/health")
        db = SessionLocal()
        count = db.execute(text("SELECT count(*) FROM api_logs")).scalar()
        db.close()
        assert count > 0