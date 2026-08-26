#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================
# Lumina 墨光 · 演示数据种子脚本
# --------------------------------------------
# PostgreSQL 就绪后运行，插入 admin/teacher/student 账号 + 示例课程/作业。
# 用法：
#   python 部署/scripts/seed_demo.py
#   python 部署/scripts/seed_demo.py --database-url postgresql://user:pw@host:5432/db
# ============================================
import argparse
import os
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def hash_password(plain: str) -> str:
    try:
        from passlib.hash import bcrypt
        return bcrypt.hash(plain)
    except ImportError:
        import bcrypt as _b
        return _b.hashpw(plain.encode("utf-8"), _b.gensalt()).decode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", default=os.getenv("DATABASE_URL",
                    "postgresql://lumina:lumina_secure_password@localhost:5432/lumina"))
    ap.add_argument("--demo-password", default="Demo@2026", help="演示账号通用密码")
    args = ap.parse_args()

    try:
        import psycopg2
    except ImportError:
        print("❌ 需要 psycopg2：pip install psycopg2-binary")
        return 1

    print(f"连接数据库: {args.database_url.split('@')[-1]}")
    conn = psycopg2.connect(args.database_url)
    conn.autocommit = True
    cur = conn.cursor()

    pw_hash = hash_password(args.demo_password)
    admin_id = str(uuid.uuid4())
    teacher_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())

    # ── 1. 用户 ──
    for uid, name, email, role, sid in [
        (admin_id, "系统管理员", "admin@lumina.edu", "admin", None),
        (teacher_id, "李教授", "teacher@lumina.edu", "teacher", "T20260001"),
        (student_id, "张同学", "student@lumina.edu", "student", "20260001"),
    ]:
        cur.execute("""
            INSERT INTO users (id, name, email, password_hash, role, student_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        """, (uid, name, email, pw_hash, role, sid))
        print(f"  {'✅' if cur.rowcount else '──'} {role:7} {name} ({email})")

    # ── 2. 课程 ──
    course_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO courses (id, code, title, description, semester, teacher_id, credits, students_count, status)
        VALUES (%s, 'CS101', '墨光程序设计基础', '示例课程：用于功能演示与冒烟测试', '2026-1', %s, 3, 0, 'published')
        ON CONFLICT DO NOTHING
    """, (course_id, teacher_id))
    print(f"  {'✅' if cur.rowcount else '──'} 课程 CS101 墨光程序设计基础")

    # ── 3. 章节 ──
    for i, (title, content) in enumerate([
        ("第一章 概述", "课程介绍、学习目标、考核方式"),
        ("第二章 基础语法", "变量、数据类型、控制流、函数"),
        ("第三章 数据结构", "列表、字典、集合、元组"),
    ], start=1):
        ch_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO chapters (id, course_id, title, content, order_num)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (ch_id, course_id, title, content, i - 1))
    print("  ✅ 章节 x3")

    # ── 4. 选课 ──
    cur.execute("""
        INSERT INTO enrollments (id, student_id, course_id, status)
        VALUES (%s, %s, %s, 'enrolled')
        ON CONFLICT (student_id, course_id) DO NOTHING
    """, (str(uuid.uuid4()), student_id, course_id))
    print(f"  {'✅' if cur.rowcount else '──'} 选课 {student_id[:8]}")

    # ── 5. 作业 ──
    assignment_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO assignments (id, course_id, title, description, max_score, due_at, status)
        VALUES (%s, %s, '冒烟测试作业', '请提交你的程序代码', 100, now() + interval '7 days', 'published')
        ON CONFLICT DO NOTHING
    """, (assignment_id, course_id))
    print(f"  {'✅' if cur.rowcount else '──'} 作业 冒烟测试作业")

    # ── 6. 提交 ──
    submission_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO submissions (id, assignment_id, student_id, text_answer)
        VALUES (%s, %s, %s, 'print("Hello Lumina")')
        ON CONFLICT DO NOTHING
    """, (submission_id, assignment_id, student_id))
    print(f"  {'✅' if cur.rowcount else '──'} 提交 {student_id[:8]}")

    # ── 7. 批阅 ──
    cur.execute("""
        INSERT INTO grades (id, submission_id, total_score, feedback, graded_by)
        VALUES (%s, %s, 95, '优秀，逻辑清晰', 'teacher')
        ON CONFLICT (submission_id) DO NOTHING
    """, (str(uuid.uuid4()), submission_id))
    print("  ✅ 批阅 95 分")

    # ── 8. 期末成绩 ──
    cur.execute("""
        INSERT INTO grade_records (id, student_id, course_id, semester, final_score, gpa_point)
        VALUES (%s, %s, %s, '2026-1', 92, 4.0)
        ON CONFLICT (student_id, course_id, semester) DO UPDATE SET final_score = EXCLUDED.final_score
    """, (str(uuid.uuid4()), student_id, course_id))
    print("  ✅ 期末成绩 92 (A)")

    cur.close()
    conn.close()

    print(f"\n{'='*50}")
    print("演示账号（密码：", args.demo_password, "）：")
    print(f"  管理员: admin@lumina.edu")
    print(f"  教师:   teacher@lumina.edu  (工号 T20260001)")
    print(f"  学生:   student@lumina.edu  (学号 20260001)")
    print("课程：CS101 墨光程序设计基础 · 作业 已布置 · 选课 已完成 · 成绩 已录入")
    return 0


if __name__ == "__main__":
    sys.exit(main())