# Lumina 墨光 · 部署方案（轻量版）

轻量级一键部署方案，用于初期上线。基于 Docker Compose，无需 Kubernetes 和复杂运维。

## 📋 架构

```
┌─────────────┐
│   Nginx     │  HTTP/HTTPS · 静态原型 · API 代理
│  :80 / :443 │
└──────┬──────┘
       │
┌──────▼────────────────────────────────────┐
│       应用服务（未来）                      │
│       /api/v1/*                           │
└──────┬────────────────────────────────────┘
       │
┌──────▼──────┐  ┌──────────┐  ┌────────────┐
│ PostgreSQL  │  │  Redis   │  │   MinIO    │
│   数据库    │  │  缓存     │  │  对象存储  │
└─────────────┘  └──────────┘  └────────────┘
```

## 🚀 快速开始

### 1. 环境要求

```bash
# Docker 版本
docker --version        # ≥ 20.10
docker-compose --version # ≥ 2.0
```

### 2. 配置环境变量

```bash
cd 部署
cp .env.example .env
vim .env   # 修改所有密码
```

### 3. 唯一 API 密钥克隆

```bash
# （可选）如果使用 Nginx HTTPS，需要 SSL 证书
mkdir -p ssl
# 将证书放入 ssl/ 目录
# fullchain.pem · privkey.pem
```

### 4. 启动服务

```bash
./scripts/start.sh
```

### 5. 验证服务

```bash
./scripts/status.sh    # 查看服务状态
./scripts/monitor.sh   # 查看运行数据
```

## 📦 服务清单

| 服务 | 端口 | 说明 | 数据卷 |
|------|------|------|--------|
| PostgreSQL | 5432 | 数据库 | postgres_data |
| Redis | 6379 | 缓存 | redis_data |
| MinIO | 9000 | 对象存储 | minio_data |
| MinIO Console | 9001 | 控制台 | — |
| Nginx | 80/443 | 反向代理 | — |

## 📜 常用命令

```bash
# 服务管理
./scripts/start.sh        # 启动所有服务
./scripts/stop.sh         # 停止所有服务
./scripts/status.sh       # 查看状态
./scripts/logs.sh         # 查看日志
./scripts/logs.sh nginx   # 查看指定服务日志

# 数据管理
./scripts/backup.sh       # 备份数据库和配置
./scripts/monitor.sh      # 查看运行监控数据
./scripts/monitor.sh api  # 查看 API 请求统计

# Docker 直接操作
docker-compose ps           # 查看状态
docker-compose down         # 停止
docker-compose down -v      # 停止并删除数据
docker-compose logs -f      # 实时日志
```

## 🎯 监控埋点

系统内置监控埋点，无需额外部署监控组件：

### API 日志
所有 API 请求自动记录到 `api_logs` 表
- 方法 · 路径 · 状态码 · 响应时间
- 用户 ID · 请求 ID · 错误信息

### 用户行为事件
业务代码中调用埋点记录到 `event_tracking` 表
- 事件名称（登录/选课/提交/批阅）
- 用户 · 会话 · 页面 · 属性

### 查询示例

```sql
-- 最近 1 小时慢请求
SELECT path, AVG(duration_ms) FROM api_logs
WHERE created_at > now() - interval '1 hour'
GROUP BY path ORDER BY AVG(duration_ms) DESC LIMIT 10;

-- 今日活跃用户
SELECT COUNT(DISTINCT user_id) FROM event_tracking
WHERE created_at > now() - interval '24 hours';
```

## 🔄 数据备份

```bash
# 手动备份
./scripts/backup.sh

# 定时备份（crontab 示例，每天凌晨 2 点）
0 2 * * * cd /d/projects/edu/部署 && ./scripts/backup.sh >> backups/backup.log 2>&1
```

备份文件保留 30 天，自动清理。

## 🚧 后期演进

用户量增长后，按需演进：

| 阶段 | 触发条件 | 演进内容 |
|------|---------|---------|
| **阶段 1** | 用户 > 2000 | 增加 Nginx 缓存 · 数据库读写分离 |
| **阶段 2** | 用户 > 5000 | 引入 K8s · 自动化 CI/CD |
| **阶段 3** | 用户 > 10000 | 微服务拆分 · 独立监控体系 |

## 🔒 安全注意事项

1. **修改默认密码**：部署后立即修改 `.env` 中所有密码
2. **限制端口暴露**：生产环境仅对外开放 80/443
3. **定期备份**：配置 crontab 自动备份
4. **更新镜像**：定期 `docker-compose pull` 更新基础镜像
5. **监控告警**：定期查看 `monitor.sh` 输出，或配置通知