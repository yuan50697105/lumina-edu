#!/bin/bash
# ============================================
# Lumina 墨光 - 一键启动脚本
# ============================================

set -e
cd "$(dirname "$0")"

# ─── 颜色 ───
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  Lumina 墨光 · 服务启动${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"

# ─── 检查 .env ───
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ 未找到 .env 文件，正在从模板创建...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠ 请编辑 .env 文件，修改默认密码后重新运行${NC}"
    exit 1
fi

# ─── 检查配置文件 ───
if [ ! -f "config/nginx/conf.d/lumina.conf" ]; then
    echo -e "${RED}✗ 缺少 Nginx 配置${NC}"
    exit 1
fi

if [ ! -f "config/postgresql/init.sql" ]; then
    echo -e "${RED}✗ 缺少 PostgreSQL 初始化脚本${NC}"
    exit 1
fi

# ─── 启动服务 ───
echo -e "${GREEN}▶ 启动所有服务...${NC}"
docker-compose up -d

# ─── 等待服务就绪 ───
echo -e "${GREEN}▶ 等待服务就绪...${NC}"
sleep 5

# 检查 PostgreSQL
echo -e "${GREEN}▶ 检查 PostgreSQL...${NC}"
if docker-compose ps postgres | grep -q "healthy"; then
    echo -e "${GREEN}  ✅ PostgreSQL 就绪${NC}"
else
    echo -e "${YELLOW}  ⏳ PostgreSQL 启动中，请稍候...${NC}"
fi

# 检查 Redis
echo -e "${GREEN}▶ 检查 Redis...${NC}"
if docker-compose ps redis | grep -q "healthy"; then
    echo -e "${GREEN}  ✅ Redis 就绪${NC}"
else
    echo -e "${YELLOW}  ⏳ Redis 启动中，请稍候...${NC}"
fi

# 检查 MinIO
echo -e "${GREEN}▶ 检查 MinIO...${NC}"
if docker-compose ps minio | grep -q "healthy"; then
    echo -e "${GREEN}  ✅ MinIO 就绪${NC}"
else
    echo -e "${YELLOW}  ⏳ MinIO 启动中，请稍候...${NC}"
fi

# 检查 Nginx
echo -e "${GREEN}▶ 检查 Nginx...${NC}"
if docker-compose ps nginx | grep -q "healthy"; then
    echo -e "${GREEN}  ✅ Nginx 就绪${NC}"
else
    echo -e "${GREEN}  ✅ Nginx 启动${NC}"
fi

# ─── 输出状态 ───
echo -e ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✨ 所有服务已启动！${NC}"
echo -e "─────────────────────────────────────────────────"
echo -e "  📄 原型页面：  http://localhost:80"
echo -e "  📦 MinIO 控制台：http://localhost:9001"
echo -e "  📧 PostgreSQL：  localhost:5432"
echo -e "  🔄 Redis：       localhost:6379"
echo -e "─────────────────────────────────────────────────"
echo -e "  查看状态：  ./scripts/status.sh"
echo -e "  查看日志：  ./scripts/logs.sh"
echo -e "  停止服务：  ./scripts/stop.sh"
echo -e "  备份数据：  ./scripts/backup.sh"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"