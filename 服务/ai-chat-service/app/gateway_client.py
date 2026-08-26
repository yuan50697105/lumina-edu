# ============================================
# Lumina 墨光 · AI 对话服务网关客户端
# 消费 ai-gateway：/gateway/route（选模型）+ /gateway/completions（统一调用）
# 用户 JWT 透传，用量自动归属对应用户
# ============================================
import json
from typing import Iterator

import httpx

from .config import settings

# 网关基础地址（compose 内 http://ai-gateway-service:8093）
GATEWAY_BASE = settings.AI_GATEWAY_URL.rstrip("/")


class GatewayError(Exception):
    """AI 网关节点的业务错误（API Key 缺失/无可用模型/限流等）"""


def route_model(user_token: str, task_type: str = "chat") -> str:
    """向网关要一个主选模型名（智能路由：按优先级+配额）"""
    try:
        resp = httpx.post(
            f"{GATEWAY_BASE}/api/v1/ai/gateway/route",
            json={"task_type": task_type},
            headers={"Authorization": user_token},
            timeout=10.0,
        )
    except httpx.HTTPError as e:
        raise GatewayError(f"网关不可达: {e}")
    if resp.status_code >= 400:
        raise GatewayError(f"路由失败 ({resp.status_code})")

    body = resp.json()
    primary = body.get("primary")
    if not primary:
        raise GatewayError(body.get("note") or "暂无可用模型，请管理员先配置模型池")
    return primary["model_name"]


def stream_completions(
    model_name: str,
    messages: list[dict],
    user_token: str,
    max_tokens: int = 2048,
) -> Iterator[dict]:
    """调网关 /gateway/completions（SSE 流式），产出统一事件 dict。

    yield: {"type":"token","content":str} | {"type":"error","message":str}
           | {"type":"done","model":str,"usage":{"prompt_tokens","completion_tokens"}}
    """
    payload = {
        "model_name": model_name,
        "messages": messages,
        "task_type": "chat",
        "max_tokens": max_tokens,
        "stream": True,
    }
    try:
        with httpx.Client(timeout=300.0) as client:
            with client.stream(
                "POST",
                f"{GATEWAY_BASE}/api/v1/ai/gateway/completions",
                json=payload,
                headers={"Authorization": user_token},
            ) as resp:
                if resp.status_code >= 400:
                    err = resp.read().decode("utf-8", errors="ignore")
                    yield {"type": "error", "message": f"网关 {resp.status_code}: {err[:200]}"}
                    return
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data:
                        continue
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    yield obj
    except httpx.HTTPError as e:
        yield {"type": "error", "message": f"网关连接失败: {e}"}