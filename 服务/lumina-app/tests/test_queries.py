# ============================================
# Lumina 墨光 · 日志查询工具单元测试
# 纯函数测试，不碰数据库
# ============================================
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.modules.logs.queries import (
    clamp_limit,
    clamp_offset,
    build_filters,
    parse_user_id,
)


class TestClampLimit:
    """limit 参数钳制测试"""

    def test_none_returns_default(self):
        """None 返回默认值 50"""
        assert clamp_limit(None) == 50

    def test_custom_default(self):
        """自定义默认值"""
        assert clamp_limit(None, default=100) == 100

    def test_normal_value(self):
        """正常值保持不变"""
        assert clamp_limit(100) == 100

    def test_max_cap(self):
        """超过上限被钳制"""
        assert clamp_limit(500) == 200

    def test_min_cap(self):
        """低于下限被钳制"""
        assert clamp_limit(0) == 1
        assert clamp_limit(-5) == 1

    def test_custom_max(self):
        """自定义上限"""
        assert clamp_limit(500, max_limit=1000) == 500


class TestClampOffset:
    """offset 参数钳制测试"""

    def test_none_returns_zero(self):
        """None 返回 0"""
        assert clamp_offset(None) == 0

    def test_zero_returns_zero(self):
        """0 返回 0"""
        assert clamp_offset(0) == 0

    def test_normal_value(self):
        """正常值保持不变"""
        assert clamp_offset(50) == 50

    def test_negative_returns_zero(self):
        """负数返回 0"""
        assert clamp_offset(-10) == 0


class TestParseUserId:
    """user_id 解析测试"""

    def test_valid_uuid(self):
        """有效 UUID 返回正确值"""
        uid = str(uuid.uuid4())
        result = parse_user_id(uid)
        assert result is not None
        assert str(result) == uid

    def test_none_returns_none(self):
        """None 返回 None"""
        assert parse_user_id(None) is None

    def test_empty_string_returns_none(self):
        """空字符串返回 None"""
        assert parse_user_id("") is None

    def test_invalid_returns_none(self):
        """非法格式返回 None"""
        assert parse_user_id("not-a-uuid") is None
        assert parse_user_id("12345") is None


class TestBuildFilters:
    """过滤条件构建测试"""

    def test_basic_filter(self):
        """基础过滤（仅 days）"""
        flt = build_filters(days=7)
        assert flt.since is not None
        assert len(flt.conditions) == 1  # created_at >= since

    def test_method_filter(self):
        """方法过滤"""
        flt = build_filters(days=1, method="GET")
        assert len(flt.conditions) == 2

    def test_method_uppercase(self):
        """方法自动转大写"""
        flt = build_filters(days=1, method="post")
        # 条件中应包含 POST
        assert len(flt.conditions) == 2

    def test_path_filter(self):
        """路径包含过滤"""
        flt = build_filters(days=1, path_contains="/api/users")
        assert len(flt.conditions) == 2

    def test_status_filter(self):
        """状态码过滤"""
        flt = build_filters(days=1, status=404)
        assert len(flt.conditions) == 2

    def test_request_id_filter(self):
        """请求 ID 过滤"""
        flt = build_filters(days=1, request_id="abc-123")
        assert len(flt.conditions) == 2

    def test_user_id_filter(self):
        """用户 ID 过滤"""
        uid = str(uuid.uuid4())
        flt = build_filters(days=1, user_id=uid)
        assert len(flt.conditions) == 2

    def test_invalid_user_id_ignored(self):
        """非法 user_id 被忽略"""
        flt = build_filters(days=1, user_id="invalid")
        assert len(flt.conditions) == 1  # 仅 since

    def test_all_filters(self):
        """所有过滤条件组合"""
        flt = build_filters(
            days=30,
            method="GET",
            path_contains="/api",
            status=200,
            request_id="req-123",
            user_id=str(uuid.uuid4()),
        )
        assert len(flt.conditions) == 6

    def test_days_clamped(self):
        """days 参数被钳制在 1-365"""
        flt1 = build_filters(days=0)
        flt2 = build_filters(days=400)
        # 应该都能正常工作，不报错
        assert flt1.since is not None
        assert flt2.since is not None
