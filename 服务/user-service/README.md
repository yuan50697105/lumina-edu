# Lumina 墨光 · user-service 用户服务

FastAPI 用户/认证服务，包含应用级监控埋点。

## 功能

- **认证**：登录（学号/工号/邮箱）、双令牌（Access 15min + Refresh 7d）、刷新、登出、修改密码
- **用户**：资料查询/更新、公开资料、管理端列表/删除（admin）
- **埋点**：`EventTracking`（业务事件）+ `APILog`（全量请求日志）写入 PostgreSQL
- **安全**：bcrypt 密码哈希、JWT 双令牌、角色权限依赖、RFC 7807 错误格式

## 技术栈

FastAPI 0.115 · SQLAlchemy 2.0 · PostgreSQL 16 · python-jose · passlib(bcrypt)

## 目录结构

```
user-service/
├── Dockerfile            # 基于 python:3.12-slim
├── requirements.txt
├── app/
│   ├── main.py           # 应用入口 + 请求日志中间件 + 健康检查
│   ├── config.py         # pydantic-settings 配置
│   ├── database.py       # SQLAlchemy engine / SessionLocal
│   ├── models.py         # User / Session / APILog / EventTracking
│   ├── schemas.py        # Pydantic 校验模型
│   ├── security.py       # bcrypt + JWT
│   ├── dependencies.py   # get_current_user / require_role
│   ├── instrumentation.py# 埋点 Instrumentation + Timer
│   └── routers/
│       ├── auth.py       # /api/v1/auth/*
│       └── users.py      # /api/v1/users*
└── tests/
    ├── test_security.py  # 单元测试（无需数据库）
    └── test_auth_api.py  # 集成测试（需 PostgreSQL）
```

## 本地运行

```bash
# 1. 启动数据库（项目根 /部署 目录）
cd ../部署 && docker compose up -d postgres

# 2. 安装依赖
cd ../服务/user-service
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt

# 3. 设置环境变量（开发默认直连 localhost:5432 lumina/lumina_secure_password）
export DATABASE_URL="postgresql://lumina:lumina_secure_password@localhost:5432/lumina"

# 4. 启动
.venv/Scripts/uvicorn app.main:app --reload --port 8080
```

访问 `http://localhost:8080/docs` 查看 Swagger UI。

## 测试

```bash
# 单元测试（无需数据库，任何环境可跑）
.venv/Scripts/python -m pytest tests/test_security.py -q

# 集成测试（需 PostgreSQL 409 已启动）
.venv/Scripts/python -m pytest tests/ -q
```

> 集成测试在数据库不可用时会自动跳过（skip），不阻塞 CI。

## Docker 部署

随 `部署/docker-compose.yml` 一起编排：

```bash
cd ../部署
cp .env.example .env    # 修改 JWT_SECRET_KEY 等敏感项
docker compose up -d --build user-service
```

镜像暴露 `:8080`，健康检查 `GET /health`。Nginx 将 `/api/*` 代理至 `user-service:8080`。

## 监控埋点

| 事件 | 说明 |
|------|------|
| `user.login` / `user.login_fail` | 登录成功/失败 |
| `user.register` | 注册 |
| `user.logout` | 登出 |
| `user.token_refresh` | 令牌刷新 |
| `user.password_change` | 修改密码 |
| `user.profile_update` | 更新资料 |
| `user.view` | 查看用户资料 |

业务事件写入 `event_tracking`；每次 HTTP 请求自动写入 `api_logs`（含 method/path/status/耗时），由 `app/main.py` 中间件完成。