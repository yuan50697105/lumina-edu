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
if ! docker-compose ps mysql | grep -q "running"; then
    echo -e "${RED}✗ MySQL 未运行，请先启动服务${NC}"
    exit 1
fi

# 加载环境变量
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

DB_NAME=${MYSQL_DATABASE:-lumina}
DB_USER=${MYSQL_USER:-lumina}
export MYSQL_PWD=${MYSQL_PASSWORD:-lumina_secure_password}

# ─── MySQL 查询封装 ───
mysqlq() {
    docker-compose exec -T mysql mysql -u "$DB_USER" -D "$DB_NAME" -e "$1" 2>/dev/null
}

TYPE=${1:-all}

echo -e "${CYAN}═══════════════════════════════════════════${NC}"
echo -e "${CYAN}  Lumina 墨光 · 运行监控${NC}"
echo -e "${CYAN}═══════════════════════════════════════════${NC}"

case $TYPE in
    # ─── API 请求统计 ───
    api|请求)
        echo -e "${GREEN}▶ 最近 1 小时 API 请求统计：${NC}"
        mysqlq "
            SELECT method, path, COUNT(*) AS requests,
                   ROUND(AVG(duration_ms)) AS avg_ms,
                   MAX(duration_ms) AS max_ms,
                   SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) AS errors
            FROM api_logs
            WHERE created_at > UTC_TIMESTAMP() - INTERVAL 1 HOUR
            GROUP BY method, path
            ORDER BY requests DESC
            LIMIT 20;"
        ;;

    # ─── 埋点事件统计 ───
    event|埋点)
        echo -e "${GREEN}▶ 最近 24 小时用户行为事件：${NC}"
        mysqlq "
            SELECT event_name, COUNT(*) AS events,
                   COUNT(DISTINCT user_id) AS users
            FROM event_tracking
            WHERE created_at > UTC_TIMESTAMP() - INTERVAL 24 HOUR
            GROUP BY event_name
            ORDER BY events DESC
            LIMIT 30;"
        ;;

    # ─── 用户活跃度 ───
    users|用户)
        echo -e "${GREEN}▶ 用户活跃度：${NC}"
        mysqlq "
            SELECT role, COUNT(*) AS total_users,
                   SUM(CASE WHEN last_login_at > UTC_TIMESTAMP() - INTERVAL 7 DAY THEN 1 ELSE 0 END) AS active_7d
            FROM users
            GROUP BY role;"
        ;;

    # ─── AI 使用统计 ───
    ai)
        echo -e "${GREEN}▶ AI 使用统计：${NC}"
        mysqlq "
            SELECT model, COUNT(*) AS conversations,
                   SUM(total_tokens) AS total_tokens,
                   ROUND(AVG(message_count)) AS avg_messages
            FROM ai_conversations
            GROUP BY model;"
        ;;

    # ─── 数据库大小 ───
    db|容量)
        echo -e "${GREEN}▶ 数据表大小：${NC}"
        mysqlq "
            SELECT table_name,
                   CONCAT(ROUND((data_length + index_length) / 1024 / 1024, 2), ' MB') AS size
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            ORDER BY (data_length + index_length) DESC
            LIMIT 15;"
        ;;

    # ─── 错误日志 ───
    error|错误)
        echo -e "${GREEN}▶ 最近 24 小时错误：${NC}"
        mysqlq "
            SELECT method, path, status_code, COUNT(*) AS errors,
                   MAX(created_at) AS last_occurred
            FROM api_logs
            WHERE status_code >= 500
              AND created_at > UTC_TIMESTAMP() - INTERVAL 24 HOUR
            GROUP BY method, path, status_code
            ORDER BY errors DESC
            LIMIT 20;"
        ;;

    # ─── 全部 ───
    all|*)
        echo -e "${GREEN}▶ 数据表清单：${NC}"
        mysqlq "
            SELECT table_name, table_rows
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            ORDER BY table_name;"
        echo -e ""
        echo -e "${YELLOW}  查看详细： ./scripts/monitor.sh [api|event|users|ai|db|error]${NC}"
        ;;
esac

echo -e "${CYAN}═══════════════════════════════════════════${NC}"