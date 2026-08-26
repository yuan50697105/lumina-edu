# Lumina 墨光 · ai-chat-service AI 对话服务

FastAPI 苏格拉底导师：SSE 流式对话、对话历史管理、对话质量埋点。消费 `ai-gateway-service` 的统一调用，只负责「教育引导编排 + 会话持久化」。

## 功能

- **苏格拉底导师对话** `POST /ai/chat`（SSE）：构建教学模式 system prompt，历史消息回看，自动调 AI 网关智能路由选模型（或 `X-Model` 指定），流式转发 token/done/error 事件
- **会话管理**：自动建会话并生成标题；续聊（传 `conversation_id` 带历史）；列表/详情/删除
- **对话质量埋点**：`ai.chat_start` / `ai.chat_done` / `ai.chat_error` + 全量请求日志
- **课程上下文**：请求可带 `context.course_id` / `context.chapter_id`，注入提示词并归档在会话上

## 路由表

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/ai/chat` | 对话（SSE 流式） | 登录 |
| GET | `/ai/conversations` | 对话历史列表（可 course_id 过滤） | 登录 |
| GET | `/ai/conversations/{id}` | 会话消息详情 | 登录 |
| DELETE | `/ai/conversations/{id}` | 删除会话（级联删消息） | 登录 |

## 对话示例

```bash
# 流式对话（模型缺省走智能路由；也可 X-Model 头/body model_name 指定）
curl -N -X POST http://localhost:8094/api/v1/ai/chat \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"message":"这个积分怎么解？","context":{"course_id":"c001","chapter_id":"ch004"}}'

# 续聊
curl -N -X POST ... -d '{"conversation_id":"<conv_uuid>","message":"那换元法呢？"}'

# 指定模型
curl -N -X POST ... -H "X-Model: qwen-max" -d '{"message":"解释极限"}'
```

SSE 事件流：`data: {"type":"token","content":...}` → `data: {"type":"done","conversation_id":...,"usage":{"prompt_tokens":N,"completion_tokens":M}}`；出错时 `{"type":"error","message":...}`。

## 架构说明

- **对接网关**：`gateway_client.py` 消费 `ai-gateway` 的 `/gateway/route`（智能选模型）+ `/gateway/completions`（SSE 统一调用）；**用户 JWT 透传**给网关，用量自动归属当前用户，本服务不持任何厂商 Key
- **提示词引擎**：`prompt.py` 纯函数（苏格拉底引导 + 课程上下文注入 + 历史窗口截断），可独立单测
- **表结构**：`ai_conversations` / `ai_messages`（对齐 init.sql 与数据库设计文档），共享 `api_logs` / `event_tracking`
- **共享库/JWT**：与其它服务同一 PostgreSQL + 同一 `JWT_SECRET_KEY` 鉴权

## 本地运行

前置：PostgreSQL 已启动 + ai-gateway:8093 已启动（模型池已配置）。

```bash
cd ../服务/ai-chat-service
../user-service/.venv/Scripts/pip install -r requirements.txt
export DATABASE_URL="postgresql://lumina:lumina_secure_password@localhost:5432/lumina"
export AI_GATEWAY_URL="http://localhost:8093"
../user-service/.venv/Scripts/uvicorn app.main:app --reload --port 8094
```

## 测试

```bash
../user-service/.venv/Scripts/python -m pytest tests/test_chat.py -q   # 单测（无需 DB/网关）
../user-service/.venv/Scripts/python -m pytest tests/ -q               # 集成（需 PG + 网关）
```

## Docker 部署

随 `部署/docker-compose.yml` 编排（`lumina-ai-chat`，:8094），内部 `AI_GATEWAY_URL=http://ai-gateway-service:8093`。Nginx 将 `/api/v1/ai/chat` 与 `/api/v1/ai/conversations` 路由至本服务。