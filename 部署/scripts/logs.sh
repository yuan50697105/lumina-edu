#!/bin/bash
# ============================================
# Lumina 墨光 - 查看服务日志
# 用法：./scripts/logs.sh [服务名]
# ============================================

cd "$(dirname "$0")/.."

SERVICE=${1:-all}

case $SERVICE in
    mysql|db)         docker-compose logs -f mysql ;;
    redis|re)         docker-compose logs -f redis ;;
    nginx|web)        docker-compose logs -f nginx ;;
    app|api)          docker-compose logs -f app ;;
    all|*)
        echo "📋 查看所有服务日志 (Ctrl+C 退出)"
        docker-compose logs -f
        ;;
esac