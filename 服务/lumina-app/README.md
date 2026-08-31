# Lumina 墨光 · 单体应用（lumina-app）

9 微服务合并为 1 个 FastAPI 单体，保留模块化结构，部署只需 **1 个容器 + MySQL**。

## 快速开始

```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8080 --reload
```

## 模块

| 模块 | 路径 | 功能 |
|------|------|------|
| user | `app/modules/user/` | 认证/用户管理 |
| course | `app/modules/course/` | 课程/章节/选课 |
| assignment | `app/modules/assignment/` | 作业/提交/批阅 |
| grade | `app/modules/grade/` | 成绩录入/统计 |
| live | `app/modules/live/` | 直播课堂（REST + after_id 轮询 · HLS） |
| ai_gateway | `app/modules/ai_gateway/` | AI 模型池/路由 |
| ai_chat | `app/modules/ai_chat/` | AI 对话 |
| ai_grade | `app/modules/ai_grade/` | AI 批阅 |
| analytics | `app/modules/analytics/` | 埋点收集 |
| logs | `app/modules/logs/` | 日志查询 |

## 端点

60 个业务 RESTful API（10 模块），prefix `/api/v1`；另有 `/health`、`/media/{path}`（HLS 反代）等。

## 部署

```bash
docker build -t lumina-app .
docker run -d -p 8080:8080 --env-file ../.env lumina-app
```
