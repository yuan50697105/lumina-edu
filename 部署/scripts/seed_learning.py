#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lumina 墨光 · D-06 种子数据脚本
生成学习路径、关卡、徽章、每日挑战等测试数据
幂等可重复运行
"""
import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '服务', 'lumina-app'))

from app.database import get_db
from app.models import (
    LearningPath, LearningPathNode, LearningPathProgress,
    UserXP, CheckInRecord, Badge, UserBadge,
    Challenge, ChallengeAttempt
)
from app.models import User
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid

def generate_guid() -> str:
    return str(uuid.uuid4())

def seed_badges(db: Session):
    """创建 18 枚徽章"""
    badges = [
        {"code": "xp_100", "name": "初露锋芒", "description": "累计获得 100 XP", "icon": "🌱", "condition_type": "xp_threshold", "condition_value": 100},
        {"code": "xp_1000", "name": "千分俱乐部", "description": "累计获得 1000 XP", "icon": "💎", "condition_type": "xp_threshold", "condition_value": 1000},
        {"code": "xp_10000", "name": "万点宗师", "description": "累计获得 10000 XP", "icon": "🚀", "condition_type": "xp_threshold", "condition_value": 10000},
        {"code": "xp_50000", "name": "学海无涯", "description": "累计获得 50000 XP", "icon": "", "condition_type": "xp_threshold", "condition_value": 50000},
        {"code": "streak_7", "name": "七日成习", "description": "连续打卡 7 天", "icon": "🔥", "condition_type": "streak", "condition_value": 7},
        {"code": "streak_30", "name": "月度坚持", "description": "连续打卡 30 天", "icon": "", "condition_type": "streak", "condition_value": 30},
        {"code": "streak_100", "name": "百日修行", "description": "连续打卡 100 天", "icon": "🏆", "condition_type": "streak", "condition_value": 100},
        {"code": "path_1", "name": "单线突破", "description": "完成 1 条学习路径", "icon": "🎯", "condition_type": "path_complete", "condition_value": 1},
        {"code": "path_10", "name": "博学者", "description": "完成 10 条学习路径", "icon": "📚", "condition_type": "path_complete", "condition_value": 10},
        {"code": "path_all", "name": "全科制霸", "description": "在每个分类下各完成 1 条路径", "icon": "🎓", "condition_type": "path_complete_all", "condition_value": 4},
        {"code": "challenge_10", "name": "答题新秀", "description": "答对 10 次每日挑战", "icon": "⚡", "condition_type": "challenge_master", "condition_value": 10},
        {"code": "challenge_100", "name": "常胜将军", "description": "答对 100 次每日挑战", "icon": "️", "condition_type": "challenge_master", "condition_value": 100},
        {"code": "challenge_streak_50", "name": "百步穿杨", "description": "连续答对 50 题", "icon": "🏹", "condition_type": "challenge_streak", "condition_value": 50},
        {"code": "first_login", "name": "墨光初识", "description": "首次登录学习系统", "icon": "👋", "condition_type": "first_login", "condition_value": 1},
        {"code": "first_stage", "name": "破冰者", "description": "完成第一个关卡", "icon": "🧊", "condition_type": "first_stage", "condition_value": 1},
        {"code": "path_conqueror", "name": "路径征服者", "description": "完成任意路径的全部关卡", "icon": "🏆", "condition_type": "path_complete_first", "condition_value": 1},
        {"code": "night_owl", "name": "夜猫子", "description": "在 22:00 后完成一个关卡", "icon": "🦉", "condition_type": "special", "condition_value": 0},
        {"code": "speed_run", "name": "闪电通关", "description": "30 分钟内完成一个测验", "icon": "⚡", "condition_type": "special", "condition_value": 0},
    ]

    for b in badges:
        existing = db.query(Badge).filter(Badge.code == b["code"]).first()
        if not existing:
            badge = Badge(**b, created_at=datetime.now())
            db.add(badge)
    db.commit()
    print(f"✅ 徽章：{len(badges)} 枚")

def seed_learning_paths(db: Session, teacher_id: str):
    """创建 3 条示范学习路径"""
    paths = [
        {
            "title": "Python 入门闯关",
            "description": "从零开始学习 Python 编程，通过 12 个关卡掌握基础语法、数据类型、控制流和函数。",
            "category": "编程",
            "difficulty": "入门",
            "cover_emoji": "🐍",
            "cover_gradient": "linear-gradient(135deg,#3D46C9,#7C3AED)",
            "nodes": [
                {"title": "变量与数据类型", "node_type": "reading", "xp_reward": 40, "duration_min": 6, "sequence": 1},
                {"title": "条件与循环（视频）", "node_type": "video", "xp_reward": 50, "duration_min": 12, "sequence": 2},
                {"title": "小测验：控制流", "node_type": "quiz", "xp_reward": 30, "duration_min": 5, "sequence": 3},
                {"title": "函数与作用域", "node_type": "reading", "xp_reward": 40, "duration_min": 8, "sequence": 4},
                {"title": "列表与切片", "node_type": "reading", "xp_reward": 50, "duration_min": 9, "sequence": 5},
                {"title": "小测验：容器类型", "node_type": "quiz", "xp_reward": 30, "duration_min": 5, "sequence": 6},
                {"title": "字典与集合（视频）", "node_type": "video", "xp_reward": 50, "duration_min": 11, "sequence": 7},
                {"title": "挑战：学生成绩统计", "node_type": "challenge", "xp_reward": 80, "duration_min": 20, "sequence": 8},
                {"title": "文件读写入门", "node_type": "reading", "xp_reward": 40, "duration_min": 8, "sequence": 9},
                {"title": "阶段测验（一）", "node_type": "quiz", "xp_reward": 40, "duration_min": 7, "sequence": 10},
                {"title": "挑战：猜数字游戏", "node_type": "challenge", "xp_reward": 80, "duration_min": 18, "sequence": 11},
                {"title": "毕业挑战：迷你记账本", "node_type": "challenge", "xp_reward": 100, "duration_min": 30, "sequence": 12},
            ]
        },
        {
            "title": "UI 设计思维 100 问",
            "description": "通过 100 个设计问题，培养 UI/UX 设计思维，掌握配色、排版、布局等核心原则。",
            "category": "设计",
            "difficulty": "入门",
            "cover_emoji": "🎨",
            "cover_gradient": "linear-gradient(135deg,#E85D3A,#F5B800)",
            "nodes": [
                {"title": "设计原则概述", "node_type": "reading", "xp_reward": 30, "duration_min": 5, "sequence": 1},
                {"title": "色彩理论基础", "node_type": "video", "xp_reward": 40, "duration_min": 10, "sequence": 2},
                {"title": "小测验：色彩搭配", "node_type": "quiz", "xp_reward": 30, "duration_min": 5, "sequence": 3},
                {"title": "排版与字体", "node_type": "reading", "xp_reward": 40, "duration_min": 8, "sequence": 4},
                {"title": "布局与网格系统", "node_type": "video", "xp_reward": 50, "duration_min": 12, "sequence": 5},
                {"title": "挑战：redesign 一个页面", "node_type": "challenge", "xp_reward": 80, "duration_min": 25, "sequence": 6},
                {"title": "交互设计基础", "node_type": "reading", "xp_reward": 40, "duration_min": 7, "sequence": 7},
                {"title": "毕业挑战：完整设计方案", "node_type": "challenge", "xp_reward": 100, "duration_min": 40, "sequence": 8},
            ]
        },
        {
            "title": "英语学术写作",
            "description": "提升英语学术写作能力，从论文结构到引用规范，全面掌握学术写作技巧。",
            "category": "语言",
            "difficulty": "进阶",
            "cover_emoji": "️",
            "cover_gradient": "linear-gradient(135deg,#2A7F4F,#94C97A)",
            "nodes": [
                {"title": "学术论文结构", "node_type": "reading", "xp_reward": 40, "duration_min": 8, "sequence": 1},
                {"title": "引言写作技巧", "node_type": "video", "xp_reward": 50, "duration_min": 15, "sequence": 2},
                {"title": "文献综述方法", "node_type": "reading", "xp_reward": 50, "duration_min": 12, "sequence": 3},
                {"title": "小测验：引用格式", "node_type": "quiz", "xp_reward": 30, "duration_min": 5, "sequence": 4},
                {"title": "数据分析与结果呈现", "node_type": "video", "xp_reward": 60, "duration_min": 18, "sequence": 5},
                {"title": "讨论与结论", "node_type": "reading", "xp_reward": 50, "duration_min": 10, "sequence": 6},
                {"title": "挑战：撰写摘要", "node_type": "challenge", "xp_reward": 80, "duration_min": 30, "sequence": 7},
                {"title": "同行评审模拟", "node_type": "challenge", "xp_reward": 100, "duration_min": 45, "sequence": 8},
                {"title": "毕业挑战：完整论文草稿", "node_type": "challenge", "xp_reward": 150, "duration_min": 60, "sequence": 9},
            ]
        },
    ]

    for p in paths:
        existing = db.query(LearningPath).filter(LearningPath.title == p["title"]).first()
        if existing:
            print(f"️  跳过已存在的路径：{p['title']}")
            continue

        path_id = generate_guid()
        total_xp = sum(n["xp_reward"] for n in p["nodes"])

        path = LearningPath(
            id=path_id,
            title=p["title"],
            description=p["description"],
            category=p["category"],
            difficulty=p["difficulty"],
            cover_emoji=p["cover_emoji"],
            cover_gradient=p["cover_gradient"],
            total_nodes=len(p["nodes"]),
            total_xp=total_xp,
            learner_count=0,
            published=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.add(path)

        for n in p["nodes"]:
            node = LearningPathNode(
                id=generate_guid(),
                path_id=path_id,
                title=n["title"],
                node_type=n["node_type"],
                xp_reward=n["xp_reward"],
                duration_min=n["duration_min"],
                sequence=n["sequence"],
                created_at=datetime.now(),
            )
            db.add(node)

    db.commit()
    print(f"✅ 学习路径：{len(paths)} 条")

def seed_daily_challenges(db: Session, teacher_id: str):
    """创建 7 天每日挑战"""
    today = datetime.now().date()

    challenges = [
        {"title": "Python 基础", "questions": [{"q": "Python 中哪个不是不可变类型？", "options": ["tuple", "str", "list", "frozenset"], "answer": "list"}], "xp_reward": 20},
        {"title": "设计原则", "questions": [{"q": "以下哪个不是设计四大基本原则？", "options": ["对比", "重复", "对齐", "渐变"], "answer": "渐变"}], "xp_reward": 20},
        {"title": "英语语法", "questions": [{"q": "Which sentence is grammatically correct?", "options": ["He don't like apples.", "He doesn't likes apples.", "He doesn't like apples.", "He not like apples."], "answer": "He doesn't like apples."}], "xp_reward": 20},
        {"title": "数据结构", "questions": [{"q": "栈的特点是？", "options": ["先进先出", "后进先出", "随机访问", "有序存储"], "answer": "后进先出"}], "xp_reward": 20},
        {"title": "算法思维", "questions": [{"q": "二分查找的时间复杂度是？", "options": ["O(n)", "O(log n)", "O(n²)", "O(1)"], "answer": "O(log n)"}], "xp_reward": 20},
        {"title": "心理学", "questions": [{"q": "马斯洛需求层次理论的最高层是？", "options": ["安全需求", "社交需求", "尊重需求", "自我实现"], "answer": "自我实现"}], "xp_reward": 20},
        {"title": "经济学", "questions": [{"q": "GDP 是指？", "options": ["国民生产总值", "国内生产总值", "国民收入", "人均收入"], "answer": "国内生产总值"}], "xp_reward": 20},
    ]

    for i, c in enumerate(challenges):
        active_date = today + timedelta(days=i)
        existing = db.query(Challenge).filter(Challenge.title == c["title"]).first()
        if existing:
            continue

        challenge = Challenge(
            id=generate_guid(),
            title=c["title"],
            description=f"每日挑战 - {active_date.isoformat()}",
            questions=c["questions"],
            xp_reward=c["xp_reward"],
            time_limit_min=30,
            max_attempts=3,
            pass_score=60,
            created_at=datetime.now(),
        )
        db.add(challenge)

    db.commit()
    print(f"✅ 每日挑战：{len(challenges)} 天")

def main():
    print("=" * 50)
    print("Lumina 墨光 · D-06 种子数据")
    print("=" * 50)

    db = next(get_db())

    try:
        # 获取教师用户 ID（使用 seed_demo.py 创建的教师账号）
        teacher = db.query(User).filter(User.email == "teacher@lumina.edu").first()
        if not teacher:
            print("❌ 未找到教师账号 teacher@lumina.edu，请先运行 seed_demo.py")
            return

        print(f"\n👤 使用教师账号：{teacher.name} ({teacher.email})")

        print("\n📝 创建徽章...")
        seed_badges(db)

        print("\n️  创建学习路径...")
        seed_learning_paths(db, teacher.id)

        print("\n 创建每日挑战...")
        seed_daily_challenges(db, teacher.id)

        print("\n" + "=" * 50)
        print("✅ 种子数据创建完成！")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 错误：{e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
