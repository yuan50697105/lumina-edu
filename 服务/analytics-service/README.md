# Lumina 墨光 · analytics-service 埋点收集服务

FastAPI 事件收集：接收前端（`web-frontend` 埋点 SDK）与各服务上报的行为事件，写入共享 `event_tracking` 表，并提供统计查询。对应 WBS 2.10。

## 功能

- **单事件上报** `POST /events`（202，游客可访问）：登录用户由 JWT 覆盖身份，游客信任客户端 `user_id`
- **批量上报** `POST /events/batch`（≤100 条/事务），适合离线排队重放
- **字段对齐** `event_tracking`：`event_name / user_id / session_id / course_id / properties / page_url` + 服务端补 `user_agent / ip_address`（x-forwarded-for 取首段）；`properties.course_id` 自动提升为列
- **统计查询**（管理员）：`GET /events/stats` 概览（总量/独立用户/独立会话/时间窗）、`GET /events/breakdown` 事件类型分布（count + 独立用户）

## 路由表

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/events` | 上报单条事件 | 公开（游客/登录） |
| POST | `/events/batch` | 批量上报 ≤100 | 公开 |
| GET | `/events/stats` | 统计概览（近 N 天，可 event_name 过滤） | 管理员 |
| GET | `/events/breakdown` | 事件类型分布（近 N 天，Top N） | 管理员 |

## 事件格式（与前端 SDK 对齐）

```json
{
  "event_name": "page.view",
  "user_id": "uuid",          // 可选；登录用户由 JWT 覆盖
  "session_id": "sess-abc",
  "page_url": "https://...",
  "properties": { "source": "web", "course_id": "c001" }   // course_id 提升为列
}
```

## 架构说明

- **生而不回执**：上报端点返回 202，前端 `sendBeacon` 不等待；失败前端口 `localStorage` 队列重试、重放走 `/events/batch`
- **共享表**：`event_tracking` / `api_logs`（init.sql 已建）；`properties` 存 JSONB，查询走既有索引 `(event_name, created_at DESC)`
- **身份信任模型**：有合法 Access Token → 服务端 JWT `sub` 覆盖，杜绝伪造；无 Token（首屏/游客）→ 信任客户端 UUID
- **限流提示**：埋点端点建议在 Nginx 配置独立 `limit_req` zone（低频 10 r/s），见部署

## 本地运行

```bash
cd ../部署 && docker compose up -d postgres
cd ../服务/analytics-service
../user-service/.venv/Scripts/pip install -r requirements.txt
export DATABASE_URL="postgresql://lumina:lumina_secure_password@localhost:5432/lumina"
../user-service/.venv/Scripts/uvicorn app.main:app --reload --port 8096
```

## 测试

```bash
../user-service/.venv/Scripts/python -m pytest tests/test_analytics.py -q   # 单测（无需 DB）
../user-service/.venv/Scripts/python -m pytest tests/ -q                    # 集成（需 PostgreSQL）
```

## Docker 部署

随 `部署/docker-compose.yml` 编排（`lumina-analytics`，:8096）。Nginx `/api/v1/events`（含 `/batch`）与 `/api/v1/events/{stats,breakdown}` → 本服务。