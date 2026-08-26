# Lumina 墨光 · ai-gateway-service AI 网关服务

FastAPI AI 网关：模型池管理、智能路由、用量统计 + 监控埋点。

## 功能

- **模型池管理**（管理员）：注册/停用模型、配置价格/优先级/任务类型；供应商配额管理
- **可用模型列表**：对外只暴露已启用模型，可按任务类型过滤（`/ai/models`）
- **智能路由**：按任务类型（chat/grade/generate/vl/speech）返回主选+备选模型；规则 = 启用状态 + 优先级 + 供应商预算配额
- **用量记录**：对话/批阅服务调用后上报 token/延迟/成本，自动累加供应商已用额度
- **用量统计**：近 N 天按模型/用户的调用量、总 token、总成本
- **种子模型池**：首次启动自动预置 6 家供应商 + 8 个国产模型
- **埋点**：`ai.*` 事件 + 全量请求日志

## 路由表

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/ai/models` | 可用模型列表（task_type 过滤） | 登录 |
| POST | `/ai/gateway/route` | 智能路由（task_type → primary/fallback） | 登录 |
| POST | `/ai/gateway/calls/record` | 记录一次模型调用用量 | 登录 |
| GET | `/ai/gateway/usage` | 用量统计（N 天） | 管理员 |
| GET | `/ai/gateway/models` | 模型池列表 | 管理员 |
| POST | `/ai/gateway/models` | 注册模型 | 管理员 |
| PATCH | `/ai/gateway/models/{id}` | 启停/更新模型 | 管理员 |
| GET/POST | `/ai/gateway/providers` | 供应商列表/新增 | 管理员 |

## 预置模型池

| 供应商 | 模型 | 任务 | 价格(¥/千token) | 优先级 |
|--------|------|------|-----------------|--------|
| qwen 通义 | qwen-max | chat, generate | 0.020 | 10 |
| qwen 通义 | qwen-vl | vl 多模态 | 0.080 | 10 |
| glm 智谱 | glm-4 | chat, grade, generate | 0.050 | 20 |
| spark 讯飞 | spark-v4 | chat | 0.030 | 30 |
| spark 讯飞 | spark-v3 | speech 语音 | 按分钟 | 10 |
| doubao 豆包 | doubao-lite | chat | 0.005 | 40 |
| bce 百川 | bce-embedding | generate(RAG) | 0.0007 | 10 |
| moonshot 月暗 | kimi | chat, grade | 0.060 | 50 |

## 架构说明

- **管理面设计**：网关负责「配置+路由+用量」，不直接调用 LLM——真实请求在对话（2.6）/批阅（2.7）服务发起，经 `/gateway/calls/record` 回传用量
- **API Key 不入库**：`QWEN_API_KEY` 等从环境变量注入（`.env.example` 已预留），避免敏感信息落库
- **共享库/JWT**：与其它服务同一 PostgreSQL + 同一 JWT_SECRET_KEY 鉴权

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