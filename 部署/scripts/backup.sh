#!/bin/bash
# ============================================
# Lumina 墨光 - 数据备份脚本
# 用法：./scripts/backup.sh
# ============================================

cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ─── 备份目录 ───
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  Lumina 墨光 · 数据备份${NC}"
echo -e "  备份时间：$DATE"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"

# ─── 检查服务 ───
if ! docker-compose ps postgres | grep -q "running"; then
    echo -e "${RED}✗ PostgreSQL 未运行，请先启动服务${NC}"
    exit 1
fi

# ─── 加载环境变量 ───
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

DB_NAME=${POSTGRES_DB:-lumina}
DB_USER=${POSTGRES_USER:-lumina}

# ─── 备份 PostgreSQL ───
echo -e "${GREEN}▶ 备份 PostgreSQL...${NC}"
docker-compose exec -T postgres pg_dump \
    -U "$DB_USER" -d "$DB_NAME" \
    --format=custom \
    -f /var/lib/postgresql/data/backup_$DATE.dump

if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✅ PostgreSQL 备份成功${NC}"
else
    echo -e "${RED}  ✗ PostgreSQL 备份失败${NC}"
fi

# ─── 复制备份到宿主机 ───
docker cp lumina-postgres:/var/lib/postgresql/data/backup_$DATE.dump "./$BACKUP_DIR/" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✅ 备份已复制到 $BACKUP_DIR/${NC}"
else
    echo -e "${YELLOW}  ⚠ 备份复制失败，请手动检查${NC}"
fi

# ─── 备份 Nginx 配置 ───
echo -e "${GREEN}▶ 备份配置文件...${NC}"
tar czf "$BACKUP_DIR/config_$DATE.tar.gz" config/ 2>/dev/null
echo -e "${GREEN}  ✅ 配置备份成功${NC}"

# ─── 清理 30 天前的备份 ───
echo -e "${GREEN}▶ 清理 30 天前的备份...${NC}"
find "$BACKUP_DIR" -name "*.dump" -mtime +30 -delete 2>/dev/null
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete 2>/dev/null
echo -e "${GREEN}  ✅ 清理完成${NC}"

# ─── 输出摘要 ───
echo -e ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✨ 备份完成！${NC}"
echo -e "─────────────────────────────────────────────────"
echo -e "  备份目录：  $BACKUP_DIR/"
ls -lh "$BACKUP_DIR" | tail -5
echo -e "${GREEN}═══════════════════════════════════════════${NC}"