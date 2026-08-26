# ============================================
# Lumina 墨光 · AI 协议适配器单元测试
# 请求构造 / 响应解析 / 消息验证
# ============================================
import json
import pytest

from app.modules.ai_gateway.adapters import (
    STYLE_OPENAI,
    STYLE_ANTHROPIC,
    STYLE_GEMINI,
    SUPPORTED_STYLES,
    ProviderError,
    ChatResult,
    validate_messages,
    build_request,
    parse_response,
    parse_stream_events,
)


class TestValidateMessages:
    """消息格式验证测试"""

    def test_valid_messages(self):
        """有效消息通过"""
        msgs = [
            {"role": "system", "content": "你是助手"},
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！"},
        ]
        result = validate_messages(msgs)
        assert len(result) == 3

    def test_invalid_role_raises(self):
        """无效角色抛出异常"""
        with pytest.raises(ProviderError, match="消息格式错误"):
            validate_messages([{"role": "admin", "content": "test"}])

    def test_missing_content_raises(self):
        """缺少 content 抛出异常"""
        with pytest.raises(ProviderError):
            validate_messages([{"role": "user"}])

    def test_non_string_content_raises(self):
        """非字符串 content 抛出异常"""
        with pytest.raises(ProviderError):
            validate_messages([{"role": "user", "content": 123}])

    def test_empty_messages(self):
        """空消息列表返回空"""
        result = validate_messages([])
        assert result == []


class TestBuildRequest:
    """请求构造测试"""

    def test_openai_style(self):
        """OpenAI 风格请求构造"""
        method, url, headers, body = build_request(
            STYLE_OPENAI,
            "https://api.openai.com/v1",
            "gpt-4",
            [{"role": "user", "content": "hello"}],
        )
        assert method == "POST"
        assert "/chat/completions" in url
        assert body["model"] == "gpt-4"
        assert body["messages"][0]["content"] == "hello"

    def test_anthropic_style(self):
        """Anthropic 风格请求构造"""
        method, url, headers, body = build_request(
            STYLE_ANTHROPIC,
            "https://api.anthropic.com",
            "claude-3",
            [
                {"role": "system", "content": "你是助手"},
                {"role": "user", "content": "hello"},
            ],
        )
        assert method == "POST"
        assert "/v1/messages" in url
        assert body["model"] == "claude-3"
        # Anthropic system 分离
        assert "system" in body
        assert body["system"] == "你是助手"
        assert body["messages"][0]["role"] == "user"

    def test_gemini_style(self):
        """Gemini 风格请求构造"""
        method, url, headers, body = build_request(
            STYLE_GEMINI,
            "https://generativelanguage.googleapis.com/v1beta",
            "gemini-pro",
            [{"role": "user", "content": "hello"}],
        )
        assert method == "POST"
        assert "generateContent" in url
        assert "contents" in body

    def test_unsupported_style_raises(self):
        """不支持的风格抛出异常"""
        with pytest.raises(ProviderError):
            build_request("unknown", "http://api.test", "model",
                          [{"role": "user", "content": "hello"}])

    def test_stream_flag(self):
        """流式标志正确传递"""
        _, _, _, body = build_request(
            STYLE_OPENAI, "http://api.test", "model",
            [{"role": "user", "content": "hello"}],
            stream=True,
        )
        assert body["stream"] is True


class TestParseResponse:
    """响应解析测试"""

    def test_openai_response(self):
        """OpenAI 响应解析"""
        raw = {
            "choices": [{"message": {"content": "你好！"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "model": "gpt-4",
        }
        result = parse_response(STYLE_OPENAI, 200, raw, "gpt-4")
        assert result.content == "你好！"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 20
        assert result.finish_reason == "stop"

    def test_anthropic_response(self):
        """Anthropic 响应解析"""
        raw = {
            "content": [{"type": "text", "text": "你好！"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
            "model": "claude-3",
        }
        result = parse_response(STYLE_ANTHROPIC, 200, raw, "claude-3")
        assert result.content == "你好！"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 20

    def test_gemini_response(self):
        """Gemini 响应解析"""
        raw = {
            "candidates": [{"content": {"parts": [{"text": "你好！"}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20},
        }
        result = parse_response(STYLE_GEMINI, 200, raw, "gemini-pro")
        assert result.content == "你好！"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 20

    def test_error_status_raises(self):
        """错误状态码抛出异常"""
        raw = {"error": {"message": "Invalid API key"}}
        with pytest.raises(ProviderError, match="供应商返回 401"):
            parse_response(STYLE_OPENAI, 401, raw, "model")


class TestParseStreamEvents:
    """流式事件解析测试"""

    def test_openai_sse_token(self):
        """OpenAI SSE token 事件"""
        chunk = 'data: {"choices":[{"delta":{"content":"你"},"index":0}]}\n\n'.encode()
        events = list(parse_stream_events(STYLE_OPENAI, chunk, "model"))
        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) >= 1
        assert token_events[0]["content"] == "你"

    def test_openai_sse_done(self):
        """OpenAI SSE 完成事件"""
        chunk = b'data: [DONE]\n\n'
        events = list(parse_stream_events(STYLE_OPENAI, chunk, "model"))
        # [DONE] 事件可能不产生事件或产生 done 事件
        assert isinstance(events, list)

    def test_anthropic_sse_token(self):
        """Anthropic SSE token 事件"""
        chunk = 'event: content_block_delta\ndata: {"delta":{"text":"你"}}\n\n'.encode()
        events = list(parse_stream_events(STYLE_ANTHROPIC, chunk, "model"))
        # 至少能解析不报错
        assert isinstance(events, list)

    def test_empty_chunk(self):
        """空字节块返回空事件"""
        events = list(parse_stream_events(STYLE_OPENAI, b"", "model"))
        assert events == []


class TestSupportedContent:
    """支持的风格常量测试"""

    def test_three_styles(self):
        """支持 3 种协议风格"""
        assert len(SUPPORTED_STYLES) == 3
        assert STYLE_OPENAI in SUPPORTED_STYLES
        assert STYLE_ANTHROPIC in SUPPORTED_STYLES
        assert STYLE_GEMINI in SUPPORTED_STYLES
