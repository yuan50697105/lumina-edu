# ============================================
# Lumina 墨光 · 结构化 JSON 日志组件 (JSONLines)
# 任一行接入：
#   logger = logging.getLogger("lumina.user")
#   logger.handlers[0].setFormatter(JsonFormatter())
# 或根日志：install_json_logging()
# ============================================
import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    """JSON Lines 格式化器，每行一个 JSON 对象。

    标准字段 + 常用扩展：
      ts, level, logger, message, module, func, line, thread,
      request_id（额外字段）, traceback（异常时）
    自定义额外字段（request_id, user_id, service 等）会展开到 JSON 顶层。
    """

    # logging.LogRecord 标准属性，不展开到 JSON
    STANDARD_ATTRS = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created",
        "msecs", "relativeCreated", "thread", "threadName", "processName",
        "process", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
        }
        # 自定义/额外字段（request_id, user_id, service 等）
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in self.STANDARD_ATTRS or key in base:
                continue
            base[key] = value
        # 异常堆栈
        if record.exc_info:
            base["traceback"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False, default=str)


def install_json_logging(level: int = logging.INFO) -> None:
    """把根日志的所有 handler 替换为 JSONLines 格式，并确保有 handler"""
    logging.basicConfig(level=level, stream=sys.stdout, force=True)
    root = logging.getLogger()
    for handler in root.handlers:
        handler.setFormatter(JsonFormatter())


__all__ = ["JsonFormatter", "install_json_logging"]