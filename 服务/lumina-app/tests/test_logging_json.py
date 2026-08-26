# ============================================
# Lumina 墨光 · JSON 日志格式化单元测试
# JsonFormatter 纯函数测试
# ============================================
import json
import logging
import pytest

from app.logging_json import JsonFormatter


@pytest.fixture
def formatter():
    return JsonFormatter()


@pytest.fixture
def record():
    """创建测试用 LogRecord"""
    rec = logging.LogRecord(
        name="lumina.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="测试消息",
        args=(),
        exc_info=None,
    )
    return rec


class TestJsonFormatter:
    """JsonFormatter 格式化测试"""

    def test_basic_fields(self, formatter, record):
        """基础字段正确"""
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["logger"] == "lumina.test"
        assert data["message"] == "测试消息"
        assert data["module"] == "test"
        assert data["line"] == 42

    def test_has_timestamp(self, formatter, record):
        """包含时间戳"""
        output = formatter.format(record)
        data = json.loads(output)
        assert "ts" in data
        # ISO 格式检查
        assert "T" in data["ts"]

    def test_has_thread(self, formatter, record):
        """包含线程信息"""
        output = formatter.format(record)
        data = json.loads(output)
        assert "thread" in data

    def test_extra_fields(self, formatter):
        """自定义额外字段展开到顶层"""
        rec = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="msg", args=(), exc_info=None,
        )
        rec.request_id = "req-123"
        rec.user_id = "user-456"
        output = formatter.format(rec)
        data = json.loads(output)
        assert data["request_id"] == "req-123"
        assert data["user_id"] == "user-456"

    def test_no_standard_attrs_leak(self, formatter, record):
        """标准属性不泄露到 JSON"""
        output = formatter.format(record)
        data = json.loads(output)
        # 这些标准属性不应出现
        for attr in ["name", "msg", "args", "levelname", "levelno",
                      "pathname", "filename", "exc_info", "lineno",
                      "funcName", "created", "msecs", "process"]:
            assert attr not in data, f"标准属性 {attr} 不应泄露"

    def test_chinese_content(self, formatter):
        """中文内容正确处理"""
        rec = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="用户 %s 登录成功", args=("张三",), exc_info=None,
        )
        output = formatter.format(rec)
        data = json.loads(output)
        assert "张三" in data["message"]

    def test_traceback_on_exception(self, formatter):
        """异常时包含 traceback"""
        try:
            raise ValueError("测试异常")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        rec = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0,
            msg="发生错误", args=(), exc_info=exc_info,
        )
        output = formatter.format(rec)
        data = json.loads(output)
        assert "traceback" in data
        assert "ValueError" in data["traceback"]
        assert "测试异常" in data["traceback"]

    def test_json_lines_format(self, formatter, record):
        """输出是单行 JSON（JSONLines）"""
        output = formatter.format(record)
        # 不应包含换行符（JSON 内部的换行会被转义）
        assert "\n" not in output
        # 能被正确解析
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_ensure_ascii_false(self, formatter):
        """中文不被 ASCII 转义"""
        rec = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="中文消息", args=(), exc_info=None,
        )
        output = formatter.format(rec)
        # 直接包含中文字符，不是 \uXXXX
        assert "中文消息" in output
        assert "\\u" not in output
