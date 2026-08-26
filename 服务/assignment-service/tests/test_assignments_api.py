# ============================================
# Lumina 墨光 · 作业服务 接口集成测试
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

# 连接不上数据库则整组跳过
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

TEACHER = ("T" + TAG, f"t-{TAG}@lumina.edu", "作业教师")
STUDENT = ("S" + TAG, f"s-{TAG}@lumina.edu", "作业学生")


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
    course_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO users (id, student_id, name, email, password_hash, role)
        VALUES (:tid, :tno, :tname, :tmail, 'x', 'teacher'),
               (:sid, :sno, :sname, :smail, 'x', 'student')
        ON CONFLICT (email) DO NOTHING
    """), {"tid": teacher_id, "tno": TEACHER[0], "tname": TEACHER[2], "tmail": TEACHER[1],
           "sid": student_id, "sno": STUDENT[0], "sname": STUDENT[2], "smail": STUDENT[1]})
    db.execute(text("""
        INSERT INTO courses (id, code, title, teacher_id, semester, status)
        VALUES (:cid, :code, '作业测试课程', :tid, '2026-1', 'published')
        ON CONFLICT (code) DO NOTHING
    """), {"cid": course_id, "code": f"AS{TAG}", "tid": teacher_id})
    db.execute(text("""
        INSERT INTO enrollments (user_id, course_id, role, status)
        VALUES (:sid, :cid, 'student', 'active'),
               (:tid, :cid, 'teacher', 'active')
        ON CONFLICT (user_id, course_id) DO NOTHING
    """), {"sid": student_id, "cid": course_id, "tid": teacher_id})
    db.commit()
    db.close()

    yield {
        "teacher_id": uuid.UUID(teacher_id),
        "student_id": uuid.UUID(student_id),
        "course_id": uuid.UUID(course_id),
    }

    db = SessionLocal()
    db.execute(text("""
        DELETE FROM grades WHERE submission_id IN (SELECT id FROM submissions);
        DELETE FROM submissions; DELETE FROM assignments; DELETE FROM enrollments; DELETE FROM courses;
        DELETE FROM api_logs WHERE path LIKE '/api/v1/%';
        DELETE FROM event_tracking; DELETE FROM users WHERE email IN (:tmail, :smail)
    """), {"tmail": TEACHER[1], "smail": STUDENT[1]})
    db.commit()
    db.close()


@pytest.fixture()
def ctx():
    return TestClient(app)


def _headers(db, uid: uuid.UUID, role: str):
    return {"Authorization": f"Bearer {make_token(str(uid), role)}"}


def _create_published_assignment(client, setup, title="第四章习题", due=None):
    """教师发布作业并置为 published"""
    asg = client.post(f"/api/v1/courses/{setup['course_id']}/assignments",
                      headers=_headers(client, setup["teacher_id"], "teacher"),
                      json={"title": title, "description": "P120-P125", "max_score": 100,
                            "due_at": (due or datetime.now(timezone.utc) + timedelta(days=7)).isoformat()})
    assert asg.status_code == 201, asg.text
    aid = asg.json()["id"]
    upd = client.patch(f"/api/v1/assignments/{aid}",
                       headers=_headers(client, setup["teacher_id"], "teacher"),
                       json={"status": "published"})
    assert upd.status_code == 200
    return aid


class TestAssignmentFlow:
    def test_teacher_creates_and_publishes(self, ctx, setup):
        aid = _create_published_assignment(ctx, setup)
        detail = ctx.get(f"/api/v1/assignments/{aid}", headers=_headers(ctx, setup["student_id"], "student"))
        assert detail.status_code == 200
        assert detail.json()["status"] == "published"
        assert detail.json()["course_title"] == "作业测试课程"

    def test_student_cannot_create(self, ctx, setup):
        resp = ctx.post(f"/api/v1/courses/{setup['course_id']}/assignments",
                        headers=_headers(ctx, setup["student_id"], "student"),
                        json={"title": "越权", "max_score": 100})
        assert resp.status_code in (403, 401)

    def test_list_assignments_filters_published(self, ctx, setup):
        aid = _create_published_assignment(ctx, setup, title="列表可见")
        resp = ctx.get(f"/api/v1/assignments?course_id={setup['course_id']}",
                       headers=_headers(ctx, setup["student_id"], "student"))
        assert resp.status_code == 200
        titles = [a["title"] for a in resp.json()["data"]]
        assert "列表可见" in titles

    def test_teacher_unpublished_hidden_from_student(self, ctx, setup):
        # 创建但保持 draft
        asg = ctx.post(f"/api/v1/courses/{setup['course_id']}/assignments",
                       headers=_headers(ctx, setup["teacher_id"], "teacher"),
                       json={"title": "草稿作业", "max_score": 100})
        draft_id = asg.json()["id"]
        resp = ctx.get(f"/api/v1/assignments/{draft_id}", headers=_headers(ctx, setup["student_id"], "student"))
        assert resp.status_code == 403


class TestSubmission:
    def test_submit_and_view_me(self, ctx, setup):
        aid = _create_published_assignment(ctx, setup, title="提交测试")
        sub = ctx.post(f"/api/v1/assignments/{aid}/submit",
                       headers=_headers(ctx, setup["student_id"], "student"),
                       data={"text_answer": "解：x=1", "submission_note": "请批阅"})
        assert sub.status_code == 201, sub.text
        body = sub.json()
        assert body["text_answer"] == "解：x=1"
        assert body["late"] is False
        assert body["graded"] is False

        me = ctx.get(f"/api/v1/assignments/{aid}/submissions/me",
                     headers=_headers(ctx, setup["student_id"], "student"))
        assert me.status_code == 200
        assert me.json()["submission_note"] == "请批阅"

    def test_submit_without_enroll_forbidden(self, ctx, setup):
        # 未选课学生
        outsider_id = str(uuid.uuid4())
        from sqlalchemy import text as t
        db = SessionLocal()
        db.execute(t("""
            INSERT INTO users (id, student_id, name, email, password_hash, role)
            VALUES (:id, 'OUT', '局外人', :mail, 'x', 'student')
            ON CONFLICT (email) DO NOTHING
        """), {"id": outsider_id, "mail": f"out-{TAG}@lumina.edu"})
        db.commit()
        db.close()

        aid = _create_published_assignment(ctx, setup, title="选修校验")
        resp = ctx.post(f"/api/v1/assignments/{aid}/submit",
                        headers=_headers(ctx, uuid.UUID(outsider_id), "student"),
                        data={"text_answer": "x"})
        assert resp.status_code == 403

    def test_late_submission_flag(self, ctx, setup):
        # 已过截止时间
        past_due = datetime.now(timezone.utc) - timedelta(days=1)
        aid = _create_published_assignment(ctx, setup, title="迟交检测", due=past_due)
        sub = ctx.post(f"/api/v1/assignments/{aid}/submit",
                       headers=_headers(ctx, setup["student_id"], "student"),
                       data={"text_answer": "补交"})
        assert sub.status_code == 201
        assert sub.json()["late"] is True


class TestGrading:
    def test_teacher_grades(self, ctx, setup):
        aid = _create_published_assignment(ctx, setup, title="批阅测试")
        sub = ctx.post(f"/api/v1/assignments/{aid}/submit",
                       headers=_headers(ctx, setup["student_id"], "student"),
                       data={"text_answer": "完整解答"})
        sid = sub.json()["id"]

        grade = ctx.post(f"/api/v1/assignments/{aid}/grade?submission_id={sid}",
                         headers=_headers(ctx, setup["teacher_id"], "teacher"),
                         json={"total_score": 90, "feedback": "过程清晰"})
        assert grade.status_code == 200, grade.text
        assert str(grade.json()["grade_letter"]) == "A"
        assert grade.json()["graded_by"] == "teacher"

        # 学生视角：已批
        me = ctx.get(f"/api/v1/assignments/{aid}/submissions/me",
                     headers=_headers(ctx, setup["student_id"], "student"))
        assert me.json()["graded"] is True
        assert me.json()["grade"]["total_score"] == 90

    def test_score_exceeds_max_rejected(self, ctx, setup):
        aid = _create_published_assignment(ctx, setup, title="超分检测")
        sub = ctx.post(f"/api/v1/assignments/{aid}/submit",
                       headers=_headers(ctx, setup["student_id"], "student"),
                       data={"text_answer": "x"})
        sid = sub.json()["id"]
        resp = ctx.post(f"/api/v1/assignments/{aid}/grade?submission_id={sid}",
                        headers=_headers(ctx, setup["teacher_id"], "teacher"),
                        json={"total_score": 150})
        assert resp.status_code == 400

    def test_teacher_sees_submissions(self, ctx, setup):
        aid = _create_published_assignment(ctx, setup, title="提交列表")
        ctx.post(f"/api/v1/assignments/{aid}/submit",
                 headers=_headers(ctx, setup["student_id"], "student"), data={"text_answer": "答案A"})
        resp = ctx.get(f"/api/v1/assignments/{aid}/submissions",
                       headers=_headers(ctx, setup["teacher_id"], "teacher"))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1
        assert resp.json()[0]["student_name"] == STUDENT[2]


class TestMonitoring:
    def test_submit_event_recorded(self, ctx, setup):
        aid = _create_published_assignment(ctx, setup, title="埋点测试")
        ctx.post(f"/api/v1/assignments/{aid}/submit",
                 headers=_headers(ctx, setup["student_id"], "student"), data={"text_answer": "答案"})
        db = SessionLocal()
        row = db.execute(text(
            "SELECT event_name FROM event_tracking WHERE event_name = 'assignment.submitted' ORDER BY id DESC LIMIT 1"
        )).first()
        db.close()
        assert row is not None

    def test_api_log_recorded(self, ctx):
        ctx.get("/health")
        db = SessionLocal()
        count = db.execute(text("SELECT count(*) FROM api_logs")).scalar()
        db.close()
        assert count > 0