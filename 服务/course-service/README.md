# Lumina 墨光 · course-service 课程服务

FastAPI 课程服务：课程、章节、选课、公告 + 监控埋点。

## 功能

- **课程**：列表（学期/院系筛选、分页）、详情、教师创建/更新（含发布状态流转）
- **章节**：列表、新增/更新/删除（教师管理）
- **选课**：学生选课/退课，`students_count` 实时维护，唯一约束去重
- **公告**：发布（教师）、列表（置顶优先）
- **我的课程**：`/courses/me/enrolled` 统一学生已选与教师开设
- **埋点**：`course.*` / `chapter.*` / `announcement.*` 事件 + 全量请求日志

## 技术要点

- **跨服务认证**：与 user-service 共享 `JWT_SECRET_KEY`，解码 Access Token 做鉴权
- **共享数据库**：轻量一期单库方案，直接查询共享 `users` 表取教师/学生姓名（减少跨服务 HTTP 调用）
- **权限模型**：教师/管理员可管理课程；普通请求需登录；学生只能选课

## 目录结构

```
course-service/
├── Dockerfile              # python:3.12-slim，暴露 :8090
├── requirements.txt
├── app/
│   ├── main.py             # 入口 + 请求日志中间件 + 健康检查
│   ├── config.py           # 配置（DATABASE_URL / JWT / USER_SERVICE_URL）
│   ├── models.py           # Course / Enrollment / Chapter / Announcement / UserBrief
│   ├── schemas.py          # Pydantic 校验
│   ├── security.py         # JWT 解码（跨服务共享密钥）
│   ├── dependencies.py     # get_current_user / require_role
│   ├── instrumentation.py  # 埋点 Instrumentation + Timer
│   └── routers/courses.py  # 全部课程端点
└── tests/
    ├── test_schemas.py     # 单元测试（无需 DB）
    └── test_courses_api.py # 集成测试（需 PostgreSQL）
```

## API 端点

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/courses` | 课程列表（semester/department/分页） | 登录 |
| GET | `/courses/me/enrolled` | 我的课程 | 登录 |
| GET | `/courses/{id}` | 课程详情 | 登录 |
| POST | `/courses` | 创建课程 | 教师/管理员 |
| PATCH | `/courses/{id}` | 更新课程/发布状态 | 教师/管理员 |
| GET | `/courses/{id}/chapters` | 章节列表 | 登录 |
| POST | `/courses/{id}/chapters` | 新增章节 | 教师/管理员 |
| PATCH/DELETE | `/courses/{id}/chapters/{chid}` | 更新/删除章节 | 教师/管理员 |
| POST | `/courses/{id}/enroll` | 选课（校验 published） | 学生 |
| DELETE | `/courses/{id}/enroll` | 退课 | 学生 |
| GET | `/courses/{id}/students` | 选课学生列表 | 教师/管理员 |
| GET | `/courses/{id}/announcements` | 公告列表 | 登录 |
| POST | `/courses/{id}/announcements` | 发布公告 | 教师/管理员 |

## 本地运行

```bash
# 1. 数据库
cd ../部署 && docker compose up -d postgres

# 2. 依赖（可复用 user-service venv 或新建）
cd ../服务/course-service
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt

# 3. 启动（端口 8090，与 user-service 的 8080 区分）
export DATABASE_URL="postgresql://lumina:lumina_secure_password@localhost:5432/lumina"
.venv/Scripts/uvicorn app.main:app --reload --port 8090
```

`http://localhost:8090/docs` → Swagger UI。

## 测试

```bash
# 单元测试（无需 DB）
../user-service/.venv/Scripts/python -m pytest tests/test_schemas.py -q

# 集成测试（需 PostgreSQL + users 表）
../user-service/.venv/Scripts/python -m pytest tests/ -q
```

## Docker 部署

随 `部署/docker-compose.yml` 编排（`lumina-course-service`），Nginx 将 `/api/v1/courses*` 路由至 `course-service:8090`。

```bash
cd ../部署 && docker compose up -d --build course-service
```