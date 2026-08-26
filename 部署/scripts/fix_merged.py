#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 修复合并后的 models.py 和 schemas.py：去重重写
import re
from pathlib import Path

TARGET = Path(r"D:\projects\edu\服务\lumina-app\app")


def extract_classes(text: str, pattern: str) -> dict[str, str]:
    """提取所有 class 定义（到下一个 class 或文件末尾）"""
    classes = {}
    # 找到每个 class 的起始位置
    starts = [(m.start(), m.group(1)) for m in re.finditer(pattern, text)]
    for i, (start, name) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        block = text[start:end].rstrip() + "\n"
        if name not in classes:  # 只保留第一个定义
            classes[name] = block
    return classes


def rewrite_models():
    all_classes = {}
    imports = set()

    for mod in (TARGET / "modules").iterdir():
        mf = mod / "models.py"
        if not mf.exists():
            continue
        text = mf.read_text(encoding="utf-8")
        # 收集 import 行
        for line in text.splitlines():
            if line.startswith(("from ", "import ")) and "models" not in line:
                imports.add(line)
        # 提取 class
        classes = extract_classes(text, r"class\s+(\w+)\(.*Base\).*:")
        all_classes.update(classes)

    # 共享表优先级：先定义 APILog/EventTracking/UserBrief/CourseBrief
    priority = ["APILog", "EventTracking", "UserBrief", "CourseBrief", "User", "Session", "Course", "Enrollment", "Chapter", "Announcement", "Assignment", "Submission", "Grade", "GradeRecord", "AIProvider", "AIModel", "AICallLog", "AIConversation", "AIMessage"]

    lines = [
        "# ============================================",
        "# Lumina 墨光 · 统一数据模型（合并 9 微服务）",
        "# ============================================",
        "from datetime import datetime, timezone",
        "",
        "from sqlalchemy import (",
        "    BigInteger, Boolean, Column, DateTime, Float, Integer, String, Text, Numeric,",
        "    ForeignKey, UniqueConstraint, Index",
        ")",
        "from sqlalchemy.dialects.postgresql import UUID, JSONB",
        "from sqlalchemy.orm import relationship",
        "",
        "from app.database import Base",
        "",
        "",
    ]

    # 按优先级顺序写入
    written = set()
    for name in priority:
        if name in all_classes:
            lines.append(all_classes[name])
            written.add(name)

    # 写入剩余
    for name, block in sorted(all_classes.items()):
        if name not in written:
            lines.append(block)

    (TARGET / "models.py").write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ models.py 重写完成：{len(all_classes)} 个 class（去重后）")


def rewrite_schemas():
    all_classes = {}
    imports = set()

    for mod in (TARGET / "modules").iterdir():
        sf = mod / "schemas.py"
        if not sf.exists():
            continue
        text = sf.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith(("from ", "import ")) and "schemas" not in line:
                imports.add(line)
        classes = extract_classes(text, r"class\s+(\w+)\(.*BaseModel\).*:")
        all_classes.update(classes)

    lines = [
        "# ============================================",
        "# Lumina 墨光 · 统一 Pydantic Schemas（合并 9 微服务）",
        "# ============================================",
        "from datetime import datetime",
        "from decimal import Decimal",
        "from typing import Any, Optional",
        "",
        "from pydantic import BaseModel, Field",
        "",
        "",
    ]

    # 先写基础类
    priority = ["SuccessResponse", "Pagination"]
    written = set()
    for name in priority:
        if name in all_classes:
            lines.append(all_classes[name])
            written.add(name)
    for name, block in sorted(all_classes.items()):
        if name not in written:
            lines.append(block)

    (TARGET / "schemas.py").write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ schemas.py 重写完成：{len(all_classes)} 个 class（去重后）")


if __name__ == "__main__":
    rewrite_models()
    rewrite_schemas()
    print("运行 python -c 'from app.main import app; print(len(app.routes))' 验证")