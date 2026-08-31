#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================
# Lumina 墨光 · 演示数据种子脚本
# --------------------------------------------
# MySQL 9.7 就绪后运行，插入 admin/teacher/student 账号 + 示例课程/作业。
# 用法：
#   python 部署/scripts/seed_demo.py
#   python 部署/scripts/seed_demo.py --database-url mysql+pymysql://user:pw@host:3306/db
# ============================================
import argparse
import os
import sys
import uuid

from sqlalchemy import create_engine, text


def hash_password(plain: str) -> str:
    import bcrypt
    return bcrypt.hashpw(plain.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", default=os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://lumina:lumina_secure_password@localhost:3306/lumina?charset=utf8mb4"))
    ap.add_argument("--demo-password", default="Demo@2026", help="演示账号通用密码")
    args = ap.parse_args()

    print(f"连接数据库: {args.database_url.split('@')[-1]}")
    try:
        engine = create_engine(args.database_url, pool_pre_ping=True)
        conn = engine.connect()
    except Exception as exc:
        print(f"❌ 连接数据库失败：{exc}")
        return 1

    pw_hash = hash_password(args.demo_password)
    admin_id = str(uuid.uuid4())
    teacher_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())

    def seed(sql: str, params: dict, label: str) -> bool:
        """执行插入并输出 ✅/──（基于影响行数）"""
        result = conn.execute(text(sql), params)
        ok = result.rowcount > 0
        print(f"  {'✅' if ok else '──'} {label}")
        return ok

    # ── 1. 用户 ──
    for uid, name, email, role, sid in [
        (admin_id, "系统管理员", "admin@lumina.edu", "admin", None),
        (teacher_id, "李教授", "teacher@lumina.edu", "teacher", "T20260001"),
        (student_id, "张同学", "student@lumina.edu", "student", "20260001"),
    ]:
        seed("""
            INSERT IGNORE INTO users (id, name, email, password_hash, role, student_id)
            VALUES (:id, :name, :email, :pw, :role, :sid)
        """, {"id": uid, "name": name, "email": email, "pw": pw_hash,
              "role": role, "sid": sid},
            f"{role:7} {name} ({email})")

    # ── 2. 课程 ──
    course_id = str(uuid.uuid4())
    seed("""
        INSERT IGNORE INTO courses (id, code, title, description, semester, teacher_id, credits, students_count, status)
        VALUES (:id, 'CS101', '墨光程序设计基础', '示例课程：用于功能演示与冒烟测试', '2026-1', :tid, 3, 0, 'published')
    """, {"id": course_id, "tid": teacher_id}, "课程 CS101 墨光程序设计基础")

    # ── 3. 章节 ──
    for i, (title, content) in enumerate([
        ("第一章 概述", "课程介绍、学习目标、考核方式"),
        ("第二章 基础语法", "变量、数据类型、控制流、函数"),
        ("第三章 数据结构", "列表、字典、集合、元组"),
    ], start=1):
        seed("""
            INSERT IGNORE INTO chapters (id, course_id, title, content, order_num)
            VALUES (:id, :cid, :title, :content, :ord)
        """, {"id": str(uuid.uuid4()), "cid": course_id, "title": title,
              "content": content, "ord": i - 1}, f"章节 {i}")
    print("  ✅ 章节 x3")

    # ── 4. 选课 ──
    seed("""
        INSERT IGNORE INTO enrollments (id, user_id, course_id, role, status, enrolled_at)
        VALUES (:id, :sid, :cid, 'student', 'active', NOW())
    """, {"id": str(uuid.uuid4()), "sid": student_id, "cid": course_id},
        f"选课 {student_id[:8]}")

    # ── 5. 作业 ──
    assignment_id = str(uuid.uuid4())
    seed("""
        INSERT IGNORE INTO assignments (id, course_id, title, description, max_score, due_at, status)
        VALUES (:id, :cid, '冒烟测试作业', '请提交你的程序代码', 100, NOW() + INTERVAL 7 DAY, 'published')
    """, {"id": assignment_id, "cid": course_id}, "作业 冒烟测试作业")

    # ── 6. 提交 ──
    submission_id = str(uuid.uuid4())
    seed("""
        INSERT IGNORE INTO submissions (id, assignment_id, student_id, text_answer, submitted_at)
        VALUES (:id, :aid, :sid, 'print("Hello Lumina")', NOW())
    """, {"id": submission_id, "aid": assignment_id, "sid": student_id},
        f"提交 {student_id[:8]}")

    # ── 7. 批阅 ──
    seed("""
        INSERT IGNORE INTO grades (id, submission_id, total_score, feedback, graded_by, graded_at)
        VALUES (:id, :sid, 95, '优秀，逻辑清晰', 'teacher', NOW())
    """, {"id": str(uuid.uuid4()), "sid": submission_id}, "批阅 95 分")

    # ── 8. 期末成绩（幂等 upsert）──
    seed("""
        INSERT INTO grade_records (id, student_id, course_id, semester, final_score, gpa_point, recorded_at)
        VALUES (:id, :sid, :cid, '2026-1', 92, 4.0, NOW()) AS new
        ON DUPLICATE KEY UPDATE final_score = new.final_score, gpa_point = new.gpa_point
    """, {"id": str(uuid.uuid4()), "sid": student_id, "cid": course_id}, "期末成绩 92 (A)")

    conn.commit()
    conn.close()
    engine.dispose()

    print(f"\n{'='*50}")
    print("演示账号（密码：", args.demo_password, "）：")
    print(f"  管理员: admin@lumina.edu")
    print(f"  教师:   teacher@lumina.edu  (工号 T20260001)")
    print(f"  学生:   student@lumina.edu  (学号 20260001)")
    print("课程：CS101 墨光程序设计基础 · 作业 已布置 · 选课 已完成 · 成绩 已录入")
    return 0


if __name__ == "__main__":
    sys.exit(main())