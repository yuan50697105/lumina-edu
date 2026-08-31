# ============================================
# Lumina 墨光 · 协作工具模块单元测试（V1.1 · D-02）
# 表结构 / 唯一约束 / schema 校验 / openapi 注册
# 纯内存断言，不连数据库
# ============================================
import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from app.database import Base
from app.main import app
from app.models import (
    CollabProject,
    DiscussionReply,
    DiscussionTopic,
    GroupMember,
    KanbanCard,
    KanbanColumn,
    ProjectGroup,
    SharedFile,
)
from app.schemas import (
    CardCreate,
    CardUpdate,
    ColumnCreate,
    GroupCreate,
    ReplyIn,
    TopicCreate,
)


@pytest.fixture(scope="module")
def tables():
    """获取所有表名"""
    return set(Base.metadata.tables.keys())


class TestTableDefinitions:
    """协作表定义测试"""

    def test_all_collab_tables_exist(self, tables):
        """8 张协作表已定义"""
        expected = {
            "project_groups",
            "group_members",
            "projects",
            "kanban_columns",
            "kanban_cards",
            "shared_files",
            "discussion_topics",
            "discussion_replies",
        }
        assert expected.issubset(tables), f"缺少表: {expected - tables}"

    def test_group_columns(self):
        """project_groups 必要字段"""
        mapper = inspect(ProjectGroup)
        columns = {c.key for c in mapper.columns}
        required = {"id", "course_id", "name", "leader_id", "created_by", "created_at"}
        assert required.issubset(columns)

    def test_group_member_unique_constraint(self):
        """group_members 唯一约束（group+user）"""
        unique = {uc.name for uc in GroupMember.__table__.constraints if getattr(uc, "name", None)}
        assert "uq_group_member" in unique

    def test_project_columns(self):
        """projects 必要字段与状态枚举"""
        mapper = inspect(CollabProject)
        columns = {c.key for c in mapper.columns}
        required = {"id", "group_id", "course_id", "title", "status", "created_by", "created_at"}
        assert required.issubset(columns)

    def test_kanban_card_columns(self):
        """kanban_cards 支持换列/排位"""
        mapper = inspect(KanbanCard)
        columns = {c.key for c in mapper.columns}
        required = {"id", "column_id", "title", "assignee_id", "order_num", "due_date"}
        assert required.issubset(columns)

    def test_file_columns(self):
        """shared_files 元数据"""
        mapper = inspect(SharedFile)
        columns = {c.key for c in mapper.columns}
        required = {"id", "group_id", "uploader_id", "filename", "size", "content_type"}
        assert required.issubset(columns)

    def test_discussion_reply_fk(self):
        """discussion_replies 外键指向 discussion_topics"""
        fks = {fk.target_fullname for fk in DiscussionReply.__table__.foreign_keys}
        assert "discussion_topics.id" in fks


class TestSchemaValidation:
    """协作 schema 校验"""

    def test_group_requires_name(self):
        with pytest.raises(ValidationError):
            GroupCreate()

    def test_column_requires_title(self):
        with pytest.raises(ValidationError):
            ColumnCreate()

    def test_card_requires_title(self):
        with pytest.raises(ValidationError):
            CardCreate()

    def test_topic_requires_title(self):
        with pytest.raises(ValidationError):
            TopicCreate()

    def test_reply_requires_content(self):
        with pytest.raises(ValidationError):
            ReplyIn()

    def test_group_create_with_leader(self):
        g = GroupCreate(name="第 3 组", leader_id=uuid.uuid4())
        assert g.leader_id is not None

    def test_card_move_via_update(self):
        """拖拽换列通过 CardUpdate.column_id 表达"""
        c = CardUpdate(title="改标题", column_id=uuid.uuid4(), order_num=2)
        assert c.column_id is not None and c.order_num == 2


class TestOpenApiRegistration:
    """协作端点 openapi 注册"""

    def test_collab_paths_registered(self):
        """17 条协作路径 / 27 个操作已注册"""
        paths = app.openapi()["paths"]
        collab_paths = [p for p in paths if any(k in p for k in ("/groups", "/projects", "/columns", "/cards", "/topics", "/files"))]
        assert len(collab_paths) == 17
        ops = sum(len([m for m in paths[p] if m in ("get", "post", "patch", "delete", "put")]) for p in collab_paths)
        assert ops == 27, f"协作端点应为 27，实际 {ops}"

    def test_group_manage_endpoints(self):
        """小组 CRUD + 成员接口齐备"""
        paths = app.openapi()["paths"]
        assert "/api/v1/courses/{course_id}/groups" in paths
        assert "/api/v1/groups/{group_id}" in paths
        assert "/api/v1/groups/{group_id}/members" in paths