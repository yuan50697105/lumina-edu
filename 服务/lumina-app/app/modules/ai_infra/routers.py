# ============================================
# Lumina 墨光 · D-09 AI 基础设施路由
# RAG 知识库 / Agent 工具调用 / 内容审核
# ============================================
import logging
import math
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, get_current_user, require_role
from app.models import (
    KnowledgeBase, KnowledgeChunk, AgentTool, AgentSession, ModerationLog,
)
from app.schemas import (
    KnowledgeBaseCreate, KnowledgeBaseOut, KnowledgeChunkOut,
    RAGQueryIn, RAGQueryOut, RAGChunkResult,
    AgentToolOut, AgentSessionOut, AgentMessageIn, AgentMessageOut, AgentToolCall,
    ModerationCheckIn, ModerationCheckOut, ModerationLogOut,
)

logger = logging.getLogger("lumina.ai_infra")
router = APIRouter(prefix="/ai-infra", tags=["AI 基础设施（D-09）"])


# ═══════════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════════

def _mock_embed(text: str) -> list[float]:
    """Mock 嵌入向量生成（实际应调用嵌入模型）"""
    # 基于字符哈希生成伪向量（仅用于演示，生产需接真实模型）
    import hashlib
    h = hashlib.md5(text.encode()).hexdigest()
    vec = [(int(h[i:i+2], 16) / 255.0) for i in range(0, 32, 2)]
    # 归一化
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """余弦相似度（Python 侧计算）"""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# 敏感词列表（简化版，生产应使用更完善的词库）
_FORBIDDEN_WORDS = ["暴力", "赌博", "毒品", "枪支", "诈骗"]


def _check_content(text: str) -> tuple[bool, Optional[str], str, float]:
    """内容审核：返回 (flagged, reason, action, confidence)"""
    text_lower = text.lower()
    for word in _FORBIDDEN_WORDS:
        if word in text_lower:
            return True, f"包含敏感词: {word}", "block", 0.95

    # 启发式：过长重复字符
    if len(set(text)) < len(text) * 0.1 and len(text) > 50:
        return True, "疑似垃圾信息（重复字符过多）", "flag", 0.7

    return False, None, "pass", 1.0


# ═══════════════════════════════════════════════════════════════════
# 1. RAG 知识库
# ═══════════════════════════════════════════════════════════════════

@router.get("/knowledge-bases", response_model=list[KnowledgeBaseOut], summary="知识库列表")
def list_knowledge_bases(
    course_id: Optional[str] = Query(None),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取知识库列表"""
    q = db.query(KnowledgeBase)
    if course_id:
        q = q.filter(KnowledgeBase.course_id == course_id)
    return q.order_by(KnowledgeBase.created_at.desc()).all()


@router.post("/knowledge-bases", response_model=KnowledgeBaseOut, status_code=201, summary="创建知识库")
def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新知识库"""
    kb = KnowledgeBase(
        name=payload.name,
        description=payload.description,
        course_id=payload.course_id,
        created_by=user.id,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseOut, summary="知识库详情")
def get_knowledge_base(
    kb_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取知识库详情"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return kb


@router.get("/knowledge-bases/{kb_id}/chunks", response_model=list[KnowledgeChunkOut], summary="知识库分块列表")
def list_chunks(
    kb_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取知识库下的分块"""
    chunks = db.query(KnowledgeChunk).filter(
        KnowledgeChunk.kb_id == kb_id
    ).order_by(KnowledgeChunk.created_at.desc()).offset(offset).limit(limit).all()
    return chunks


@router.post("/knowledge-bases/{kb_id}/chunks", response_model=KnowledgeChunkOut, status_code=201, summary="添加分块")
def add_chunk(
    kb_id: str,
    content: str = Query(..., min_length=1, max_length=10000),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """添加分块并生成嵌入向量（Mock）"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 生成嵌入（Mock）
    embedding = _mock_embed(content)
    token_count = len(content) // 4  # 粗略估算

    chunk = KnowledgeChunk(
        kb_id=kb_id,
        content=content,
        embedding=embedding,
        token_count=token_count,
    )
    db.add(chunk)
    kb.chunk_count = (kb.chunk_count or 0) + 1
    db.commit()
    db.refresh(chunk)
    return chunk


@router.post("/rag/query", response_model=RAGQueryOut, summary="RAG 查询")
def rag_query(
    payload: RAGQueryIn,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """RAG 检索增强生成：检索相关分块 → 增强 prompt → LLM 生成答案"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == payload.kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 1. 生成查询嵌入（Mock）
    query_embedding = _mock_embed(payload.query)

    # 2. 检索最相似的分块（Python 侧计算余弦相似度）
    chunks = db.query(KnowledgeChunk).filter(
        KnowledgeChunk.kb_id == payload.kb_id,
        KnowledgeChunk.embedding.isnot(None),
    ).all()

    scored = []
    for c in chunks:
        if c.embedding:
            score = _cosine_similarity(query_embedding, c.embedding)
            scored.append((c, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_chunks = scored[:payload.top_k]

    sources = [
        RAGChunkResult(
            chunk_id=c.id,
            content=c.content[:200],  # 截断展示
            score=round(s, 4),
            metadata_json=c.metadata_json,
        )
        for c, s in top_chunks
    ]

    # 3. 构建增强 prompt（简化版）
    context = "\n\n".join([c.content for c, _ in top_chunks])
    augmented_prompt = f"""基于以下参考资料回答用户问题：

参考资料：
{context}

用户问题：{payload.query}

请用中文简洁回答："""

    # 4. 调用 LLM 生成答案（Mock，实际应调用 ai_gateway）
    # 这里用简化版返回
    answer = f"根据知识库检索到 {len(top_chunks)} 个相关分块。"
    if top_chunks:
        answer += f"\n\n最相关内容：{top_chunks[0][0].content[:100]}..."
    answer += f"\n\n（注意：此为 D-09 Mock 响应，生产环境将调用 ai_gateway 生成真实答案）"

    total_tokens = sum(c.token_count for c, _ in top_chunks) + len(payload.query) // 4

    return RAGQueryOut(
        query=payload.query,
        answer=answer,
        sources=sources,
        model_used="mock-rag-v1",
        total_tokens=total_tokens,
    )


# ═══════════════════════════════════════════════════════════════════
# 2. Agent 工具调用
# ═══════════════════════════════════════════════════════════════════

@router.get("/agent/tools", response_model=list[AgentToolOut], summary="Agent 工具列表")
def list_agent_tools(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取可用工具列表"""
    tools = db.query(AgentTool).filter(AgentTool.enabled == True).all()

    # 如果数据库没有工具，返回预置工具定义
    if not tools:
        return [
            AgentToolOut(
                id="00000000-0000-0000-0000-000000000001",
                name="get_course_info",
                description="获取课程详情（教师/学生/选课数）",
                parameters_schema={"type": "object", "properties": {"course_id": {"type": "string"}}},
                enabled=True,
            ),
            AgentToolOut(
                id="00000000-0000-0000-0000-000000000002",
                name="search_documents",
                description="在知识库中搜索文档",
                parameters_schema={"type": "object", "properties": {"query": {"type": "string"}, "kb_id": {"type": "string"}}},
                enabled=True,
            ),
            AgentToolOut(
                id="00000000-0000-0000-0000-000000000003",
                name="calculate_grade",
                description="计算学生成绩（GPA/平均分）",
                parameters_schema={"type": "object", "properties": {"student_id": {"type": "string"}}},
                enabled=True,
            ),
        ]
    return tools


@router.get("/agent/sessions", response_model=list[AgentSessionOut], summary="Agent 会话列表")
def list_agent_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的 Agent 会话列表"""
    sessions = db.query(AgentSession).filter(
        AgentSession.user_id == user.id
    ).order_by(AgentSession.updated_at.desc()).offset(offset).limit(limit).all()

    return [
        AgentSessionOut(
            id=s.id, user_id=s.user_id, title=s.title,
            message_count=len(s.messages or []),
            tool_call_count=len(s.tool_calls or []),
            status=s.status, created_at=s.created_at, updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.post("/agent/chat", response_model=AgentMessageOut, summary="Agent 对话（工具调用）")
def agent_chat(
    payload: AgentMessageIn,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Agent 对话：支持多轮工具调用"""
    # 获取或创建会话
    if payload.session_id:
        session = db.query(AgentSession).filter(
            AgentSession.id == payload.session_id,
            AgentSession.user_id == user.id,
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        session = AgentSession(user_id=user.id, messages=[], tool_calls=[])
        db.add(session)
        db.commit()
        db.refresh(session)

    # 添加用户消息
    messages = session.messages or []
    messages.append({"role": "user", "content": payload.message})

    # Mock Agent 响应（实际应调用 ai_gateway 进行多轮工具调用）
    tool_calls = []

    # 简单启发式：如果消息包含"课程"，调用 get_course_info
    if "课程" in payload.message and payload.tools_enabled:
        tool_call = AgentToolCall(
            tool_name="get_course_info",
            parameters={"course_id": "mock-course-id"},
            result={"title": "计算机基础", "teacher": "张老师", "students": 45},
            duration_ms=50,
        )
        tool_calls.append(tool_call)

    # 生成回复
    if tool_calls:
        response = f"我调用了 {len(tool_calls)} 个工具来获取信息。根据工具返回的结果，{tool_calls[0].result}"
    else:
        response = "您好！我是 Lumina AI 助手。请问有什么可以帮助您的？（注意：此为 D-09 Mock 响应）"

    messages.append({"role": "assistant", "content": response})

    # 更新会话
    session.messages = messages
    session.tool_calls = (session.tool_calls or []) + [tc.dict() for tc in tool_calls]
    if not session.title:
        session.title = payload.message[:50]
    db.commit()

    return AgentMessageOut(
        session_id=session.id,
        message=response,
        tool_calls=tool_calls,
        model_used="mock-agent-v1",
        total_tokens=len(payload.message) // 4 + len(response) // 4,
    )


# ═══════════════════════════════════════════════════════════════════
# 3. 内容审核
# ═══════════════════════════════════════════════════════════════════

@router.post("/moderation/check", response_model=ModerationCheckOut, summary="内容审核检查")
def moderation_check(
    payload: ModerationCheckIn,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """检查内容是否违规"""
    flagged, reason, action, confidence = _check_content(payload.content_text)

    # 写入审核日志
    log = ModerationLog(
        user_id=user.id,
        content_type=payload.content_type,
        content_id=payload.content_id,
        content_text=payload.content_text[:1000],  # 截断存储
        flagged=flagged,
        reason=reason,
        action=action,
    )
    db.add(log)
    db.commit()

    return ModerationCheckOut(
        flagged=flagged,
        reason=reason,
        action=action,
        confidence=confidence,
    )


@router.get("/moderation/logs", response_model=list[ModerationLogOut], summary="审核日志列表（管理员）")
def list_moderation_logs(
    content_type: Optional[str] = Query(None),
    flagged_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """获取审核日志（仅管理员）"""
    q = db.query(ModerationLog)
    if content_type:
        q = q.filter(ModerationLog.content_type == content_type)
    if flagged_only:
        q = q.filter(ModerationLog.flagged == True)
    return q.order_by(ModerationLog.created_at.desc()).offset(offset).limit(limit).all()
