# ============================================
# Lumina 墨光 · AI 批阅服务网关客户端
# 消费 ai-gateway：/gateway/route（选模型）+ /gateway/completions（非流式）
# 用户 JWT 透传，用量自动归属对应用户
# ============================================
import httpx

from app.config import settings

GATEWAY_BASE = settings.AI_GATEWAY_URL.rstrip("/")


class GatewayError(Exception):
    """AI 网关错误（API Key 缺失/无可用模型/限流等）"""


def route_model(user_token: str, task_type: str = "grade") -> str:
    """向网关要一个主选模型名（智能路由：优先级+配额）"""
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


def fetch_completions(
    model_name: str,
    messages: list[dict],
    user_token: str,
    task_type: str = "grade",
    max_tokens: int = 2048,
) -> dict:
    """调网关 /gateway/completions（非流式），返回 CompletionsOut 形状。

    returns: {"content": str, "model": str, "finish_reason": str|None,
              "prompt_tokens": int, "completion_tokens": int}
    """
    payload = {
        "model_name": model_name,
        "messages": messages,
        "task_type": task_type,
        "max_tokens": max_tokens,
        "stream": False,
    }
    try:
        resp = httpx.post(
            f"{GATEWAY_BASE}/api/v1/ai/gateway/completions",
            json=payload,
            headers={"Authorization": user_token},
            timeout=300.0,
        )
    except httpx.HTTPError as e:
        raise GatewayError(f"网关连接失败: {e}")

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", "")
        except Exception:
            detail = resp.text[:200]
        raise GatewayError(f"模型调用失败 ({resp.status_code}): {detail}")
    return resp.json()