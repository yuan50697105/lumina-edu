#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================
# Lumina 墨光 · 生成 MySQL 初始化脚本 init.sql
# --------------------------------------------
# 从 app/models.py（SQLAlchemy）重新编译生成 部署/config/mysql/init.sql，
# 确保 DDL 与当前模型一致（含 datetime server_default、索引）。
# 用法：
#   cd 服务/lumina-app
#   python 部署/scripts/gen_init_sql.py
# ============================================
import io
import sys
from pathlib import Path

# 支持在仓库任意目录运行（先切到 lumina-app）
ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "服务" / "lumina-app"
sys.path.insert(0, str(APP_DIR))

from sqlalchemy.dialects import mysql  # noqa: E402
from sqlalchemy.schema import CreateTable  # noqa: E402

from app.models import Base  # noqa: E402

OUT = ROOT / "部署" / "config" / "mysql" / "init.sql"


def main() -> int:
    buf = io.StringIO()
    buf.write("""-- ============================================
-- Lumina 墨光 · MySQL 9.7 初始化脚本
-- 单体应用 create_all 会自动建表；本脚本供 compose
-- /docker-entrypoint-initdb.d 或生产环境初始化使用。
-- 由 app/models.py（SQLAlchemy）自动生成，勿手工编辑；
-- 重新生成：python 部署/scripts/gen_init_sql.py
-- ============================================

""")
    for t in Base.metadata.sorted_tables:
        ddl = str(CreateTable(t).compile(dialect=mysql.dialect()))
        buf.write(ddl + ";\n\n")
        for ix in t.indexes:
            cols = ", ".join(c.name for c in ix.columns)
            buf.write(f"CREATE INDEX {ix.name} ON {t.name} ({cols});\n\n")

    sql = buf.getvalue()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(sql, encoding="utf-8")
    print(f"已生成 {OUT.relative_to(ROOT)}")
    print(f"  CREATE TABLE: {len(Base.metadata.tables)} 张")
    print(f"  INDEX:        {sql.count('CREATE INDEX')} 个")
    print(f"  server_default(时间): {sql.count('CURRENT_TIMESTAMP')} 处")
    return 0


if __name__ == "__main__":
    sys.exit(main())