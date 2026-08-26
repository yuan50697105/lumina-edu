#!/bin/bash
# ============================================
# Lumina 墨光 - 服务状态检查
# ============================================

cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}═══════════════════════════════════════════${NC}"
echo -e "${CYAN}  Lumina 墨光 · 服务状态${NC}"
echo -e "${CYAN}═══════════════════════════════════════════${NC}"

# ─── 服务状态 ───
docker-compose ps

echo -e ""

# ─── 资源使用 ───
echo -e "${CYAN}▶ 资源使用：${NC}"
docker stats --no-stream --format "  {{.Name}}  CPU: {{.CPUPerc}}  MEM: {{.MemUsage}}"

echo -e ""

# ─── 服务健康检查 ───
echo -e "${CYAN}▶ 服务健康检查：${NC}"

# PostgreSQL
if curl -s http://localhost:5432 >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅ PostgreSQL: 运行中${NC}"
else
    echo -e "  ${RED}✗ PostgreSQL: 未就绪${NC}"
fi

# Redis
if curl -s http://localhost:6379 >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Redis: 运行中${NC}"
else
    echo -e "  ${RED}✗ Redis: 未就绪${NC}"
fi

# MinIO
if curl -s http://localhost:9000/minio/health/live >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅ MinIO: 运行中${NC}"
else
    echo -e "  ${RED}✗ MinIO: 未就绪${NC}"
fi

# Nginx
if curl -s http://localhost/health >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Nginx: 运行中${NC}"
else
    echo -e "  ${RED}✗ Nginx: 未就绪${NC}"
fi

# ─── 磁盘使用 ───
echo -e ""
echo -e "${CYAN}▶ 磁盘使用：${NC}"
docker system df

echo -e "${CYAN}═══════════════════════════════════════════${NC}"