# ============================================
# Lumina 墨光 · 管理端（D-07/D-08）单元测试
# 课程审批 / 系统设置 / 审计日志 / 内容举报 / 监控大盘
# 表结构 / schema 校验 / OpenAPI 注册
# 纯内存断言，不连数据库
# ============================================
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from app.database import Base
from app.models import (
    AuditLog,
    ContentReport,
    CourseApproval,
    SystemSetting,
)
from app.schemas import (
    AuditLogOut,
    CourseApprovalOut,
    CourseApprovalReview,
    CourseApprovalStatusOut,
    CourseApprovalSubmit,
    DashboardGrowth,
    DashboardHealth,
    DashboardOverview,
    DashboardRecentActivity,
    GrowthPoint,
    HealthMetric,
    RecentActivityItem,
    ReportCreate,
    ReportOut,
    ReportResolve,
    SettingBatchIn,
    SettingBatchItem,
    SettingCategoryOut,
    SettingOut,
    SettingUpdate,
)


@pytest.fixture(scope="module")
def tables():
    return set(Base.metadata.tables.keys())


# ───────────────────────────────────────────────────────────────
# 表定义
# ───────────────────────────────────────────────────────────────
class TestD07TableDefinitions:

    def test_tables_exist(self, tables):
        required = {
            "course_approvals",
            "system_settings",
            "audit_logs",
            "content_reports",
        }
        assert required.issubset(tables)

    def test_course_approval_columns(self):
        mapper = inspect(CourseApproval)
        cols = {c.key for c in mapper.columns}
        assert {"id", "course_id", "submitted_by", "reviewer_id",
                "status", "comment", "submitted_at", "reviewed_at"}.issubset(cols)
        # 状态默认 pending
        assert mapper.columns["status"].default.arg == "pending"

    def test_system_setting_columns(self):
        mapper = inspect(SystemSetting)
        cols = {c.key for c in mapper.columns}
        assert {"id", "key", "value", "category", "description",
                "updated_by", "created_at", "updated_at"}.issubset(cols)
        assert mapper.columns["category"].default.arg == "general"

    def test_audit_log_columns(self):
        mapper = inspect(AuditLog)
        cols = {c.key for c in mapper.columns}
        assert {"id", "actor_id", "action", "target_type", "target_id",
                "details", "ip_address", "user_agent", "status",
                "archived", "created_at"}.issubset(cols)
        # id 为 BIGINT 自增
        assert str(mapper.columns["id"].type).startswith("BIGINT")
        # archived 默认 False
        assert mapper.columns["archived"].default.arg is False
        # status 默认 success
        assert mapper.columns["status"].default.arg == "success"

    def test_content_report_columns(self):
        mapper = inspect(ContentReport)
        cols = {c.key for c in mapper.columns}
        assert {"id", "reporter_id", "target_type", "target_id", "reason",
                "description", "status", "reviewer_id", "resolution",
                "created_at", "reviewed_at"}.issubset(cols)
        assert mapper.columns["status"].default.arg == "pending"
        assert mapper.columns["reason"].default.arg == "other"


# ───────────────────────────────────────────────────────────────
# Schema 校验
# ───────────────────────────────────────────────────────────────
class TestD07Schemas:

    # 课程审批
    def test_approval_submit_defaults(self):
        s = CourseApprovalSubmit()
        assert s.note is None

    def test_approval_submit_note_maxlen(self):
        with pytest.raises(ValidationError):
            CourseApprovalSubmit(note="x" * 501)

    def test_approval_review_comment_maxlen(self):
        with pytest.raises(ValidationError):
            CourseApprovalReview(comment="x" * 1001)

    def test_approval_out_required_fields(self):
        now = datetime.now(timezone.utc)
        out = CourseApprovalOut(
            id=uuid.uuid4(),
            course_id=uuid.uuid4(),
            submitted_by=uuid.uuid4(),
            status="pending",
            submitted_at=now,
        )
        assert out.status == "pending"
        assert out.reviewer_id is None
        assert out.reviewed_at is None

    def test_approval_status_out(self):
        cid = uuid.uuid4()
        s = CourseApprovalStatusOut(course_id=cid, has_approval=False)
        assert s.has_approval is False
        assert s.status is None

    # 系统设置
    def test_setting_update_value_any(self):
        u = SettingUpdate(value="hello")
        assert u.value == "hello"
        u2 = SettingUpdate(value=42, description="number")
        assert u2.value == 42
        u3 = SettingUpdate(value={"nested": [1, 2, 3]})
        assert u3.value == {"nested": [1, 2, 3]}

    def test_setting_batch_min_one(self):
        with pytest.raises(ValidationError):
            SettingBatchIn(items=[])
        b = SettingBatchIn(items=[SettingBatchItem(key="k", value="v")])
        assert len(b.items) == 1

    def test_setting_batch_max_100(self):
        with pytest.raises(ValidationError):
            SettingBatchIn(items=[SettingBatchItem(key=f"k{i}", value=i) for i in range(101)])

    def test_setting_out_fields(self):
        now = datetime.now(timezone.utc)
        out = SettingOut(key="site_name", value="Lumina", category="general", updated_at=now)
        assert out.category == "general"
        assert out.description is None

    def test_setting_category_out(self):
        c = SettingCategoryOut(category="general", count=2, keys=["k1", "k2"])
        assert c.count == 2

    # 审计日志
    def test_audit_log_out(self):
        now = datetime.now(timezone.utc)
        out = AuditLogOut(
            id=1, action="course.approve",
            status="success", archived=False, created_at=now,
        )
        assert out.id == 1
        assert out.archived is False

    def test_audit_log_details_dict(self):
        now = datetime.now(timezone.utc)
        out = AuditLogOut(
            id=2, action="setting.update",
            details={"key": "site_name", "value": "new"},
            status="success", archived=False, created_at=now,
        )
        assert out.details["key"] == "site_name"

    # 内容举报
    def test_report_create_valid(self):
        tid = uuid.uuid4()
        r = ReportCreate(target_type="discussion", target_id=tid, reason="spam")
        assert r.target_type == "discussion"
        assert r.reason == "spam"

    def test_report_create_invalid_target_type(self):
        tid = uuid.uuid4()
        with pytest.raises(ValidationError):
            ReportCreate(target_type="invalid_type", target_id=tid)

    def test_report_create_invalid_reason(self):
        tid = uuid.uuid4()
        with pytest.raises(ValidationError):
            ReportCreate(target_type="discussion", target_id=tid, reason="nope")

    def test_report_create_all_target_types(self):
        for t in ["discussion", "announcement", "file", "message", "course", "user"]:
            ReportCreate(target_type=t, target_id=uuid.uuid4())

    def test_report_create_all_reasons(self):
        for r in ["spam", "abuse", "harassment", "copyright", "nsfw", "other"]:
            ReportCreate(target_type="discussion", target_id=uuid.uuid4(), reason=r)

    def test_report_create_description_maxlen(self):
        with pytest.raises(ValidationError):
            ReportCreate(
                target_type="discussion", target_id=uuid.uuid4(),
                description="x" * 1001,
            )

    def test_report_resolve_status(self):
        r = ReportResolve(status="resolved", resolution="已处理")
        assert r.status == "resolved"
        with pytest.raises(ValidationError):
            ReportResolve(status="invalid")

    def test_report_resolve_resolution_maxlen(self):
        with pytest.raises(ValidationError):
            ReportResolve(status="resolved", resolution="x" * 1001)

    def test_report_out(self):
        now = datetime.now(timezone.utc)
        out = ReportOut(
            id=uuid.uuid4(), reporter_id=uuid.uuid4(),
            target_type="discussion", target_id=uuid.uuid4(),
            reason="spam", status="pending", created_at=now,
        )
        assert out.status == "pending"
        assert out.reason == "spam"

    # 监控大盘
    def test_dashboard_overview_defaults(self):
        o = DashboardOverview(
            total_users=0, total_students=0, total_teachers=0,
            total_courses=0, active_courses=0,
            dau=0, mau=0, pending_approvals=0, pending_reports=0,
            today_registrations=0,
        )
        assert o.total_users == 0
        assert o.dau == 0

    def test_dashboard_growth(self):
        g = DashboardGrowth(
            months=[GrowthPoint(month="2026-09", new_users=10, new_courses=2, active_users=8)],
        )
        assert len(g.months) == 1

    def test_dashboard_health(self):
        h = DashboardHealth(
            metrics=[HealthMetric(name="api", status="healthy")],
            overall_status="healthy",
        )
        assert h.sla_target == 99.9

    def test_dashboard_recent_activity(self):
        items = [RecentActivityItem(
            id=uuid.uuid4(), type="audit", action="course.approve",
            created_at=datetime.now(timezone.utc),
        )]
        ra = DashboardRecentActivity(items=items)
        assert len(ra.items) == 1


# ───────────────────────────────────────────────────────────────
# OpenAPI 注册
# ───────────────────────────────────────────────────────────────
class TestD07OpenAPIRegistration:

    @pytest.fixture(autouse=True)
    def _load_app(self):
        from app.main import app
        self.app = app

    def _paths(self):
        schema = self.app.openapi()
        return schema.get("paths", {})

    def test_admin_dashboard_registered(self):
        paths = self._paths()
        assert "/api/v1/admin/dashboard/overview" in paths
        assert "/api/v1/admin/dashboard/growth" in paths
        assert "/api/v1/admin/dashboard/health" in paths
        assert "/api/v1/admin/dashboard/recent-activity" in paths

    def test_admin_approvals_registered(self):
        paths = self._paths()
        assert "/api/v1/admin/approvals/courses" in paths
        assert "/api/v1/admin/approvals/courses/{approval_id}" in paths
        assert "/api/v1/admin/courses/{course_id}/approval-status" in paths
        assert "/api/v1/admin/courses/{course_id}/submit-for-approval" in paths
        assert "/api/v1/admin/approvals/courses/{approval_id}/approve" in paths
        assert "/api/v1/admin/approvals/courses/{approval_id}/reject" in paths

    def test_admin_reports_registered(self):
        paths = self._paths()
        assert "/api/v1/admin/reports" in paths
        assert "/api/v1/admin/reports/{report_id}/resolve" in paths

    def test_settings_registered(self):
        paths = self._paths()
        assert "/api/v1/admin/settings" in paths
        assert "/api/v1/admin/settings/categories" in paths
        assert "/api/v1/admin/settings/{key}" in paths
        assert "/api/v1/admin/settings/batch" in paths

    def test_audit_registered(self):
        paths = self._paths()
        assert "/api/v1/admin/audit" in paths
        assert "/api/v1/admin/audit/{log_id}" in paths
        assert "/api/v1/admin/audit/export" in paths
        assert "/api/v1/admin/audit/archive" in paths

    def test_total_count_increases(self):
        schema = self.app.openapi()
        paths_count = len(schema["paths"])
        ops_count = sum(len(m) for m in schema["paths"].values())
        # D-05 基线 121 paths / 158 ops → D-07 新增 20 paths / 22 ops
        assert paths_count >= 140, f"预期 >=140 路径，实际 {paths_count}"
        assert ops_count >= 175, f"预期 >=175 操作，实际 {ops_count}"
