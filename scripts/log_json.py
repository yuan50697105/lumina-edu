#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================
# Lumina 墨光 · 结构化 JSON 日志演示
# --------------------------------------------
# 使用方式：
#   1) 在任意 FastAPI 服务中复制 服务/logs-service/app/logging_json.py
#   2) main.py 一行接入：
#         from logging_json import install_json_logging
#         install_json_logging()          # stdio 输出 JSONLines
#      或仅替换现有 handler 格式：
#         logger.handlers[0].setFormatter(JsonFormatter())
#   3) 自定义字段用 extra 传递（request_id / user_id / service 等）
# ============================================
import logging
import os
import sys

# 便于演示直接引用 logs-service 的组件（正式部署时复制到各服务）
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "服务", "logs-service", "app",
))

from logging_json import install_json_logging  # noqa: E402

install_json_logging()
logger = logging.getLogger("lumina.demo")

logger.info("演示：正常日志", extra={"service": "demo", "method": "GET", "path": "/api/v1/courses"})

try:
    raise ValueError("演示：业务异常")
except ValueError:
    logger.error(
        "演示：错误日志（含堆栈）",
        extra={"service": "demo", "request_id": "REQ-DEMO-001", "user_id": "u-001"},
        exc_info=True,
    )

print("──── 共输出 2 行 JSONLines，直接管道给 logstash/filebeat 等即可 ────")