# ============================================
# Lumina 墨光 · 直播模块单元测试（V1.1 · D-01）
# 表结构 / 唯一约束 / schema 校验 / openapi 注册
# 纯内存断言，不连数据库
# ============================================
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from app.database import Base
from app.main import app
from app.models import (
    LiveAttendee,
    LiveMessage,
    LiveQuiz,
    LiveQuizAnswer,
    LiveRoom,
)
from app.schemas import (
    LiveCallIn,
    LiveMessageCreate,
    LiveQuizAnswerIn,
    LiveQuizCreate,
    LiveRaiseRequest,
    LiveRoomCreate,
)


@pytest.fixture(scope="module")
def tables():
    """获取所有表名"""
    return set(Base.metadata.tables.keys())


class TestTableDefinitions:
    """直播表定义测试"""

    def test_all_live_tables_exist(self, tables):
        """5 张直播表已定义"""
        expected = {"live_rooms", "live_attendees", "live_messages", "live_quizzes", "live_quiz_answers"}
        assert expected.issubset(tables), f"缺少表: {expected - tables}"

    def test_live_room_columns(self):
        """live_rooms 必要字段"""
        mapper = inspect(LiveRoom)
        columns = {c.key for c in mapper.columns}
        required = {"id", "course_id", "teacher_id", "title", "status", "created_at"}
        assert required.issubset(columns)

    def test_live_attendee_unique_constraint(self):
        """live_attendees 唯一约束（room+user）"""
        unique = {uc.name for uc in LiveAttendee.__table__.constraints if getattr(uc, "name", None)}
        assert "uq_live_attendee" in unique

    def test_quiz_answer_unique_constraint(self):
        """live_quiz_answers 唯一约束（quiz+user 一题一答）"""
        unique = {uc.name for uc in LiveQuizAnswer.__table__.constraints if getattr(uc, "name", None)}
        assert "uq_quiz_answer" in unique

    def test_quiz_options_json(self):
        """live_quizzes.options 为 JSON 列"""
        mapper = inspect(LiveQuiz)
        options = next(c for c in mapper.columns if c.key == "options")
        assert options.type.__class__.__name__ in ("JSON", "JSONType")


class TestRoomSchema:
    """直播房间 schema 校验"""

    def test_requires_course_id(self):
        """course_id 必填"""
        with pytest.raises(ValidationError):
            LiveRoomCreate()

    def test_title_optional(self):
        """title 可选（缺省由后端补课程名）"""
        m = LiveRoomCreate(course_id=uuid.uuid4())
        assert m.title is None

    def test_room_out_from_attributes(self):
        """LiveRoomOut 支持 ORM from_attributes"""
        from app.schemas import LiveRoomOut
        room = LiveRoom(
            id=uuid.uuid4(), course_id=uuid.uuid4(), teacher_id=uuid.uuid4(),
            title="测试直播", status="scheduled",
        )
        out = LiveRoomOut.model_validate(room)
        assert out.title == "测试直播" and out.status == "scheduled"


class TestRaiseSchema:
    """举手 schema"""

    def test_active_default_true(self):
        """默认举手为 True"""
        assert LiveRaiseRequest().active is True

    def test_active_false(self):
        """可传 False 取消举手"""
        assert LiveRaiseRequest(active=False).active is False


class TestQuizSchema:
    """答题 schema 校验"""

    def test_options_required(self):
        """无 question/options 时报错"""
        with pytest.raises(ValidationError):
            LiveQuizCreate()

    def test_quiz_out_from_attributes(self):
        """LiveQuizOut 支持 ORM from_attributes"""
        from app.schemas import LiveQuizOut
        quiz = LiveQuiz(
            id=uuid.uuid4(), room_id=uuid.uuid4(), teacher_id=uuid.uuid4(),
            question="1+1=", options=[{"key": "A", "text": "2"}], status="active",
        )
        out = LiveQuizOut.model_validate(quiz)
        assert out.options[0]["key"] == "A" and out.status == "active"


class TestMessageSchema:
    """消息 schema 校验"""

    def test_requires_content(self):
        """content 必填"""
        with pytest.raises(ValidationError):
            LiveMessageCreate(msg_type="chat")

    def test_default_type_chat(self):
        """缺省消息类型为 chat"""
        m = LiveMessageCreate(content="你好")
        assert m.msg_type == "chat"

    def test_message_out_from_attributes(self):
        """LiveMessageOut 支持 ORM from_attributes"""
        from app.schemas import LiveMessageOut
        msg = LiveMessage(id=1, room_id=uuid.uuid4(), user_id=uuid.uuid4(), msg_type="chat",
                          content="hi", created_at=datetime.now(timezone.utc))
        out = LiveMessageOut.model_validate(msg)
        assert out.content == "hi"


class TestCallSchema:
    """点名 schema"""

    def test_user_id_optional(self):
        """不传 user_id 表示随机点名"""
        assert LiveCallIn().user_id is None

    def test_user_id_present(self):
        uid = uuid.uuid4()
        assert LiveCallIn(user_id=uid).user_id == uid


class TestOpenAPILive:
    """openapi 直播端点注册"""

    def test_16_live_paths_registered(self):
        """16 个直播端点全部出现在 openapi"""
        spec = app.openapi()
        live_paths = [p for p in spec["paths"] if "/live" in p or "/live/rooms" in p]
        assert len(live_paths) >= 16
        assert "/api/v1/live/rooms" in spec["paths"]
        assert "/api/v1/live/rooms/{room_id}/start" in spec["paths"]
        assert "/api/v1/live/rooms/{room_id}/quizzes/{quiz_id}/result" in spec["paths"]

    def test_quiz_answer_choices_validation(self):
        """LiveQuizAnswerIn 必须 choice"""
        with pytest.raises(ValidationError):
            LiveQuizAnswerIn()
        assert LiveQuizAnswerIn(choice="A").choice == "A"