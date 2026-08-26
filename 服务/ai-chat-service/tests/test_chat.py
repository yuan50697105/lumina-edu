# ============================================
# Lumina 墨光 · AI 对话服务单元测试
# 纯逻辑：提示词引擎 / Schema 校验 / 网关客户端错误处理
# 无需 PostgreSQL / 无需 AI 网关
# ============================================
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.prompt import (
    SOCRATIC_SYSTEM_PROMPT,
    auto_title,
    build_messages,
    context_paragraph,
)
from app.schemas import ChatRequest


class TestPromptEngine:
    def test_empty_context_no_paragraph(self):
        assert context_paragraph(None) == ""
        assert context_paragraph({}) == ""

    def test_context_paragraph(self):
        p = context_paragraph({"course_id": uuid.uuid4()})
        assert "课程ID" in p
        assert p.endswith("。\n\n")

    def test_build_messages_orders(self):
        history = [
            {"role": "user", "content": "什么是微积分？"},
            {"role": "assistant", "content": "先想想它解决什么问题。"},
        ]
        msgs = build_messages(history, "极限是什么？")
        assert msgs[0]["role"] == "system"
        assert SOCRATIC_SYSTEM_PROMPT in msgs[0]["content"]
        assert msgs[1:] == history + [{"role": "user", "content": "极限是什么？"}]

    def test_build_messages_with_context(self):
        ctx = {"course_id": uuid.uuid4(), "chapter_id": uuid.uuid4()}
        msgs = build_messages([], "为什么", ctx)
        assert "学生当前正在学习" in msgs[0]["content"]
        assert "章节ID" in msgs[0]["content"]

    def test_build_messages_truncates_history(self):
        history = [{"role": "user" if i % 2 == 0 else "assistant",
                    "content": f"消息{i}"} for i in range(50)]
        msgs = build_messages([], "最后一问", max_history=6)
        assert len(msgs) == 2  # system + user，history 为空
        msgs = build_messages(history, "最后一问", max_history=6)
        assert len(msgs) == 1 + 6 + 1
        assert msgs[-1]["content"] == "最后一问"

    def test_auto_title(self):
        assert auto_title("这个问题怎么解") == "这个问题怎么解"
        title = auto_title("A" * 30)
        assert title.endswith("…")
        assert len(title) == 21


class TestChatRequestSchema:
    def test_valid(self):
        req = ChatRequest(message="对不上")
        assert req.context is None

    def test_message_required(self):
        with pytest.raises(Exception):
            ChatRequest(message="")

    def test_max_tokens_bounds(self):
        with pytest.raises(Exception):
            ChatRequest(message="x", max_tokens=10)   # < 64
        with pytest.raises(Exception):
            ChatRequest(message="x", max_tokens=99999)

    def test_context_rejects_invalid_uuid(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ChatRequest(message="x", context={"course_id": "not-a-uuid"})

    def test_context_with_uuid(self):
        cid = uuid.uuid4()
        req = ChatRequest(message="x", context={"course_id": str(cid)})
        assert str(req.context.course_id) == str(cid)