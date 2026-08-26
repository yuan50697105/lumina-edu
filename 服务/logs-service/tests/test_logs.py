# ============================================
# Lumina 墨光 · 基础日志系统单元测试
# 过滤构造 / 分页钳制 / JSON 日志格式化
# ============================================
import json
import logging
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.logging_json import JsonFormatter, install_json_logging
from app.queries import (
    build_filters, clamp_limit, clamp_offset, parse_user_id,
)


# ─── 分页钳制 ───
def test_clamp_limit_default():
    assert clamp_limit(None) == 50


def test_clamp_limit_low():
    assert clamp_limit(0) == 1


def test_clamp_limit_high():
    assert clamp_limit(500) == 200


def test_clamp_limit_in_range():
    assert clamp_limit(20) == 20


def test_clamp_offset_negative():
    assert clamp_offset(-5) == 0


def test_clamp_offset_zero():
    assert clamp_offset(None) == 0


# ─── 过滤构造 ───
def test_build_filters_basic():
    flt = build_filters(7, method="get", path_contains="users",
                        status=404, request_id="req-1", user_id=str(uuid.uuid4()))
    assert len(flt.conditions) > 0
    sql = " AND ".join(str(c) for c in flt.conditions)
    assert "api_logs.method" in sql
    assert "api_logs.path" in sql
    assert "api_logs.status_code" in sql
    assert "api_logs.request_id" in sql
    assert "api_logs.user_id" in sql


def test_build_filters_no_optional():
    flt = build_filters(7)
    # 仅时间条件
    assert len(flt.conditions) == 1


def test_build_filters_invalid_user_id():
    """非法 UUID 不构成 user_id 过滤（等价不按用户过滤）"""
    flt = build_filters(7, user_id="not-a-uuid")
    sql = " AND ".join(str(c) for c in flt.conditions)
    assert "user_id" not in sql


def test_build_filters_days_clamp():
    # 两次调用相差毫秒，用秒级精度比较
    assert abs((build_filters(400).since - build_filters(365).since).total_seconds()) < 60
    assert abs((build_filters(0).since - build_filters(1).since).total_seconds()) < 60


def test_parse_user_id():
    uid = uuid.uuid4()
    assert parse_user_id(str(uid)) == uid
    assert parse_user_id("bad-id") is None
    assert parse_user_id(None) is None


# ─── JSON 日志格式化 ───
def _logged(fmt, level=logging.INFO, message="hello lumina", **kwargs):
    rec = logging.LogRecord(
        name="lumina.demo", level=level, pathname="test.py",
        lineno=10, msg=message, args=(), exc_info=None, func="demo",
    )
    for k, v in kwargs.items():
        setattr(rec, k, v)
    return json.loads(fmt.format(rec))


def test_json_formatter_basic():
    out = _logged(JsonFormatter())
    assert out["level"] == "INFO"
    assert out["logger"] == "lumina.demo"
    assert out["message"] == "hello lumina"
    assert out["module"] == "test"
    assert set(out) >= {"ts", "level", "logger", "message", "module", "func", "line", "thread"}


def test_json_formatter_chinese():
    out = _logged(JsonFormatter(), message="墨光日志")
    assert out["message"] == "墨光日志"


def test_json_formatter_extra_request_id():
    out = _logged(JsonFormatter(), request_id="REQ-123")
    assert out["request_id"] == "REQ-123"


def test_json_formatter_traceback():
    fmt = JsonFormatter()
    rec = logging.LogRecord(
        name="lumina.demo", level=logging.ERROR, pathname="test.py",
        lineno=10, msg="boom", args=(), exc_info=(ValueError, ValueError("x"), None),
        func="demo",
    )
    out = json.loads(fmt.format(rec))
    assert out["level"] == "ERROR"
    assert "ValueError" in out["traceback"]


def test_json_formatter_no_standard_dupes():
    """name/levelno/process 等标准属性不应展开到 JSON"""
    out = _logged(JsonFormatter())
    assert "name" not in out
    assert "levelno" not in out
    assert "msg" not in out
    assert "process" not in out