#!/bin/bash
# ============================================
# Lumina 墨光 - 埋点数据查询
# 查看系统运行情况和用户行为数据
# 用法：./scripts/monitor.sh [类型]
# ============================================

cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# ─── 服务检查 ───
if ! docker-compose ps postgres | grep -q "running"; then
    echo -e "${RED}✗ PostgreSQL 未运行，请先启动服务${NC}"
    exit 1
fi

# 加载环境变量
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

DB_NAME=${POSTGRES_DB:-lumina}
DB_USER=${POSTGRES_USER:-lumina}

TYPE=${1:-all}

echo -e "${CYAN}═══════════════════════════════════════════${NC}"
echo -e "${CYAN}  Lumina 墨光 · 运行监控${NC}"
echo -e "${CYAN}═══════════════════════════════════════════${NC}"

case $TYPE in
    # ─── API 请求统计 ───
    api|请求)
        echo -e "${GREEN}▶ 最近 1 小时 API 请求统计：${NC}"
        docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -c "
            SELECT method, path, count(*) AS requests,
                   ROUND(AVG(duration_ms)) AS avg_ms,
                   MAX(duration_ms) AS max_ms,
                   count(*) FILTER (WHERE status_code >= 500) AS errors
            FROM api_logs
            WHERE created_at > now() - interval '1 hour'
            GROUP BY method, path
            ORDER BY requests DESC
            LIMIT 20;"
        ;;

    # ─── 埋点事件统计 ───
    event|埋点)
        echo -e "${GREEN}▶ 最近 24 小时用户行为事件：${NC}"
        docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -c "
            SELECT event_name, count(*) AS events,
                   count(DISTINCT user_id) AS users
            FROM event_tracking
            WHERE created_at > now() - interval '24 hours'
            GROUP BY event_name
            ORDER BY events DESC
            LIMIT 30;"
        ;;

    # ─── 用户活跃度 ───
    users|用户)
        echo -e "${GREEN}▶ 用户活跃度：${NC}"
        docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -c "
            SELECT role, count(*) AS total_users,
                   count(*) FILTER (WHERE last_login_at > now() - interval '7 days') AS active_7d
            FROM users
            GROUP BY role;"
        ;;

    # ─── AI 使用统计 ───
    ai)
        echo -e "${GREEN}▶ AI 使用统计：${NC}"
        docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -c "
            SELECT model, count(*) AS conversations,
                   SUM(total_tokens) AS total_tokens,
                   ROUND(AVG(message_count)) AS avg_messages
            FROM ai_conversations
            GROUP BY model;"
        ;;

    # ─── 数据库大小 ───
    db|容量)
        echo -e "${GREEN}▶ 数据表大小：${NC}"
        docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -c "
            SELECT tablename, pg_size_pretty(pg_total_relation_size(tablename::text)) AS size
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(tablename::text) DESC
            LIMIT 15;"
        ;;

    # ─── 错误日志 ───
    error|错误)
        echo -e "${GREEN}▶ 最近 24 小时错误：${NC}"
        docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -c "
            SELECT method, path, status_code, count(*) AS errors,
                   MAX(created_at) AS last_occurred
            FROM api_logs
            WHERE status_code >= 500
              AND created_at > now() - interval '24 hours'
            GROUP BY method, path, status_code
            ORDER BY errors DESC
            LIMIT 20;"
        ;;

    # ─── 全部 ───
    all|*)
        echo -e "${GREEN}▶ 数据库大小：${NC}"
        docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -c "
            SELECT tablename FROM pg_tables WHERE schemaname='public';" | head -20
        echo -e ""
        echo -e "${YELLOW}  查看详细： ./scripts/monitor.sh [api|event|users|ai|db|error]${NC}"
        ;;
esac

echo -e "${CYAN}═══════════════════════════════════════════${NC}"