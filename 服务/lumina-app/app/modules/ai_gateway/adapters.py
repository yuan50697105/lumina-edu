# ============================================
# Lumina 墨光 · AI 协议适配层
# 统一内部消息 -> 各厂商格式（OpenAI / Anthropic / Gemini）
# 各厂商响应 -> 统一结构（content + 用量）
# ============================================
import json
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

import httpx

# ─── 协议风格常量 ───
STYLE_OPENAI = "openai"
STYLE_ANTHROPIC = "anthropic"
STYLE_GEMINI = "gemini"

SUPPORTED_STYLES = {STYLE_OPENAI, STYLE_ANTHROPIC, STYLE_GEMINI}

DEFAULT_TIMEOUT = 120.0


class ProviderError(Exception):
    """供应商调用异常"""


@dataclass
class ChatResult:
    """统一模型输出"""
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: Optional[str] = None
    model: Optional[str] = None
    raw: dict = field(default_factory=dict)


def validate_messages(messages: list[dict]) -> list[dict]:
    """校验统一消息格式 [{role: system|user|assistant, content: str}]"""
    allowed = {"system", "user", "assistant"}
    out = []
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if role not in allowed or not isinstance(content, str):
            raise ProviderError(f"消息格式错误: {m}")
        out.append({"role": role, "content": content})
    return out


def _system_and_messages(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """拆分 system 提示与对话消息（Anthropic/Gemini 体系分离 system）"""
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system") or None
    chat = [m for m in messages if m["role"] != "system"]
    return system, chat


# ─── 请求构造 ───
def build_request(
    style: str,
    base_url: str,
    model: str,
    messages: list[dict],
    *,
    max_tokens: int = 4096,
    stream: bool = False,
) -> tuple[str, str, dict, dict | None]:
    """返回 (method, url, headers, body)"""
    messages = validate_messages(messages)

    if style == STYLE_OPENAI:
        url = f"{base_url.rstrip('/')}/chat/completions"
        body = {"model": model, "messages": messages, "stream": stream}
        if max_tokens:
            body["max_tokens"] = max_tokens
        return "POST", url, {}, body

    if style == STYLE_ANTHROPIC:
        url = f"{base_url.rstrip('/')}/v1/messages"
        system, chat = _system_and_messages(messages)
        body: dict[str, Any] = {
            "model": model,
            "messages": chat,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if system:
            body["system"] = system
        return "POST", url, {"content-type": "application/json", "anthropic-version": "2023-06-01"}, body

    if style == STYLE_GEMINI:
        url = f"{base_url.rstrip('/')}/v1beta/models/{model}:generateContent{'?alt=sse' if stream else ''}"
        system, chat = _system_and_messages(messages)
        contents = []
        for m in chat:
            gemini_role = "model" if m["role"] == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": m["content"]}]})
        body: dict[str, Any] = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        return "POST", url, {}, body

    raise ProviderError(f"不支持的协议风格: {style}")


def resolve_headers(provider_name: str, api_key: str, style: str) -> dict:
    """按供应商注入鉴权头"""
    if not api_key:
        raise ProviderError(f"供应商 {provider_name} 未配置 API Key")
    if style == STYLE_ANTHROPIC:
        return {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    if style == STYLE_GEMINI:
        return {"x-goog-api-key": api_key}
    return {"Authorization": f"Bearer {api_key}"}


# ─── 响应解析（非流式）───
def parse_response(style: str, status_code: int, body_json: dict, model: str) -> ChatResult:
    if status_code >= 400:
        err = body_json.get("error") or body_json.get("message") or body_json
        raise ProviderError(f"供应商返回 {status_code}: {err}")

    if style == STYLE_OPENAI:
        choice = (body_json.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content") or ""
        usage = body_json.get("usage") or {}
        return ChatResult(
            content=content,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            finish_reason=choice.get("finish_reason"),
            model=body_json.get("model") or model,
            raw=body_json,
        )

    if style == STYLE_ANTHROPIC:
        blocks = body_json.get("content") or []
        content = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        usage = body_json.get("usage") or {}
        return ChatResult(
            content=content,
            prompt_tokens=int(usage.get("input_tokens") or 0),
            completion_tokens=int(usage.get("output_tokens") or 0),
            finish_reason=body_json.get("stop_reason"),
            model=body_json.get("model") or model,
            raw=body_json,
        )

    if style == STYLE_GEMINI:
        candidates = body_json.get("candidates") or []
        if candidates:
            parts = (candidates[0].get("content") or {}).get("parts") or []
            content = "".join(p.get("text", "") for p in parts if "text" in p)
        else:
            content = ""
        meta = body_json.get("usageMetadata") or {}
        return ChatResult(
            content=content,
            prompt_tokens=int(meta.get("promptTokenCount") or 0),
            completion_tokens=int(meta.get("candidatesTokenCount") or 0),
            finish_reason=(candidates[0] or {}).get("finishReason"),
            model=model,
            raw=body_json,
        )

    raise ProviderError(f"不支持的协议风格: {style}")


# ─── 流式解析（SSE → 统一 token 事件）───
def parse_stream_events(style: str, byte_chunk: bytes, model: str):
    """解析厂商 SSE 字节流，产出统一事件 dict。

    yield: {"type":"token","content": str} | {"type":"usage","prompt_tokens":int,"completion_tokens":int} | {"type":"error","message":str}
    """
    if style == STYLE_OPENAI:
        for line in byte_chunk.decode("utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                continue
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            choice = (obj.get("choices") or [{}])[0]
            delta = (choice.get("delta") or {}).get("content")
            if delta:
                yield {"type": "token", "content": delta}
            usage = obj.get("usage")
            if usage:
                yield {"type": "usage", "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                       "completion_tokens": int(usage.get("completion_tokens") or 0)}

    elif style == STYLE_ANTHROPIC:
        event_type = None
        for line in byte_chunk.decode("utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                try:
                    obj = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                if obj.get("type") == "content_block_delta":
                    delta = (obj.get("delta") or {}).get("text")
                    if delta:
                        yield {"type": "token", "content": delta}
                if obj.get("type") == "message_delta":
                    usage = obj.get("usage")
                    if usage:
                        yield {"type": "usage", "prompt_tokens": int(usage.get("input_tokens") or 0),
                               "completion_tokens": int(usage.get("output_tokens") or 0)}

    elif style == STYLE_GEMINI:
        for line in byte_chunk.decode("utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            candidates = obj.get("candidates") or []
            if candidates:
                parts = (candidates[0].get("content") or {}).get("parts") or []
                text = "".join(p.get("text", "") for p in parts if "text" in p)
                if text:
                    yield {"type": "token", "content": text}
            meta = obj.get("usageMetadata")
            if meta and meta.get("candidatesTokenCount") is not None:
                yield {"type": "usage", "prompt_tokens": int(meta.get("promptTokenCount") or 0),
                       "completion_tokens": int(meta.get("candidatesTokenCount") or 0)}

    else:
        raise ProviderError(f"不支持的协议风格: {style}")


# ─── 统一调用执行 ───
def call_chat(
    style: str,
    base_url: str,
    model: str,
    api_key: str,
    provider_name: str,
    messages: list[dict],
    *,
    max_tokens: int = 4096,
    stream: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
):
    """发起模型调用，返回统一 ChatResult（非流式）"""
    method, url, _h, body = build_request(style, base_url, model, messages,
                                          max_tokens=max_tokens, stream=stream)
    headers = resolve_headers(provider_name, api_key, style)
    headers.setdefault("content-type", "application/json")

    with httpx.Client(timeout=timeout) as client:
        resp = client.request(method, url, headers=headers, json=body)
        try:
            body_json = resp.json()
        except json.JSONDecodeError:
            raise ProviderError(f"供应商响应非 JSON: HTTP {resp.status_code}")
    return parse_response(style, resp.status_code, body_json, model)


def stream_chat(
    style: str,
    base_url: str,
    model: str,
    api_key: str,
    provider_name: str,
    messages: list[dict],
    *,
    max_tokens: int = 4096,
    timeout: float = DEFAULT_TIMEOUT,
) -> Iterator[dict]:
    """发起流式调用，产出统一事件流（token/usage/error）"""
    method, url, _h, body = build_request(style, base_url, model, messages,
                                          max_tokens=max_tokens, stream=True)
    headers = resolve_headers(provider_name, api_key, style)
    headers.setdefault("content-type", "application/json")

    with httpx.Client(timeout=timeout) as client:
        with client.stream(method, url, headers=headers, json=body) as resp:
            if resp.status_code >= 400:
                err_body = resp.read().decode("utf-8", errors="ignore")
                yield {"type": "error", "message": f"供应商返回 {resp.status_code}: {err_body[:200]}"}
                return
            for chunk in resp.iter_raw():
                if not chunk:
                    continue
                try:
                    for event in parse_stream_events(style, chunk, model):
                        yield event
                except ProviderError as e:
                    yield {"type": "error", "message": str(e)}
                    return