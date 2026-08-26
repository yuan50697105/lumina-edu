# Lumina 墨光 · 基础日志系统 (logs-service)

## 职责

- **日志检索**：`GET /api/v1/logs/query`（admin）按条件检索共享表 `api_logs`
- **日志统计**：`GET /api/v1/logs/summary`（admin）总体指标 + TOP 路径
- **结构化日志规范**：`app/logging_json.py` 提供 JSONLines 格式化器，供全部服务统一接入

## 快速开始

```bash
# 依赖
pip install -r requirements.txt

# 本地开发（默认 DATABASE_URL 指向 localhost:5432）
uvicorn app.main:app --port 8097 --reload
```

## 接口

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/health` | 公开 | 健康检查 |
| GET | `/api/v1/logs/query` | admin | `days`(≤365) `method` `path_contains` `status` `request_id` `user_id` `limit`(≤200) `offset` |
| GET | `/api/v1/logs/summary` | admin | `total/errors/error_rate/avg/max/top_paths` |

## 结构化 JSON 日志接入

任一行接入（详见 `scripts/log_json.py` 演示与 `scripts/README.md`）：

```python
from logging_json import install_json_logging
install_json_logging()          # main.py 一处启用

logger.error("批阅失败", extra={"request_id": req_id}, exc_info=True)
```

输出每行一个 JSON：`ts/level/logger/message/module/func/line/thread` +
扩展字段 `request_id/user_id/service` + 异常 `traceback`，中文 UTF-8。

## 测试

```bash
# 纯净单测（无需数据库）：分页钳制 / 过滤构造 / JSON 格式化
python -m pytest tests/test_logs.py -q

# 集成测试需 PostgreSQL（未就绪自动跳过）
python -m pytest tests/ -q
```

端口 `8097`，Docker HEALTHCHECK 检查 `/health`。