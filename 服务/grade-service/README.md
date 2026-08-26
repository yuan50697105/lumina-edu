# Lumina 墨光 · grade-service 成绩服务

FastAPI 成绩服务：学期成绩汇总、成绩单、统计 + 监控埋点。

## 功能

- **录入成绩**：教师按学生录入/更新学期成绩（`student_id + course_id + semester` 唯一，重复录入为更新）
- **自动计算**：百分制 → GPA 绩点（4.0 制映射）+ A-F 等级自动派生
- **我的成绩单**：学生查看课程明细 + **加权 GPA**（按学分加权）+ 总学分
- **课程成绩**：教师查看本课程全部学生成绩
- **统计**：平均分 / 最高最低 / 及格率 / A-F 分布（按课程或学期筛选）
- **埋点**：`grade.*` 事件 + 全量请求日志

## GPA 映射（4.0 制）

| 分数 | 绩点 | 等级 |
|------|------|------|
| ≥90 | 4.0 | A |
| 85–89 | 3.7 | B |
| 82–84 | 3.3 | B |
| 78–81 | 3.0 | C |
| 75–77 | 2.7 | C |
| 72–74 | 2.3 | C |
| 68–71 | 2.0 | D |
| 64–67 | 1.5 | D |
| 60–63 | 1.0 | D |
| <60 | 0.0 | F |

## API 端点

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/grades/me` | 我的成绩单（GPA + 学分 + 明细） | 登录 |
| GET | `/grades/statistics` | 成绩统计（course_id/semester） | 登录 |
| GET | `/courses/{cid}/grades` | 课程成绩列表 | 教师/管理员 |
| POST | `/courses/{cid}/grades` | 录入/更新成绩 | 教师/管理员 |
| DELETE | `/courses/{cid}/grades/{sid}` | 删除成绩 | 教师/管理员 |

## 本地运行

```bash
# 1. 数据库
cd ../部署 && docker compose up -d postgres

# 2. 依赖（复用 user-service venv 或新建）
cd ../服务/grade-service
../user-service/.venv/Scripts/pip install -r requirements.txt

# 3. 启动（端口 8092）
export DATABASE_URL="postgresql://lumina:lumina_secure_password@localhost:5432/lumina"
../user-service/.venv/Scripts/uvicorn app.main:app --reload --port 8092
```

## 测试

```bash
# 单元测试（GPA/字母映射、schema，无需 DB）
../user-service/.venv/Scripts/python -m pytest tests/test_grades.py -q

# 集成测试（需 PostgreSQL）
../user-service/.venv/Scripts/python -m pytest tests/ -q
```

## Docker 部署

随 `部署/docker-compose.yml` 编排（`lumina-grade-service`，:8092）。Nginx 正则路由 `/api/v1/grades*` 与 `/api/v1/courses/{id}/grades*` 转发至本服务（顺序敏感，见 `lumina.conf`）。

## 数据来源说明

`grade_records` 存储**学期最终成绩**（成绩单数据源）。作业级批阅明细在 `grades` 表（assignment-service 维护）。将来 2.7 AI 批阅完成后，可增加「按作业成绩自动汇总」功能，将平均分写入 grade_records。