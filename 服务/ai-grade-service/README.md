# Lumina 墨光 · ai-grade-service AI 批阅服务

FastAPI 辅助批阅：对作业提交调用 LLM 按评分标准（rubric）逐项评分，结构化输出 + 写 `grades` 表。

## 功能

- **AI 辅助批阅** `POST /ai/grade`：校验作业/提交归属 → 调网关（task_type=grade）→ 模型按 rubric 返回 JSON → 容错解析 → 写入 `grades` 表（graded_by=ai）→ 返回结构化成绩
- **可配置评分标准**：请求携带 rubric（维度/权重/满分），缺省复用作业 rubric
- **模型选择**：`model_name` / `X-Model` 头指定，缺省走网关智能路由（grade 场景）
- **批阅准确率埋点**：`ai.grade_start/done/error`（置信度、总分、维度数、token、延迟）

## 路由表

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/ai/grade` | AI 辅助批阅（结构化成绩） | 教师/管理员 |

## 请求/响应示例

```bash
curl -X POST http://localhost:8095/api/v1/ai/grade \
  -H "Authorization: Bearer <teacher_token>" -H "Content-Type: application/json" \
  -d '{
    "assignment_id": "a001", "submission_id": "s123",
    "rubric": [{"criteria":"解题过程完整","weight":0.4,"max_score":40},
               {"criteria":"答案正确","weight":0.4,"max_score":40},
               {"criteria":"书写规范","weight":0.2,"max_score":20}]
  }'
```

```json
{
  "code": 0,
  "data": {
    "scores": [{"criteria": "解题过程完整", "score": 36, "max": 40, "comment": "步骤完整"},
               {"criteria": "答案正确", "score": 38, "max": 40, "comment": "结果正确"},
               {"criteria": "书写规范", "score": 18, "max": 20, "comment": "基本规范"}],
    "total": 92, "feedback": "整体思路清晰…", "model": "qwen-max", "confidence": 0.93
  }
}
```

## 架构说明

- **容错解析**：`prompt.py` 的 `extract_json` 兼容 ```json 围栏/前导文字/尾注；`parse_grade_result` 防御缺字段与越界——分数 clamp 到 [0, max]，置信度 clamp 到 [0,1]，坏条目跳过
- **对接网关**：`gateway_client.py` 消费 `/gateway/route`（route task_type=**grade**）+ `/gateway/completions`（**非流式**，批阅为结构化输出）；用户 JWT 透传，用量归属教师
- **grades 表**：按 `submission_id` 唯一 upsert（重复批阅覆盖，不冲突）；`graded_by='ai'`、`grader_id`、`ai_model`、`confidence`、`rubric_scores` 落库
- **权限**：教师/管理员可批阅；学生 403；作业不存在/提交不匹配 404
- **共享库/JWT**：与其它服务同一 PostgreSQL + 同一 `JWT_SECRET_KEY`

## 本地运行

前置：PostgreSQL + ai-gateway:8093（模型池已配置）。

```bash
cd ../服务/ai-grade-service
../user-service/.venv/Scripts/pip install -r requirements.txt
export DATABASE_URL="postgresql://lumina:lumina_secure_password@localhost:5432/lumina"
export AI_GATEWAY_URL="http://localhost:8093"
../user-service/.venv/Scripts/uvicorn app.main:app --reload --port 8095
```

## 测试

```bash
../user-service/.venv/Scripts/python -m pytest tests/test_grade.py -q   # 单测（无需 DB/网关）
../user-service/.venv/Scripts/python -m pytest tests/ -q               # 集成（需 PG + 网关）
```

## Docker 部署

随 `部署/docker-compose.yml` 编排（`lumina-ai-grade`，:8095），内部 `AI_GATEWAY_URL=http://ai-gateway-service:8093`。Nginx `/api/v1/ai/grade` → 本服务。