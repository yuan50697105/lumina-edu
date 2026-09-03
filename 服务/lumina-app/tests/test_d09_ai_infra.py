# ============================================
# Lumina 墨光 · D-09 AI 基础设施 单元测试
# RAG 知识库 / Agent 工具 / 内容审核
# 表结构 / schema 校验 / OpenAPI 注册 / 工具函数
# ============================================
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from app.database import Base
from app.models import (
    KnowledgeBase, KnowledgeChunk, AgentTool, AgentSession, ModerationLog,
)
from app.schemas import (
    KnowledgeBaseCreate, KnowledgeBaseOut, KnowledgeChunkOut,
    RAGQueryIn, RAGQueryOut, RAGChunkResult,
    AgentToolOut, AgentSessionOut, AgentMessageIn, AgentMessageOut, AgentToolCall,
    ModerationCheckIn, ModerationCheckOut, ModerationLogOut,
)
from app.modules.ai_infra.routers import _mock_embed, _cosine_similarity, _check_content


@pytest.fixture(scope="module")
def tables():
    return set(Base.metadata.tables.keys())


# ───────────────────────────────────────────────────────────────
# D-09 表定义
# ───────────────────────────────────────────────────────────────
class TestD09TableDefinitions:

    def test_tables_exist(self, tables):
        required = {
            "knowledge_bases", "knowledge_chunks",
            "agent_tools", "agent_sessions", "moderation_logs",
        }
        assert required.issubset(tables)

    def test_knowledge_base_columns(self):
        mapper = inspect(KnowledgeBase)
        cols = {c.key for c in mapper.columns}
        assert {"id", "course_id", "name", "description", "chunk_count",
                "embedding_model", "created_by"}.issubset(cols)

    def test_knowledge_chunk_columns(self):
        mapper = inspect(KnowledgeChunk)
        cols = {c.key for c in mapper.columns}
        assert {"id", "kb_id", "content", "metadata_json", "embedding",
                "token_count"}.issubset(cols)

    def test_agent_tool_columns(self):
        mapper = inspect(AgentTool)
        cols = {c.key for c in mapper.columns}
        assert {"id", "name", "description", "parameters_schema", "handler",
                "enabled"}.issubset(cols)
        # name 唯一
        assert mapper.columns["name"].unique

    def test_agent_session_columns(self):
        mapper = inspect(AgentSession)
        cols = {c.key for c in mapper.columns}
        assert {"id", "user_id", "title", "messages", "tool_calls", "status"}.issubset(cols)

    def test_moderation_log_columns(self):
        mapper = inspect(ModerationLog)
        cols = {c.key for c in mapper.columns}
        assert {"id", "user_id", "content_type", "content_id", "content_text",
                "flagged", "reason", "action"}.issubset(cols)


# ───────────────────────────────────────────────────────────────
# D-09 工具函数
# ───────────────────────────────────────────────────────────────
class TestD09UtilityFunctions:

    def test_mock_embed_returns_vector(self):
        vec = _mock_embed("测试文本")
        assert isinstance(vec, list)
        assert len(vec) == 16  # 16 维向量
        # 归一化：L2 范数 ≈ 1
        norm = sum(x * x for x in vec) ** 0.5
        assert abs(norm - 1.0) < 0.01

    def test_mock_embed_deterministic(self):
        v1 = _mock_embed("相同文本")
        v2 = _mock_embed("相同文本")
        assert v1 == v2

    def test_mock_embed_different_inputs(self):
        v1 = _mock_embed("文本 A")
        v2 = _mock_embed("文本 B")
        assert v1 != v2

    def test_cosine_similarity_identical(self):
        vec = [0.5, 0.5, 0.5, 0.5]
        sim = _cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.001

    def test_cosine_similarity_orthogonal(self):
        v1 = [1.0, 0.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0, 0.0]
        sim = _cosine_similarity(v1, v2)
        assert abs(sim) < 0.001

    def test_cosine_similarity_opposite(self):
        v1 = [1.0, 0.0]
        v2 = [-1.0, 0.0]
        sim = _cosine_similarity(v1, v2)
        assert abs(sim + 1.0) < 0.001

    def test_cosine_similarity_zero_vector(self):
        v1 = [0.0, 0.0]
        v2 = [1.0, 0.0]
        sim = _cosine_similarity(v1, v2)
        assert sim == 0.0

    def test_check_content_clean(self):
        flagged, reason, action, conf = _check_content("这是一条正常的消息")
        assert flagged is False
        assert reason is None
        assert action == "pass"
        assert conf == 1.0

    def test_check_content_forbidden_word(self):
        flagged, reason, action, conf = _check_content("包含暴力内容的消息")
        assert flagged is True
        assert reason is not None
        assert "暴力" in reason
        assert action == "block"
        assert conf >= 0.9

    def test_check_content_multiple_forbidden(self):
        for word in ["暴力", "赌博", "毒品", "枪支", "诈骗"]:
            flagged, reason, action, conf = _check_content(f"测试{word}")
            assert flagged is True
            assert word in reason
            assert action == "block"

    def test_check_content_spam_repetitive(self):
        flagged, reason, action, conf = _check_content("a" * 100)
        assert flagged is True
        assert "重复" in reason or "垃圾" in reason
        assert action == "flag"


# ───────────────────────────────────────────────────────────────
# D-09 Schema 校验
# ───────────────────────────────────────────────────────────────
class TestD09Schemas:

    def test_knowledge_base_create(self):
        kb = KnowledgeBaseCreate(name="测试知识库")
        assert kb.name == "测试知识库"
        assert kb.description is None
        assert kb.course_id is None

    def test_knowledge_base_out(self):
        out = KnowledgeBaseOut(
            id=uuid.uuid4(), name="测试",
            chunk_count=10, embedding_model="text-embedding-v3",
            created_at=datetime.now(timezone.utc),
        )
        assert out.chunk_count == 10

    def test_rag_query_in(self):
        q = RAGQueryIn(kb_id=uuid.uuid4(), query="什么是机器学习？")
        assert q.top_k == 5
        assert q.model_name is None

    def test_rag_query_in_top_k_validation(self):
        with pytest.raises(ValidationError):
            RAGQueryIn(kb_id=uuid.uuid4(), query="test", top_k=0)
        with pytest.raises(ValidationError):
            RAGQueryIn(kb_id=uuid.uuid4(), query="test", top_k=25)

    def test_rag_query_out(self):
        out = RAGQueryOut(
            query="test", answer="answer",
            sources=[RAGChunkResult(chunk_id=uuid.uuid4(), content="c", score=0.85)],
            model_used="mock", total_tokens=100,
        )
        assert len(out.sources) == 1
        assert out.sources[0].score == 0.85

    def test_agent_tool_out(self):
        out = AgentToolOut(
            id=uuid.uuid4(), name="get_course",
            description="获取课程",
            parameters_schema={"type": "object"},
            enabled=True,
        )
        assert out.enabled is True

    def test_agent_message_in(self):
        msg = AgentMessageIn(message="帮我查课程")
        assert msg.tools_enabled is True
        assert msg.session_id is None

    def test_agent_message_out(self):
        out = AgentMessageOut(
            session_id=uuid.uuid4(), message="回复",
            tool_calls=[AgentToolCall(
                tool_name="test", parameters={},
                result={"ok": True}, duration_ms=50,
            )],
            model_used="mock", total_tokens=50,
        )
        assert len(out.tool_calls) == 1

    def test_moderation_check_in(self):
        c = ModerationCheckIn(content_type="chat", content_text="正常消息")
        assert c.content_type == "chat"

    def test_moderation_check_in_invalid_type(self):
        with pytest.raises(ValidationError):
            ModerationCheckIn(content_type="invalid", content_text="test")

    def test_moderation_check_out(self):
        out = ModerationCheckOut(flagged=True, reason="敏感词", action="block", confidence=0.95)
        assert out.flagged is True
        assert out.confidence == 0.95


# ───────────────────────────────────────────────────────────────
# OpenAPI 注册
# ───────────────────────────────────────────────────────────────
class TestD09OpenAPIRegistration:

    @pytest.fixture(autouse=True)
    def _load_app(self):
        from app.main import app
        self.app = app

    def _paths(self):
        schema = self.app.openapi()
        return schema.get("paths", {})

    def test_knowledge_bases_registered(self):
        paths = self._paths()
        assert "/api/v1/ai-infra/knowledge-bases" in paths
        assert "/api/v1/ai-infra/knowledge-bases/{kb_id}" in paths
        assert "/api/v1/ai-infra/knowledge-bases/{kb_id}/chunks" in paths

    def test_rag_query_registered(self):
        paths = self._paths()
        assert "/api/v1/ai-infra/rag/query" in paths

    def test_agent_tools_registered(self):
        paths = self._paths()
        assert "/api/v1/ai-infra/agent/tools" in paths
        assert "/api/v1/ai-infra/agent/sessions" in paths
        assert "/api/v1/ai-infra/agent/chat" in paths

    def test_moderation_registered(self):
        paths = self._paths()
        assert "/api/v1/ai-infra/moderation/check" in paths
        assert "/api/v1/ai-infra/moderation/logs" in paths

    def test_total_count(self):
        schema = self.app.openapi()
        paths_count = len(schema["paths"])
        ops_count = sum(len(m) for m in schema["paths"].values())
        # D-06/D-08 基线 162 paths / 201 ops → D-09 新增 9 paths / 11 ops
        assert paths_count >= 170, f"预期 >=170 路径，实际 {paths_count}"
        assert ops_count >= 210, f"预期 >=210 操作，实际 {ops_count}"
