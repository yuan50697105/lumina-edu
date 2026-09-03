# ============================================
# Lumina 墨光 · D-06 自主学习路由
# 学习路径 / 闯关挑战 / XP / 打卡 / 徽章 / 排行榜
# ============================================
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, get_current_user
from app.models import (
    LearningPath, LearningPathNode, LearningPathProgress,
    UserXP, CheckInRecord, Badge, UserBadge,
    Challenge, ChallengeAttempt, User,
)
from app.schemas import (
    LearningPathOut, LearningPathNodeOut,
    UserXPOut, CheckInOut, CheckInCalendarOut,
    BadgeOut, ChallengeOut, ChallengeStartOut, ChallengeSubmitIn, ChallengeResultOut,
    LeaderboardOut, LeaderboardEntry, LearningStatsOut,
)

router = APIRouter(prefix="/learning", tags=["自主学习（D-06）"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_or_create_xp(db: Session, user_id: str) -> UserXP:
    """获取或初始化用户 XP 记录"""
    xp = db.query(UserXP).filter(UserXP.user_id == user_id).first()
    if not xp:
        xp = UserXP(user_id=user_id, total_xp=0, level=1, streak_days=0)
        db.add(xp)
        db.commit()
        db.refresh(xp)
    return xp


def _calculate_level(total_xp: int) -> tuple[int, int, int]:
    """计算等级：每 100 XP 升一级，返回 (level, current_level_xp, xp_to_next)"""
    level = total_xp // 100 + 1
    current_level_xp = total_xp % 100
    xp_to_next = 100
    return level, current_level_xp, xp_to_next


# ═══════════════════════════════════════════════════════════════════
# 1. 学习路径
# ═══════════════════════════════════════════════════════════════════

@router.get("/paths", response_model=list[LearningPathOut], summary="学习路径列表")
def list_paths(
    category: Optional[str] = Query(None, description="分类过滤"),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取所有已发布的学习路径"""
    q = db.query(LearningPath).filter(LearningPath.published == True)
    if category:
        q = q.filter(LearningPath.category == category)
    paths = q.order_by(LearningPath.created_at.desc()).all()

    # 计算当前用户进度
    out = []
    for p in paths:
        total_nodes = db.query(LearningPathNode).filter(
            LearningPathNode.path_id == p.id
        ).count()
        done_nodes = db.query(LearningPathProgress).filter(
            LearningPathProgress.user_id == user.id,
            LearningPathProgress.path_id == p.id,
            LearningPathProgress.status == "done",
        ).count()
        progress_pct = (done_nodes / total_nodes * 100) if total_nodes > 0 else 0

        out.append(LearningPathOut(
            id=p.id, title=p.title, description=p.description,
            category=p.category, difficulty=p.difficulty,
            cover_emoji=p.cover_emoji, cover_gradient=p.cover_gradient,
            total_nodes=p.total_nodes or total_nodes,
            total_xp=p.total_xp, learner_count=p.learner_count,
            progress_pct=round(progress_pct, 1),
            created_at=p.created_at,
        ))
    return out


@router.get("/paths/{path_id}", response_model=list[LearningPathNodeOut], summary="路径节点列表（地图）")
def list_path_nodes(
    path_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取路径下所有节点及当前用户状态"""
    path = db.query(LearningPath).filter(LearningPath.id == path_id).first()
    if not path:
        raise HTTPException(status_code=404, detail="路径不存在")

    nodes = db.query(LearningPathNode).filter(
        LearningPathNode.path_id == path_id
    ).order_by(LearningPathNode.sequence).all()

    out = []
    for n in nodes:
        progress = db.query(LearningPathProgress).filter(
            LearningPathProgress.user_id == user.id,
            LearningPathProgress.node_id == n.id,
        ).first()

        # 自动解锁逻辑：第一个节点默认 current，后续节点根据前一节点 done 解锁
        if progress:
            node_status = progress.status
            xp_earned = progress.xp_earned
            completed_at = progress.completed_at
        else:
            # 检查是否应该解锁
            prev_nodes = db.query(LearningPathProgress).filter(
                LearningPathProgress.user_id == user.id,
                LearningPathProgress.path_id == path_id,
                LearningPathProgress.status == "done",
            ).count()
            if n.sequence == 1 or prev_nodes >= n.sequence - 1:
                node_status = "current"
                # 初始化进度记录
                progress = LearningPathProgress(
                    user_id=user.id, path_id=path_id, node_id=n.id,
                    status="current", xp_earned=0,
                )
                db.add(progress)
            else:
                node_status = "locked"
            xp_earned = 0
            completed_at = None

        out.append(LearningPathNodeOut(
            id=n.id, path_id=n.path_id, sequence=n.sequence,
            node_type=n.node_type, title=n.title, description=n.description,
            duration_min=n.duration_min, xp_reward=n.xp_reward,
            status=node_status, xp_earned=xp_earned, completed_at=completed_at,
        ))

    db.commit()
    return out


@router.post("/paths/{path_id}/join", summary="加入学习路径")
def join_path(
    path_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """加入路径，learner_count +1"""
    path = db.query(LearningPath).filter(LearningPath.id == path_id).first()
    if not path:
        raise HTTPException(status_code=404, detail="路径不存在")

    # 检查是否已加入
    existing = db.query(LearningPathProgress).filter(
        LearningPathProgress.user_id == user.id,
        LearningPathProgress.path_id == path_id,
    ).first()
    if existing:
        return {"message": "已加入该路径", "already_joined": True}

    # 增加 learner_count
    path.learner_count = (path.learner_count or 0) + 1
    db.commit()
    return {"message": "成功加入路径", "already_joined": False}


# ═══════════════════════════════════════════════════════════════════
# 2. 经验值 / 等级
# ═══════════════════════════════════════════════════════════════════

@router.get("/xp", response_model=UserXPOut, summary="获取用户经验值")
def get_user_xp(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户 XP、等级、连续打卡天数"""
    xp = _get_or_create_xp(db, user.id)
    level, current_xp, xp_to_next = _calculate_level(xp.total_xp)
    level_progress_pct = (current_xp / 100) * 100

    return UserXPOut(
        user_id=xp.user_id,
        total_xp=xp.total_xp,
        level=xp.level,
        streak_days=xp.streak_days,
        last_checkin_date=xp.last_checkin_date,
        xp_to_next_level=xp_to_next - current_xp,
        level_progress_pct=round(level_progress_pct, 1),
    )


# ═══════════════════════════════════════════════════════════════════
# 3. 打卡签到
# ═══════════════════════════════════════════════════════════════════

@router.post("/checkin", response_model=CheckInOut, summary="每日打卡")
def daily_checkin(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """每日打卡 +10 XP，连续打卡天数 +1"""
    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 检查今日是否已打卡
    existing = db.query(CheckInRecord).filter(
        CheckInRecord.user_id == user.id,
        CheckInRecord.checkin_date == today_start,
    ).first()
    if existing:
        xp = _get_or_create_xp(db, user.id)
        return CheckInOut(
            success=False,
            message="今日已打卡，明天继续！",
            xp_awarded=0,
            streak_days=xp.streak_days,
            already_checked=True,
        )

    # 创建打卡记录
    record = CheckInRecord(user_id=user.id, checkin_date=today_start, xp_awarded=10)
    db.add(record)

    # 更新 XP
    xp = _get_or_create_xp(db, user.id)
    xp.total_xp += 10
    xp.streak_days += 1
    xp.last_checkin_date = today_start
    xp.level, _, _ = _calculate_level(xp.total_xp)

    db.commit()

    return CheckInOut(
        success=True,
        message="🔥 打卡成功 +10 XP",
        xp_awarded=10,
        streak_days=xp.streak_days,
        already_checked=False,
    )


@router.get("/checkin/calendar", response_model=CheckInCalendarOut, summary="打卡日历")
def checkin_calendar(
    days: int = Query(30, ge=7, le=90, description="查询天数"),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """近 N 天打卡记录"""
    now = _now()
    start_date = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

    records = db.query(CheckInRecord).filter(
        CheckInRecord.user_id == user.id,
        CheckInRecord.checkin_date >= start_date,
    ).all()

    checked_dates = {r.checkin_date.date() for r in records}
    day_list = []
    for i in range(days):
        d = (now - timedelta(days=days - 1 - i)).date()
        day_list.append({
            "date": d.isoformat(),
            "checked": d in checked_dates,
            "xp": 10 if d in checked_dates else 0,
        })

    xp = _get_or_create_xp(db, user.id)
    return CheckInCalendarOut(
        days=day_list,
        total_checked=len(checked_dates),
        current_streak=xp.streak_days,
    )


# ═══════════════════════════════════════════════════════════════════
# 4. 徽章
# ═══════════════════════════════════════════════════════════════════

@router.get("/badges", response_model=list[BadgeOut], summary="徽章列表")
def list_badges(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """所有徽章，标记当前用户已获得"""
    badges = db.query(Badge).all()
    user_badges = {ub.badge_id: ub.earned_at for ub in db.query(UserBadge).filter(
        UserBadge.user_id == user.id
    ).all()}

    out = []
    for b in badges:
        out.append(BadgeOut(
            id=b.id, code=b.code, name=b.name, description=b.description,
            icon=b.icon, condition_type=b.condition_type,
            condition_value=b.condition_value,
            earned=b.id in user_badges,
            earned_at=user_badges.get(b.id),
        ))
    return out


# ═══════════════════════════════════════════════════════════════════
# 5. 闯关挑战
# ═══════════════════════════════════════════════════════════════════

@router.get("/challenges/{challenge_id}", response_model=ChallengeOut, summary="挑战详情")
def get_challenge(
    challenge_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取挑战信息（不含题目答案）"""
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="挑战不存在")

    # 计算剩余尝试次数
    attempts = db.query(ChallengeAttempt).filter(
        ChallengeAttempt.user_id == user.id,
        ChallengeAttempt.challenge_id == challenge_id,
    ).count()
    attempts_left = max(0, challenge.max_attempts - attempts)

    questions = challenge.questions or []
    return ChallengeOut(
        id=challenge.id, node_id=challenge.node_id,
        title=challenge.title, description=challenge.description,
        time_limit_min=challenge.time_limit_min,
        question_count=len(questions),
        max_attempts=challenge.max_attempts,
        pass_score=challenge.pass_score,
        xp_reward=challenge.xp_reward,
        attempts_left=attempts_left,
    )


@router.post("/challenges/{challenge_id}/start", response_model=ChallengeStartOut, summary="开始闯关")
def start_challenge(
    challenge_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """开始闯关，返回题目（不含答案）"""
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="挑战不存在")

    # 检查尝试次数
    attempts = db.query(ChallengeAttempt).filter(
        ChallengeAttempt.user_id == user.id,
        ChallengeAttempt.challenge_id == challenge_id,
    ).count()
    if attempts >= challenge.max_attempts:
        raise HTTPException(status_code=400, detail="已达最大尝试次数")

    # 创建尝试记录
    attempt = ChallengeAttempt(user_id=user.id, challenge_id=challenge_id)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    # 返回题目（不含答案）
    questions = challenge.questions or []
    questions_no_answer = [
        {"index": i, "q": q.get("q", ""), "options": q.get("options", [])}
        for i, q in enumerate(questions)
    ]

    return ChallengeStartOut(
        challenge_id=challenge.id,
        title=challenge.title,
        time_limit_min=challenge.time_limit_min,
        questions=questions_no_answer,
        attempt_id=attempt.id,
    )


@router.post("/challenges/attempts/{attempt_id}/submit", response_model=ChallengeResultOut, summary="提交闯关答案")
def submit_challenge(
    attempt_id: str,
    payload: ChallengeSubmitIn,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交答案，自动评分"""
    attempt = db.query(ChallengeAttempt).filter(ChallengeAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="尝试记录不存在")
    if attempt.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作")
    if attempt.submitted_at:
        raise HTTPException(status_code=400, detail="已提交过")

    challenge = db.query(Challenge).filter(Challenge.id == attempt.challenge_id).first()
    questions = challenge.questions or []

    # 评分
    correct_count = 0
    answers_review = []
    user_answers = {a["index"]: a["answer"] for a in payload.answers}

    for i, q in enumerate(questions):
        user_ans = user_answers.get(i)
        correct_ans = q.get("answer")
        is_correct = user_ans == correct_ans
        if is_correct:
            correct_count += 1
        answers_review.append({
            "index": i,
            "q": q.get("q", ""),
            "your_answer": user_ans,
            "correct_answer": correct_ans,
            "is_correct": is_correct,
        })

    total_count = len(questions)
    score = int((correct_count / total_count) * 100) if total_count > 0 else 0
    passed = score >= challenge.pass_score

    # 更新尝试记录
    attempt.answers = payload.answers
    attempt.score = score
    attempt.passed = passed
    attempt.xp_earned = challenge.xp_reward if passed else 0
    attempt.submitted_at = _now()

    # 如果通过，增加 XP
    if passed:
        xp = _get_or_create_xp(db, user.id)
        xp.total_xp += attempt.xp_earned
        xp.level, _, _ = _calculate_level(xp.total_xp)

    db.commit()

    return ChallengeResultOut(
        attempt_id=attempt.id,
        score=score,
        passed=passed,
        xp_earned=attempt.xp_earned,
        correct_count=correct_count,
        total_count=total_count,
        answers_review=answers_review,
    )


# ═══════════════════════════════════════════════════════════════════
# 6. 排行榜
# ═══════════════════════════════════════════════════════════════════

@router.get("/leaderboard", response_model=LeaderboardOut, summary="排行榜")
def get_leaderboard(
    limit: int = Query(50, ge=1, le=100),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """XP 排行榜"""
    entries = db.query(UserXP).order_by(UserXP.total_xp.desc()).limit(limit).all()

    result = []
    my_rank = None
    for i, xp in enumerate(entries, 1):
        u = db.query(User).filter(User.id == xp.user_id).first()
        result.append(LeaderboardEntry(
            rank=i,
            user_id=xp.user_id,
            name=u.name if u else "Unknown",
            total_xp=xp.total_xp,
            level=xp.level,
            streak_days=xp.streak_days,
        ))
        if xp.user_id == user.id:
            my_rank = i

    total_users = db.query(UserXP).count()
    return LeaderboardOut(entries=result, my_rank=my_rank, total_users=total_users)


# ═══════════════════════════════════════════════════════════════════
# 7. 学习统计（成就页）
# ═══════════════════════════════════════════════════════════════════

@router.get("/stats", response_model=LearningStatsOut, summary="学习统计汇总")
def get_learning_stats(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """成就页统计"""
    xp = _get_or_create_xp(db, user.id)

    paths_completed = db.query(LearningPathProgress).filter(
        LearningPathProgress.user_id == user.id,
        LearningPathProgress.status == "done",
    ).with_entities(LearningPathProgress.path_id).distinct().count()

    paths_total = db.query(LearningPath).filter(LearningPath.published == True).count()

    badges_earned = db.query(UserBadge).filter(UserBadge.user_id == user.id).count()
    badges_total = db.query(Badge).count()

    challenges_passed = db.query(ChallengeAttempt).filter(
        ChallengeAttempt.user_id == user.id,
        ChallengeAttempt.passed == True,
    ).count()

    from app.models import VideoWatchHistory
    videos_watched = db.query(VideoWatchHistory).filter(
        VideoWatchHistory.user_id == user.id,
        VideoWatchHistory.progress_pct >= 90,
    ).count()

    from app.models import Video
    videos_total = db.query(Video).filter(Video.published == True).count()

    return LearningStatsOut(
        total_xp=xp.total_xp,
        level=xp.level,
        streak_days=xp.streak_days,
        paths_completed=paths_completed,
        paths_total=paths_total,
        badges_earned=badges_earned,
        badges_total=badges_total,
        challenges_passed=challenges_passed,
        videos_watched=videos_watched,
        videos_total=videos_total,
    )
