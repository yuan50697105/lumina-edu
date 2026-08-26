# ============================================
# Lumina 墨光 · AI 对话服务路由
# /ai/chat SSE 流式对话 · /ai/conversations 历史
# ============================================
import json
import time as _t
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .database import get_db
from .dependencies import AuthUser, get_current_user
from .gateway_client import GatewayError, route_model, stream_completions
from .instrumentation import (
    EVENT_CHAT_DONE,
    EVENT_CHAT_ERROR,
    EVENT_CHAT_START,
    EVENT_CONV_DELETE,
    EVENT_CONV_LIST,
    EVENT_CONV_VIEW,
    Instrumentation,
    Timer,
)
from .models import AIConversation, AIMessage
from .prompt import auto_title, build_messages
from .schemas import ChatRequest, ConversationOut, MessageOut, SuccessResponse

router = APIRouter(prefix="/ai", tags=["AI 对话"])


# ─── 工具 ───
def _get_owned_conversation(db: Session, conv_id: uuid.UUID, user: AuthUser) -> AIConversation:
    conv = db.get(AIConversation, conv_id)
    if not conv or str(conv.user_id) != str(user.id):
        raise HTTPException(status_code=404, detail="对话不存在")
    return conv


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


# ─── SSE 流式对话 ───
@router.post("/chat", summary="AI 对话（苏格拉底导师，SSE 流式）")
def chat(
    payload: ChatRequest,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """流式对话。请求体见 ChatRequest；模型可用 X-Model 头或 model_name 指定，缺省智能路由。"""
    user_token = request.headers.get("authorization", "")
    if not user_token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少访问令牌")

    # ── 会话：新建 or 续聊 ──
    if payload.conversation_id:
        conv = _get_owned_conversation(db, payload.conversation_id, user)
        history = [
            {"role": m.role, "content": m.content or ""}
            for m in db.query(AIMessage)
            .filter(AIMessage.conversation_id == conv.id)
            .order_by(AIMessage.created_at)
            .all()
            if m.role in ("user", "assistant")
        ]
    else:
        conv = None
        history = []

    # ── 模型：指定 or 智能路由 ──
    model_name = payload.model_name or request.headers.get("x-model")
    if not model_name:
        try:
            model_name = route_model(user_token, "chat")
        except GatewayError as e:
            raise HTTPException(status_code=400, detail=str(e))

    if not conv:
        conv = AIConversation(
            user_id=user.id,
            title=auto_title(payload.message),
            model=model_name,
            context_course_id=payload.context.course_id if payload.context else None,
            context_chapter_id=payload.context.chapter_id if payload.context else None,
        )
        db.add(conv)
        db.flush()

    # 保存用户消息（流式过程中后端逐一落库）
    attachments = None
    ctx_dict = None
    if payload.context:
        ctx_dict = payload.context.model_dump(exclude_none=True)
    if payload.attachments:
        attachments = [a for a in payload.attachments if isinstance(a, dict)]

    db.add(AIMessage(
        conversation_id=conv.id, role="user", content=payload.message,
        attachments=attachments,
    ))
    db.commit()

    messages = build_messages(history, payload.message, ctx_dict)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_CHAT_START, properties={
            "conversation_id": str(conv.id), "model": model_name,
            "course_id": str(conv.context_course_id) if conv.context_course_id else None,
            "message_len": len(payload.message),
        }
    )

    def gen():
        with Timer() as timer:
            pieces: list[str] = []
            prompt_tokens = completion_tokens = 0
            errored = False
            try:
                for event in stream_completions(model_name, messages, user_token,
                                                payload.max_tokens):
                    ev_type = event.get("type")
                    if ev_type == "token":
                        pieces.append(event.get("content") or "")
                        yield _sse(event)
                    elif ev_type == "error":
                        errored = True
                        yield _sse(event)
                        break
                    elif ev_type == "done":
                        usage = event.get("usage") or {}
                        prompt_tokens = int(usage.get("prompt_tokens") or 0)
                        completion_tokens = int(usage.get("completion_tokens") or 0)
                        yield _sse({
                            "type": "done",
                            "conversation_id": str(conv.id),
                            "model": model_name,
                            "usage": {"prompt_tokens": prompt_tokens,
                                      "completion_tokens": completion_tokens},
                        })
            except GatewayError as e:
                errored = True
                yield _sse({"type": "error", "message": str(e)})

            if not errored:
                db.flush()
            # ── 落库：助手回复 + 会话计数 ──
            db.add(AIMessage(
                conversation_id=conv.id, role="assistant",
                content="".join(pieces),
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                latency_ms=timer.duration_ms,
            ))
            conv.message_count = (conv.message_count or 0) + 2
            conv.total_tokens = (conv.total_tokens or 0) + prompt_tokens + completion_tokens
            db.commit()

            if errored:
                Instrumentation(db, request, str(user.id)).track(
                    EVENT_CHAT_ERROR, properties={
                        "conversation_id": str(conv.id), "model": model_name,
                        "tokens": prompt_tokens + completion_tokens,
                    }
                )
            else:
                Instrumentation(db, request, str(user.id)).track(
                    EVENT_CHAT_DONE, properties={
                        "conversation_id": str(conv.id), "model": model_name,
                        "tokens": prompt_tokens + completion_tokens,
                        "latency_ms": timer.duration_ms,
                        "message_len": len(payload.message),
                        "course_id": str(conv.context_course_id) if conv.context_course_id else None,
                    }
                )

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── 对话历史 ───
@router.get("/conversations", response_model=list[ConversationOut], summary="对话历史列表")
def list_conversations(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20,
    course_id: uuid.UUID | None = None,
):
    query = db.query(AIConversation).filter(AIConversation.user_id == user.id)
    if course_id:
        query = query.filter(AIConversation.context_course_id == course_id)
    convs = query.order_by(AIConversation.updated_at.desc()).limit(min(limit, 100)).all()
    Instrumentation(db, request, str(user.id)).track(
        EVENT_CONV_LIST, properties={"count": len(convs)}
    )
    return convs


@router.get("/conversations/{conversation_id}", response_model=list[MessageOut], summary="会话消息详情")
def conversation_messages(
    conversation_id: uuid.UUID,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = _get_owned_conversation(db, conversation_id, user)
    msgs = (
        db.query(AIMessage)
        .filter(AIMessage.conversation_id == conv.id)
        .order_by(AIMessage.created_at)
        .all()
    )
    Instrumentation(db, request, str(user.id)).track(
        EVENT_CONV_VIEW, properties={"conversation_id": str(conv.id), "count": len(msgs)}
    )
    return msgs


@router.delete("/conversations/{conversation_id}", response_model=SuccessResponse, summary="删除会话")
def delete_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = _get_owned_conversation(db, conversation_id, user)
    db.delete(conv)  # 消息级联删除
    db.commit()
    Instrumentation(db, request, str(user.id)).track(
        EVENT_CONV_DELETE, properties={"conversation_id": str(conversation_id)}
    )
    return SuccessResponse()