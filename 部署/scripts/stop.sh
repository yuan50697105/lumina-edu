#!/bin/bash
# ============================================
# Lumina 墨光 - 停止服务脚本
# ============================================

cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}▶ 停止所有服务...${NC}"

# ─── 停止服务 ───
docker-compose down

# ─── 提示数据卷保留 ───
echo -e "${YELLOW}ℹ 数据卷已保留（mysql_data / redis_data）${NC}"
echo -e "${YELLOW}  如需完全清理： docker-compose down -v${NC}"

echo -e "${GREEN}✅ 服务已停止${NC}"