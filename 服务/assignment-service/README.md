# Lumina 墨光 · assignment-service 作业服务

FastAPI 作业服务：作业、提交、批阅 + 监控埋点。

## 功能

- **作业管理**：教师发布（rubric/AI 标记）、更新、删除、状态流转（draft → published → closed）
- **作业列表**：学生只读 published；教师/管理员含 draft（限定自己课程）；支持按 course_id 筛选
- **提交**：学生 multipart 提交（文件 + 文字答案 + 备注），自动**迟交判定**，支持重交覆盖
- **批阅**：教师手动评分（A-F 字母自动映射、rubric 维度得分），AI 批阅在 2.7 接入
- **权限**：学生需已选课才能提交；教师需课程授课权才能管理/批阅
- **埋点**：`assignment.*` 事件 + 全量请求日志

## 技术要点

- 共享 JWT + 共享 `users`/`courses`/`enrollments` 表校验（轻量一期单库方案）
- 文件上传走本地 `uploads/` 临时存储（静态挂载 `/files/*`），正式环境切换 MinIO
- `grades` 表 `submission_id` UNIQUE → 一次提交一条批阅记录，重新批阅为更新

## API 端点

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/assignments` | 作业列表（course_id/status 筛选） | 登录 |
| GET | `/assignments/{id}` | 作业详情 | 登录 |
| POST | `/courses/{cid}/assignments` | 发布作业 | 教师/管理员 |
| PATCH | `/assignments/{id}` | 更新作业/状态 | 教师/管理员 |
| DELETE | `/assignments/{id}` | 删除作业 | 教师/管理员 |
| POST | `/assignments/{id}/submit` | 提交作业（multipart） | 学生（已选课） |
| GET | `/assignments/{id}/submissions` | 提交列表（含批阅结果） | 教师/管理员 |
| GET | `/assignments/{id}/submissions/me` | 我的提交 | 登录（本人） |
| POST | `/assignments/{id}/grade?submission_id=` | 批阅作业 | 教师/管理员 |

## 本地运行

```bash
# 1. 数据库
cd ../部署 && docker compose up -d postgres

# 2. 依赖
cd ../服务/assignment-service
../user-service/.venv/Scripts/pip install -r requirements.txt

# 3. 启动（端口 8091）
export DATABASE_URL="postgresql://lumina:lumina_secure_password@localhost:5432/lumina"
../user-service/.venv/Scripts/uvicorn app.main:app --reload --port 8091
```

## 测试

```bash
# 单元测试（无需 DB）
../user-service/.venv/Scripts/python -m pytest tests/test_schemas.py -q

# 集成测试（需 PostgreSQL）
../user-service/.venv/Scripts/python -m pytest tests/ -q
```

> 集成测试含：发布→提交→批阅→状态全链路、迟交标记、越权拦截（未选课提交 403）、分数超限 400。

## Docker 部署

随 `部署/docker-compose.yml` 编排（`lumina-assignment-service`，:8091）。Nginx 通过正则路由 `/api/v1/assignments*` 与 `/api/v1/courses/{id}/assignments*` 转发至本服务（顺序敏感，见 `lumina.conf`）。