#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================
# Lumina 墨光 · 演示数据种子脚本（幂等版）
# --------------------------------------------
# MySQL 9.7 就绪后运行；幂等：已存在的账号/课程/关联记录会被复用，
# 不会重复插入（重复运行输出「已存在，复用」）。
# 用法：
#   python 部署/scripts/seed_demo.py
#   python 部署/scripts/seed_demo.py --demo-password xxxx
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

    def scalar(sql: str, **kw):
        row = conn.execute(text(sql), kw).fetchone()
        return row[0] if row else None

    def ensure(sql_select: str, sel: dict, sql_insert: str, params: dict, label: str):
        """查询存在则复用，否则插入新记录；返回实体主键"""
        existing = scalar(sql_select, **sel)
        if existing is not None:
            print(f"  ── {label}（已存在，复用）")
            return existing
        eid = str(uuid.uuid4())
        conn.execute(text(sql_insert), {**params, "id": eid})
        print(f"  ✅ {label}")
        return eid

    pw_hash = hash_password(args.demo_password)

    # ── 1. 用户 ──
    admin_id = ensure("SELECT id FROM users WHERE email=:e", {"e": "admin@lumina.edu"},
        "INSERT IGNORE INTO users (id,name,email,password_hash,role) VALUES (:id,'系统管理员',:e,:pw,'admin')",
        {"e": "admin@lumina.edu", "pw": pw_hash}, "管理员 admin@lumina.edu")
    teacher_id = ensure("SELECT id FROM users WHERE email=:e", {"e": "teacher@lumina.edu"},
        "INSERT IGNORE INTO users (id,name,email,password_hash,role,student_id) VALUES (:id,'李教授',:e,:pw,'teacher','T20260001')",
        {"e": "teacher@lumina.edu", "pw": pw_hash}, "教师 teacher@lumina.edu")
    student_id = ensure("SELECT id FROM users WHERE email=:e", {"e": "student@lumina.edu"},
        "INSERT IGNORE INTO users (id,name,email,password_hash,role,student_id) VALUES (:id,'张同学',:e,:pw,'student','20260001')",
        {"e": "student@lumina.edu", "pw": pw_hash}, "学生 student@lumina.edu")
    # 未选课学生（越权/权限校验专用：直播加入 403、课程权限等）
    ensure("SELECT id FROM users WHERE email=:e", {"e": "nouser@lumina.edu"},
        "INSERT IGNORE INTO users (id,name,email,password_hash,role) VALUES (:id,'未选课学生',:e,:pw,'student')",
        {"e": "nouser@lumina.edu", "pw": pw_hash}, "未选课学生 nouser@lumina.edu（越权测试）")

    # ── 2. 课程 ──
    course_id = ensure("SELECT id FROM courses WHERE code='CS101'", {},
        "INSERT IGNORE INTO courses (id,code,title,description,semester,teacher_id,credits,students_count,status) "
        "VALUES (:id,'CS101','墨光程序设计基础','示例课程：用于功能演示与冒烟测试','2026-1',:tid,3,0,'published')",
        {"tid": teacher_id}, "课程 CS101 墨光程序设计基础")

    # ── 3. 章节 ──
    for i, (title, content) in enumerate([
        ("第一章 概述", "课程介绍、学习目标、考核方式"),
        ("第二章 基础语法", "变量、数据类型、控制流、函数"),
        ("第三章 数据结构", "列表、字典、集合、元组"),
    ], start=1):
        ensure(
            "SELECT id FROM chapters WHERE course_id=:cid AND order_num=:ord",
            {"cid": course_id, "ord": i - 1},
            "INSERT IGNORE INTO chapters (id,course_id,title,content,order_num) VALUES (:id,:cid,:title,:content,:ord)",
            {"cid": course_id, "title": title, "content": content, "ord": i - 1},
            f"章节 {i}")

    # ── 4. 选课 ──
    ensure("SELECT id FROM enrollments WHERE user_id=:uid AND course_id=:cid",
        {"uid": student_id, "cid": course_id},
        "INSERT IGNORE INTO enrollments (id,user_id,course_id,role,status,enrolled_at) "
        "VALUES (:id,:uid,:cid,'student','active',NOW())",
        {"uid": student_id, "cid": course_id}, "选课")

    # ── 5. 作业 ──
    assignment_id = ensure("SELECT id FROM assignments WHERE course_id=:cid AND title='冒烟测试作业'",
        {"cid": course_id},
        "INSERT IGNORE INTO assignments (id,course_id,title,description,max_score,due_at,status) "
        "VALUES (:id,:cid,'冒烟测试作业','请提交你的程序代码',100,NOW() + INTERVAL 7 DAY,'published')",
        {"cid": course_id}, "作业 冒烟测试作业")

    # ── 6. 提交 ──
    submission_id = ensure("SELECT id FROM submissions WHERE assignment_id=:aid AND student_id=:sid",
        {"aid": assignment_id, "sid": student_id},
        "INSERT IGNORE INTO submissions (id,assignment_id,student_id,text_answer,submitted_at) "
        'VALUES (:id,:aid,:sid,\'print("Hello Lumina")\',NOW())',
        {"aid": assignment_id, "sid": student_id}, "提交")

    # ── 7. 批阅 ──
    ensure("SELECT id FROM grades WHERE submission_id=:sid",
        {"sid": submission_id},
        "INSERT IGNORE INTO grades (id,submission_id,total_score,feedback,graded_by,graded_at) "
        "VALUES (:id,:sid,95,'优秀，逻辑清晰','teacher',NOW())",
        {"sid": submission_id}, "批阅 95 分")

    # ── 8. 期末成绩（存在则更新，保证幂等）──
    gr = scalar("SELECT id FROM grade_records WHERE student_id=:sid AND course_id=:cid AND semester='2026-1'",
                sid=student_id, cid=course_id)
    if gr:
        conn.execute(text("UPDATE grade_records SET final_score=92, gpa_point=4.0 WHERE id=:i"), {"i": gr})
        print("  ── 期末成绩 92 (A)（已存在，更新）")
    else:
        conn.execute(text(
            "INSERT INTO grade_records (id,student_id,course_id,semester,final_score,gpa_point,recorded_at) "
            "VALUES (:gid,:sid,:cid,'2026-1',92,4.0,NOW())"
        ), {"gid": str(uuid.uuid4()), "sid": student_id, "cid": course_id})
        print("  ✅ 期末成绩 92 (A)")

    # ── 9. 直播演示房间（固定流 roomdemo，配合 部署/stream 演示推流一键起流）──
    ensure("SELECT id FROM live_rooms WHERE stream_key='roomdemo'", {},
        "INSERT IGNORE INTO live_rooms (id,course_id,teacher_id,title,status,stream_key,viewer_count,created_at) "
        "VALUES (:id,:cid,:tid,'直播演示间（固定流 roomdemo）','scheduled','roomdemo',0,NOW())",
        {"cid": course_id, "tid": teacher_id}, "直播演示房间 roomdemo")

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