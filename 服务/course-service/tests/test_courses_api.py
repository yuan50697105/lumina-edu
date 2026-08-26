# ============================================
# Lumina 墨光 · 课程服务 接口集成测试
# 需要 PostgreSQL + users 表（user-service/init.sql 提供）
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
from app.models import Announcement, Chapter, Course, Enrollment

# 连接不上数据库则整组跳过
try:
    db = SessionLocal()
    db.execute(text("SELECT 1"))
    db.close()
    DB_READY = True
except Exception:
    DB_READY = False

pytestmark = pytest.mark.skipif(not DB_READY, reason="PostgreSQL 未就绪（docker-compose up -d postgres）")

from app.config import settings  # noqa: E402

TEST_TAG = uuid.uuid4().hex[:8]

# 测试用户（插入共享 users 表）
TEACHER = {
    "student_id": f"T{TEST_TAG}", "name": "测试教师", "email": f"teacher-{TEST_TAG}@lumina.edu",
    "role": "teacher", "department": "数学学院",
}
STUDENT = {
    "student_id": f"S{TEST_TAG}", "name": "测试学生", "email": f"student-{TEST_TAG}@lumina.edu",
    "role": "student", "department": "计算机学院",
}


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
    db.execute(text("""
        INSERT INTO users (id, student_id, name, email, password_hash, role, department)
        VALUES (:tid, :tno, :tname, :tmail, 'x', 'teacher', :tdept),
               (:sid, :sno, :sname, :smail, 'x', 'student', :sdept)
        ON CONFLICT (email) DO NOTHING
    """), {
        "tid": teacher_id, "tno": TEACHER["student_id"], "tname": TEACHER["name"],
        "tmail": TEACHER["email"], "tdept": TEACHER["department"],
        "sid": student_id, "sno": STUDENT["student_id"], "sname": STUDENT["name"],
        "smail": STUDENT["email"], "sdept": STUDENT["department"],
    })
    db.commit()
    db.close()

    yield {"teacher_id": uuid.UUID(teacher_id), "student_id": uuid.UUID(student_id)}

    # 清理
    db = SessionLocal()
    db.execute(text("""
        DELETE FROM announcements; DELETE FROM enrollments; DELETE FROM chapters; DELETE FROM courses;
        DELETE FROM event_tracking; DELETE FROM api_logs WHERE path LIKE '/api/v1/%';
        DELETE FROM users WHERE email IN (:tmail, :smail)
    """), {"tmail": TEACHER["email"], "smail": STUDENT["email"]})
    db.commit()
    db.close()


@pytest.fixture()
def client():
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "course-service"


class TestCourseCRUD:
    def _create_published_course(self, client, setup, code=None, semester="2026-1"):
        token = make_token(setup["teacher_id"], "teacher")
        code = code or f"CS{TEST_TAG}"
        resp = client.post("/api/v1/courses", headers={"Authorization": f"Bearer {token}"}, json={
            "code": code, "title": "高等数学", "description": "微积分基础",
            "department": "数学学院", "credits": 4.0, "semester": semester,
        })
        assert resp.status_code == 201, resp.text
        course = resp.json()
        # 发布课程
        resp2 = client.patch(f"/api/v1/courses/{course['id']}",
                             headers={"Authorization": f"Bearer {token}"},
                             json={"status": "published"})
        assert resp2.status_code == 200
        return course

    def test_teacher_creates_course(self, client, setup):
        course = self._create_published_course(client, setup, code=f"CS{TEST_TAG}-1")
        assert course["title"] == "高等数学"
        assert course["status"] == "published"
        assert course["teacher"]["name"] == "测试教师"  # join users 成功

    def test_course_code_conflict(self, client, setup):
        self._create_published_course(client, setup, code=f"CS{TEST_TAG}-dup")
        resp = client.post("/api/v1/courses",
                           headers={"Authorization": f"Bearer {make_token(setup['teacher_id'], 'teacher')}"},
                           json={"code": f"CS{TEST_TAG}-dup", "title": "重复", "semester": "2026-1"})
        assert resp.status_code == 409

    def test_student_cannot_create(self, client, setup):
        resp = client.post("/api/v1/courses",
                           headers={"Authorization": f"Bearer {make_token(setup['student_id'], 'student')}"},
                           json={"code": f"CS{TEST_TAG}-stu", "title": "越权", "semester": "2026-1"})
        assert resp.status_code == 403

    def test_list_courses(self, client, setup):
        self._create_published_course(client, setup, code=f"CS{TEST_TAG}-list")
        resp = client.get("/api/v1/courses",
                          headers={"Authorization": f"Bearer {make_token(setup['student_id'], 'student')}"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    def test_auth_required(self, client):
        resp = client.get("/api/v1/courses")
        assert resp.status_code == 401


class TestEnrollment:
    def test_student_enroll_then_drop(self, client, setup):
        course = self._seed(client, setup, "CS-ENR")
        token = make_token(setup["student_id"], "student")
        eurl = f"/api/v1/courses/{course['id']}/enroll"

        # 选课
        resp = client.post(eurl, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "student"

        # 重复选课
        resp = client.post(eurl, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 409

        # 退课
        resp = client.delete(eurl, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_student_cannot_enroll_draft_course(self, client, setup):
        token_t = make_token(setup["teacher_id"], "teacher")
        resp = client.post("/api/v1/courses", headers={"Authorization": f"Bearer {token_t}"}, json={
            "code": "CS-DRAFT", "title": "未发布课程", "semester": "2026-1"})
        course_id = resp.json()["id"]

        resp = client.post(f"/api/v1/courses/{course_id}/enroll",
                           headers={"Authorization": f"Bearer {make_token(setup['student_id'], 'student')}"})
        assert resp.status_code == 400

    def test_my_courses(self, client, setup):
        course = self._seed(client, setup, "CS-MINE")
        token = make_token(setup["student_id"], "student")
        client.post(f"/api/v1/courses/{course['id']}/enroll", headers={"Authorization": f"Bearer {token}"})
        resp = client.get("/api/v1/courses/me/enrolled", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_teacher_sees_students(self, client, setup):
        course = self._seed(client, setup, "CS-STU")
        # 学生选课
        stoken = make_token(setup["student_id"], "student")
        client.post(f"/api/v1/courses/{course['id']}/enroll", headers={"Authorization": f"Bearer {stoken}"})
        # 教师查学生列表
        resp = client.get(f"/api/v1/courses/{course['id']}/students",
                          headers={"Authorization": f"Bearer {make_token(setup['teacher_id'], 'teacher')}"})
        assert resp.status_code == 200
        names = [s["name"] for s in resp.json()]
        assert "测试学生" in names

    def _seed(self, client, setup, code):
        token = make_token(setup["teacher_id"], "teacher")
        resp = client.post("/api/v1/courses", headers={"Authorization": f"Bearer {token}"}, json={
            "code": f"{code}-{TEST_TAG}", "title": "选课测试课程", "semester": "2026-1"})
        cid = resp.json()["id"]
        client.patch(f"/api/v1/courses/{cid}", headers={"Authorization": f"Bearer {token}"}, json={"status": "published"})
        return client.get(f"/api/v1/courses/{cid}",
                          headers={"Authorization": f"Bearer {make_token(setup['student_id'], 'student')}"}).json()


class TestChaptersAndAnnouncements:
    def test_chapter_crud(self, client, setup):
        # 教师建课程
        token_t = make_token(setup["teacher_id"], "teacher")
        resp = client.post("/api/v1/courses", headers={"Authorization": f"Bearer {token_t}"}, json={
            "code": f"CH{TEST_TAG}", "title": "章节测试", "semester": "2026-1"})
        cid = resp.json()["id"]

        # 新增章节
        resp = client.post(f"/api/v1/courses/{cid}/chapters", headers={"Authorization": f"Bearer {token_t}"},
                           json={"title": "第1章", "content": "# 绪论", "order_num": 1})
        assert resp.status_code == 201
        chid = resp.json()["id"]

        # 更新章节
        resp = client.patch(f"/api/v1/courses/{cid}/chapters/{chid}", headers={"Authorization": f"Bearer {token_t}"},
                            json={"content": "# 绪论（修订）"})
        assert resp.status_code == 200
        assert resp.json()["content"] == "# 绪论（修订）"

        # 章节列表
        resp = client.get(f"/api/v1/courses/{cid}/chapters",
                          headers={"Authorization": f"Bearer {make_token(setup['student_id'], 'student')}"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # 删除章节
        resp = client.delete(f"/api/v1/courses/{cid}/chapters/{chid}", headers={"Authorization": f"Bearer {token_t}"})
        assert resp.status_code == 200

    def test_announcement_flow(self, client, setup):
        token_t = make_token(setup["teacher_id"], "teacher")
        resp = client.post("/api/v1/courses", headers={"Authorization": f"Bearer {token_t}"}, json={
            "code": f"AN{TEST_TAG}", "title": "公告测试", "semester": "2026-1"})
        cid = resp.json()["id"]

        resp = client.post(f"/api/v1/courses/{cid}/announcements", headers={"Authorization": f"Bearer {token_t}"},
                           json={"title": "调课通知", "content": "下周三停课", "pinned": True})
        assert resp.status_code == 201
        aid = resp.json()["id"]

        resp = client.get(f"/api/v1/courses/{cid}/announcements",
                          headers={"Authorization": f"Bearer {make_token(setup['student_id'], 'student')}"})
        assert resp.status_code == 200
        assert any(a["id"] == aid for a in resp.json())


class TestMonitoring:
    def test_course_event_recorded(self, client, setup):
        """选课后 event_tracking 应新增 course.enroll"""
        token_t = make_token(setup["teacher_id"], "teacher")
        resp = client.post("/api/v1/courses", headers={"Authorization": f"Bearer {token_t}"}, json={
            "code": f"EV{TEST_TAG}", "title": "埋点测试", "semester": "2026-1"})
        cid = resp.json()["id"]
        client.patch(f"/api/v1/courses/{cid}", headers={"Authorization": f"Bearer {token_t}"}, json={"status": "published"})

        stoken = make_token(setup["student_id"], "student")
        client.post(f"/api/v1/courses/{cid}/enroll", headers={"Authorization": f"Bearer {stoken}"})

        db = SessionLocal()
        row = db.execute(
            text("SELECT event_name FROM event_tracking WHERE event_name = 'course.enroll' ORDER BY id DESC LIMIT 1")
        ).first()
        db.close()
        assert row is not None

    def test_api_log_recorded(self, client):
        client.get("/health")
        db = SessionLocal()
        count = db.execute(text("SELECT count(*) FROM api_logs")).scalar()
        db.close()
        assert count > 0