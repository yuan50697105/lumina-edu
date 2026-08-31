# ============================================
# Lumina 墨光 · 消息通知模块单元测试（V1.1 · D-03）
# 表结构 / schema 校验（含注册角色限制）/ openapi 注册
# 纯内存断言，不连数据库
# ============================================
import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from app.database import Base
from app.main import app
from app.models import Notification
from app.schemas import NotificationOut, RegisterRequest, UnreadCountOut


@pytest.fixture(scope="module")
def tables():
    """获取所有表名"""
    return set(Base.metadata.tables.keys())


class TestTableDefinitions:
    """消息通知表定义测试"""

    def test_notification_table_exists(self, tables):
        """notifications 表已定义"""
        assert "notifications" in tables

    def test_notification_columns(self):
        """notifications 必要字段"""
        mapper = inspect(Notification)
        columns = {c.key for c in mapper.columns}
        required = {"id", "user_id", "type", "title", "is_read", "created_at"}
        assert required.issubset(columns)

    def test_notification_user_index(self):
        """user_id 建有索引（按用户查列表）"""
        cols = [c.name for i in Notification.__table__.indexes for c in i.columns]
        assert "user_id" in cols

    def test_partial_columns(self):
        """可选择字段 ref_type/ref_id 可空"""
        mapper = inspect(Notification)
        for key in ("content", "ref_type", "ref_id"):
            assert mapper.columns[key].nullable, f"{key} 应可空"


class TestRegisterSchema:
    """注册 schema 校验"""

    def test_default_role_student(self):
        r = RegisterRequest(name="新同学", email="x@lumina.edu", password="Passw0rd1")
        assert r.role == "student"

    def test_admin_role_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(name="恶意", email="a@lumina.edu", password="Passw0rd1", role="admin")

    def test_short_password_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(name="短密码", email="b@lumina.edu", password="short")

    def test_teacher_role_allowed(self):
        r = RegisterRequest(
            name="王老师", email="w@lumina.edu", password="Passw0rd1",
            role="teacher", student_id="T20269999",
        )
        assert r.role == "teacher"
        assert r.student_id == "T20269999"

    def test_bad_role_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(name="x", email="c@lumina.edu", password="Passw0rd1", role="root")


class TestNotificationSchemas:
    """通知 schema 校验"""

    def test_notification_out_required(self):
        n = NotificationOut(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            type="welcome",
            title="欢迎",
            is_read=False,
            created_at="2026-08-31T12:00:00+08:00",
        )
        assert n.is_read is False
        assert n.ref_type is None

    def test_notification_out_from_orm(self):
        """model_validate 可直接序列化 ORM"""
        n = Notification(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            type="live_call", title="点名",
            is_read=False,
            created_at="2026-08-31T12:00:00+08:00",
        )
        out = NotificationOut.model_validate(n)
        assert out.type == "live_call"
        assert out.is_read is False

    def test_unread_count_out(self):
        c = UnreadCountOut(unread_count=3)
        assert c.unread_count == 3


class TestOpenAPI:
    """OpenAPI 注册回归"""

    def test_register_and_notif_paths_registered(self):
        spec = app.openapi()
        paths = spec["paths"]
        assert "/api/v1/auth/register" in paths
        for p in (
            "/api/v1/notifications/my",
            "/api/v1/notifications/my/unread-count",
            "/api/v1/notifications/my/read-all",
            "/api/v1/notifications/my/{notification_id}/read",
        ):
            assert p in paths, f"缺少路径 {p}"