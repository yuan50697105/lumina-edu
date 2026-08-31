# ============================================
# Lumina 墨光 · 数据模型单元测试
# 表结构 / 字段定义 / 关系映射
# ============================================
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect, create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import (
    User, UserBrief, Course, CourseBrief, Session as SessionModel,
    Enrollment, Chapter, Announcement, Assignment, Submission,
    GradeRecord, APILog, EventTracking,
    AICallLog, AIConversation, AIMessage, AIModel, AIProvider,
)


@pytest.fixture(scope="module")
def tables():
    """获取所有表名"""
    return set(Base.metadata.tables.keys())


class TestTableDefinitions:
    """表定义测试"""

    def test_all_tables_exist(self, tables):
        """所有 22 张表已定义"""
        expected = {
            "users", "sessions", "courses", "enrollments", "chapters",
            "announcements", "assignments", "submissions", "grade_records",
            "api_logs", "event_tracking",
            "ai_call_logs", "ai_conversations", "ai_messages",
            "ai_models", "ai_providers", "grades",
            "live_rooms", "live_attendees", "live_messages",
            "live_quizzes", "live_quiz_answers",
        }
        assert expected.issubset(tables), f"缺少表: {expected - tables}"

    def test_table_count(self, tables):
        """表数量为 22（17 业务 + 5 直播 V1.1）"""
        assert len(tables) == 22


class TestUserModel:
    """用户模型测试"""

    def test_tablename(self):
        """表名正确"""
        assert User.__tablename__ == "users"

    def test_has_required_columns(self):
        """包含必要字段"""
        mapper = inspect(User)
        columns = {c.key for c in mapper.columns}
        required = {"id", "student_id", "name", "email", "password_hash", "role"}
        assert required.issubset(columns)

    def test_user_brief_same_table(self):
        """UserBrief 映射到同一张表"""
        assert UserBrief.__tablename__ == "users"


class TestCourseModel:
    """课程模型测试"""

    def test_tablename(self):
        assert Course.__tablename__ == "courses"

    def test_has_required_columns(self):
        mapper = inspect(Course)
        columns = {c.key for c in mapper.columns}
        required = {"id", "code", "title", "teacher_id", "semester", "status"}
        assert required.issubset(columns)

    def test_course_brief_same_table(self):
        """CourseBrief 映射到同一张表"""
        assert CourseBrief.__tablename__ == "courses"


class TestAssignmentModel:
    """作业模型测试"""

    def test_tablename(self):
        assert Assignment.__tablename__ == "assignments"

    def test_has_ai_fields(self):
        """包含 AI 批阅字段"""
        mapper = inspect(Assignment)
        columns = {c.key for c in mapper.columns}
        assert "ai_grading" in columns
        assert "rubric" in columns


class TestAIModels:
    """AI 模型测试"""

    def test_ai_conversations_table(self):
        """AI 会话表"""
        assert AIConversation.__tablename__ == "ai_conversations"

    def test_ai_messages_table(self):
        """AI 消息表"""
        assert AIMessage.__tablename__ == "ai_messages"

    def test_ai_models_table(self):
        """AI 模型配置表"""
        assert AIModel.__tablename__ == "ai_models"

    def test_ai_providers_table(self):
        """AI 供应商表"""
        assert AIProvider.__tablename__ == "ai_providers"


class TestMonitoringModels:
    """监控模型测试"""

    def test_api_log_table(self):
        """API 日志表"""
        assert APILog.__tablename__ == "api_logs"
        mapper = inspect(APILog)
        columns = {c.key for c in mapper.columns}
        assert "method" in columns
        assert "path" in columns
        assert "duration_ms" in columns

    def test_event_tracking_table(self):
        """事件追踪表"""
        assert EventTracking.__tablename__ == "event_tracking"
        mapper = inspect(EventTracking)
        columns = {c.key for c in mapper.columns}
        assert "event_name" in columns
        assert "properties" in columns
