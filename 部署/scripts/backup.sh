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
if ! docker-compose ps mysql | grep -q "running"; then
    echo -e "${RED}✗ MySQL 未运行，请先启动服务${NC}"
    exit 1
fi

# ─── 加载环境变量 ───
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

DB_NAME=${MYSQL_DATABASE:-lumina}
DB_USER=${MYSQL_USER:-lumina}

# ─── 备份 MySQL ───
echo -e "${GREEN}▶ 备份 MySQL...${NC}"
docker-compose exec -T -e MYSQL_PWD="${MYSQL_PASSWORD:-lumina_secure_password}" mysql mysqldump \
    -u "$DB_USER" "$DB_NAME" \
    --single-transaction --routines --triggers \
    > "$BACKUP_DIR/lumina_$DATE.sql"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✅ MySQL 备份成功 → $BACKUP_DIR/lumina_$DATE.sql${NC}"
else
    echo -e "${RED}  ✗ MySQL 备份失败${NC}"
fi

# ─── 备份 Nginx 配置 ───
echo -e "${GREEN}▶ 备份配置文件...${NC}"
tar czf "$BACKUP_DIR/config_$DATE.tar.gz" config/ 2>/dev/null
echo -e "${GREEN}  ✅ 配置备份成功${NC}"

# ─── 清理 30 天前的备份 ───
echo -e "${GREEN}▶ 清理 30 天前的备份...${NC}"
find "$BACKUP_DIR" -name "*.sql" -mtime +30 -delete 2>/dev/null
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