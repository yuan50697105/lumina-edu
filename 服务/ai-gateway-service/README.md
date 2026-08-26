# Lumina 墨光 · ai-gateway-service AI 网关服务

FastAPI AI 网关：模型池管理、智能路由、统一协议调用、用量统计 + 监控埋点。

## 功能

- **模型池管理**（管理员）：注册/停用模型、配置价格/优先级/任务类型、供应商配额管理
- **可用模型列表**：对外只暴露已启用模型，可按任务类型过滤（`/ai/models`）
- **智能路由**：按任务类型（chat/grade/generate/vl/speech）返回主选+备选模型；规则 = 启用状态 + 优先级 + 供应商预算配额
- **统一协议调用**：一个 `/gateway/completions` 端点发真实 LLM 请求，自动适配 OpenAI / Anthropic / Gemini 三套协议（含 SSE 流式）
- **自定义模型池（运营端）**：供应商/模型全部由运营端通过管理 API 配置，不预置任何模型——首次接入厂商流程：注册供应商 → 注册模型 → 配置环境变量 Key
- **用量记录**：对话/批阅服务调用后上报 token/延迟/成本，自动累加供应商已用额度
- **用量统计**：近 N 天按模型/用户的调用量、总 token、总成本
- **埋点**：`ai.*` 事件 + 全量请求日志

## 路由表

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/ai/models` | 可用模型列表（task_type 过滤） | 登录 |
| POST | `/ai/gateway/route` | 智能路由（task_type → primary/fallback） | 登录 |
| POST | `/ai/gateway/completions` | 统一模型调用（协议自适应 + SSE 流式） | 登录 |
| POST | `/ai/gateway/calls/record` | 记录一次模型调用用量 | 登录 |
| GET | `/ai/gateway/usage` | 用量统计（N 天） | 管理员 |
| GET | `/ai/gateway/models` | 模型池列表 | 管理员 |
| POST | `/ai/gateway/models` | 注册模型 | 管理员 |
| PATCH | `/ai/gateway/models/{id}` | 启停/更新模型 | 管理员 |
| GET/POST | `/ai/gateway/providers` | 供应商列表/新增 | 管理员 |

## 配置模型池（运营端自定义）

不预置任何模型——首次接入需按以下顺序配置：

### 1. 注册供应商

```bash
# OpenAI 兼容系（国内厂商 endpoint 为 /v1 或 compatible-mode）
curl -X POST http://localhost:8093/api/v1/ai/gateway/providers \
  -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" \
  -d '{"name":"qwen","display_name":"通义千问","endpoint_base":"https://dashscope.aliyuncs.com/compatible-mode/v1","monthly_quota":500}'

# Anthropic 系
curl -X POST .../providers -d '{"name":"anthropic","display_name":"Anthropic","endpoint_base":"https://api.anthropic.com","monthly_quota":100}'

# Gemini 系
curl -X POST .../providers -d '{"name":"gemini","display_name":"Google Gemini","endpoint_base":"https://generativelanguage.googleapis.com","monthly_quota":100}'
```

### 2. 在模型池注册模型

```bash
# OpenAI 兼容模型（api_style=openai）
curl -X POST http://localhost:8093/api/v1/ai/gateway/models \
  -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" \
  -d '{"provider_name":"qwen","model_name":"qwen-max","display_name":"通义千问 Max","task_types":["chat","generate"],"priority":10,"cost_per_1k_tokens":0.02,"max_tokens":8192,"api_style":"openai"}'

# Anthropic 模型（api_style=anthropic，自动切 x-api-key 协议）
curl -X POST .../models -d '{"provider_name":"anthropic","model_name":"claude-3-5-sonnet","display_name":"Claude Sonnet","task_types":["chat","grade"],"priority":5,"cost_per_1k_tokens":0.1,"api_style":"anthropic"}'

# Gemini 模型（api_style=gemini，自动切 x-goog-api-key 协议）
curl -X POST .../models -d '{"provider_name":"gemini","model_name":"gemini-2.0-flash","display_name":"Gemini 2.0 Flash","task_types":["chat","generate"],"priority":5,"cost_per_1k_tokens":0.08,"api_style":"gemini"}'
```

### 3. 配置环境变量 Key

在 `.env` / compose 中为对应厂商注入 Key（`QWEN_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` 等），重启网关生效。Key 不入库。

> **提示**：`api_style` 决定 `/gateway/completions` 走哪套协议（openai / anthropic / gemini）；`endpoint_base` 是厂商 API Base URL。两者在注册时可随时通过 PATCH 调整。

## 架构说明

- **统一适配层**：`app/adapters.py` 将统一内部消息 `[{role, content}]` 翻译成三家厂商协议——
  - **OpenAI 系**（qwen/glm/spark/doubao/bce/moonshot）：POST `{base}/chat/completions`，`Authorization: Bearer`
  - **Anthropic 系**（claude）：POST `{base}/v1/messages`，`x-api-key` + `anthropic-version`；system 拆成独立字段
  - **Gemini 系**：POST `{base}/v1beta/models/{model}:generateContent`，`x-goog-api-key`；role 映射 model/user
  - 响应统一为 `ChatResult(content / prompt_tokens / completion_tokens / finish_reason)`；SSE 统一为 `{type: token|usage|error}` 事件流
- **管理面设计**：网关负责「配置+路由+用量+统一调用」；真实 LLM 请求既可走网关 `/gateway/completions`，也可由对话（2.6）/批阅（2.7）服务直接调用适配层
- **API Key 不入库**：`QWEN_API_KEY` 等从环境变量注入（`.env.example` 已预留 OpenAI 系 + Anthropic + Gemini），避免敏感信息落库
- **模型协议识别**：每个模型注册时通过 `api_style`（openai/anthropic/gemini）标记，供应商 `endpoint_base` 存厂商 API Base URL，适配层据此组装请求
- **共享库/JWT**：与其它服务同一 PostgreSQL + 同一 JWT_SECRET_KEY 鉴权

## 统一调用示例

```bash
# 非流式（自动按模型 api_style 适配协议）
curl -X POST http://localhost:8093/api/v1/ai/gateway/completions \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"model_name":"qwen-max","messages":[{"role":"user","content":"总结本课重点"}],"max_tokens":1024}'

# SSE 流式（data: {"type":"token",...} → data: {"type":"done","usage":{...}}）
curl -N -X POST ... -d '{"model_name":"qwen-max","stream":true,"messages":[...]}'
```

## 本地运行

```bash
cd ../部署 && docker compose up -d postgres
cd ../服务/ai-gateway-service
../user-service/.venv/Scripts/pip install -r requirements.txt
export DATABASE_URL="postgresql://lumina:lumina_secure_password@localhost:5432/lumina"
../user-service/.venv/Scripts/uvicorn app.main:app --reload --port 8093
```

## 测试

```bash
../user-service/.venv/Scripts/python -m pytest tests/test_gateway.py -q   # 单测（无需 DB）
../user-service/.venv/Scripts/python -m pytest tests/ -q                 # 集成（需 PostgreSQL）
```

## Docker 部署

随 `部署/docker-compose.yml` 编排（`lumina-ai-gateway`，:8093）。Nginx 将 `/api/v1/ai/*` 路由至本服务。