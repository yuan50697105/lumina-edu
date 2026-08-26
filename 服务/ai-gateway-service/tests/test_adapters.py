# ============================================
# Lumina 墨光 · AI 协议适配层单元测试
# 纯逻辑测试：无需 PostgreSQL，mock 三厂商请求/响应格式
# ============================================
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.adapters import (
    STYLE_ANTHROPIC,
    STYLE_GEMINI,
    STYLE_OPENAI,
    ProviderError,
    build_request,
    parse_response,
    parse_stream_events,
    resolve_headers,
)

MSGS = [
    {"role": "system", "content": "你是阅卷助教"},
    {"role": "user", "content": "批改这段作文"},
]


class TestBuildRequest:
    def test_openai_format(self):
        method, url, _h, body = build_request(
            STYLE_OPENAI, "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "qwen-max", MSGS, max_tokens=2048)
        assert method == "POST"
        assert url == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        assert body["model"] == "qwen-max"
        assert body["messages"][0] == {"role": "system", "content": "你是阅卷助教"}
        assert body["max_tokens"] == 2048
        assert body["stream"] is False

    def test_anthropic_format(self):
        method, url, headers, body = build_request(
            STYLE_ANTHROPIC, "https://api.anthropic.com", "claude-3-5-sonnet",
            MSGS, max_tokens=2048)
        assert method == "POST"
        assert url == "https://api.anthropic.com/v1/messages"
        assert headers == {"content-type": "application/json", "anthropic-version": "2023-06-01"}
        # system 单独字段，不出现在 messages
        assert body["system"] == "你是阅卷助教"
        assert body["messages"] == [{"role": "user", "content": "批改这段作文"}]
        assert body["max_tokens"] == 2048

    def test_gemini_format(self):
        method, url, _h, body = build_request(
            STYLE_GEMINI, "https://generativelanguage.googleapis.com", "gemini-2.0-flash",
            MSGS, max_tokens=2048)
        assert method == "POST"
        assert url == ("https://generativelanguage.googleapis.com/v1beta/models/"
                       "gemini-2.0-flash:generateContent")
        assert body["systemInstruction"] == {"parts": [{"text": "你是阅卷助教"}]}
        contents = body["contents"]
        assert contents[0] == {"role": "user", "parts": [{"text": "批改这段作文"}]}
        assert body["generationConfig"] == {"maxOutputTokens": 2048}

    def test_openai_trailing_slash(self):
        _, url, _, _ = build_request(
            STYLE_OPENAI, "https://spark-api-open.xf-yun.com/v1/", "spark-v4", MSGS)
        assert url == "https://spark-api-open.xf-yun.com/v1/chat/completions"

    def test_unsupported_style(self):
        with pytest.raises(ProviderError):
            build_request("bogus", "https://x", "m", MSGS)

    def test_invalid_message_role(self):
        with pytest.raises(ProviderError):
            build_request(STYLE_OPENAI, "https://x", "m",
                          [{"role": "admin", "content": "hi"}])


class TestResolveHeaders:
    def test_openai_bearer(self):
        h = resolve_headers("qwen", "sk-abc", STYLE_OPENAI)
        assert h["Authorization"] == "Bearer sk-abc"

    def test_anthropic_x_api_key(self):
        h = resolve_headers("anthropic", "ak-xyz", STYLE_ANTHROPIC)
        assert h["x-api-key"] == "ak-xyz"
        assert h["anthropic-version"] == "2023-06-01"

    def test_gemini_key(self):
        h = resolve_headers("gemini", "g-secret", STYLE_GEMINI)
        assert h["x-goog-api-key"] == "g-secret"

    def test_missing_key(self):
        with pytest.raises(ProviderError):
            resolve_headers("qwen", "", STYLE_OPENAI)


class TestParseResponse:
    def test_openai(self):
        body = {
            "choices": [{"message": {"content": "你好"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 3},
            "model": "qwen-max",
        }
        r = parse_response(STYLE_OPENAI, 200, body, "qwen-max")
        assert r.content == "你好"
        assert r.prompt_tokens == 12
        assert r.completion_tokens == 3
        assert r.finish_reason == "stop"
        assert r.model == "qwen-max"

    def test_anthropic(self):
        body = {
            "content": [{"type": "text", "text": "批注完毕"}],
            "usage": {"input_tokens": 50, "output_tokens": 20},
            "stop_reason": "end_turn",
            "model": "claude-3-5-sonnet",
        }
        r = parse_response(STYLE_ANTHROPIC, 200, body, "claude-3-5-sonnet")
        assert r.content == "批注完毕"
        assert r.prompt_tokens == 50
        assert r.completion_tokens == 20
        assert r.finish_reason == "end_turn"

    def test_gemini(self):
        body = {
            "candidates": [{"content": {"parts": [{"text": "评分 92"}]},
                            "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 33, "candidatesTokenCount": 7},
        }
        r = parse_response(STYLE_GEMINI, 200, body, "gemini-2.0-flash")
        assert r.content == "评分 92"
        assert r.prompt_tokens == 33
        assert r.completion_tokens == 7
        assert r.finish_reason == "STOP"

    def test_http_error(self):
        body = {"error": {"message": "rate limited"}}
        with pytest.raises(ProviderError) as ei:
            parse_response(STYLE_OPENAI, 429, body, "m")
        assert "429" in str(ei.value)

    def test_multi_part_gemini_content(self):
        body = {
            "candidates": [{"content": {"parts": [
                {"text": "成绩："}, {"text": "A"},
            ]}}],
            "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1},
        }
        r = parse_response(STYLE_GEMINI, 200, body, "gemini-2.0-flash")
        assert r.content == "成绩：A"


class TestParseStreamEvents:
    def test_openai_sse(self):
        chunk = (
            'data: {"choices":[{"delta":{"content":"你"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"好"}}]}\n\n'
            'data: {"choices":[],"usage":{"prompt_tokens":4,"completion_tokens":2}}\n\n'
            "data: [DONE]\n\n"
        ).encode()
        events = list(parse_stream_events(STYLE_OPENAI, chunk, "qwen-max"))
        toks = [e["content"] for e in events if e["type"] == "token"]
        usage = next(e for e in events if e["type"] == "usage")
        assert toks == ["你", "好"]
        assert usage["prompt_tokens"] == 4
        assert usage["completion_tokens"] == 2

    def test_anthropic_sse(self):
        chunk = (
            'event: content_block_delta\n'
            'data: {"type":"content_block_delta","delta":{"text":"阅"}}\n\n'
            'event: content_block_delta\n'
            'data: {"type":"content_block_delta","delta":{"text":"卷"}}\n\n'
            'event: message_delta\n'
            'data: {"type":"message_delta","usage":{"input_tokens":7,"output_tokens":2}}\n\n'
        ).encode()
        events = list(parse_stream_events(STYLE_ANTHROPIC, chunk, "claude-x"))
        toks = [e["content"] for e in events if e["type"] == "token"]
        usage = next(e for e in events if e["type"] == "usage")
        assert toks == ["阅", "卷"]
        assert usage["prompt_tokens"] == 7
        assert usage["completion_tokens"] == 2

    def test_gemini_sse(self):
        chunk = (
            'data: {"candidates":[{"content":{"parts":[{"text":"A+"}]}}]}\n\n'
            'data: {"usageMetadata":{"promptTokenCount":9,"candidatesTokenCount":1}}\n\n'
        ).encode()
        events = list(parse_stream_events(STYLE_GEMINI, chunk, "gemini-x"))
        toks = [e["content"] for e in events if e["type"] == "token"]
        usage = next(e for e in events if e["type"] == "usage")
        assert toks == ["A+"]
        assert usage["prompt_tokens"] == 9
        assert usage["completion_tokens"] == 1

    def test_unsupported_style(self):
        with pytest.raises(ProviderError):
            list(parse_stream_events("bogus", b"", "m"))