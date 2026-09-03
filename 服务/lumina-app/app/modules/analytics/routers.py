# ============================================
# Lumina 墨光 · 埋点收集服务路由
# POST /events 收集（游客/登录） · GET 统计（admin）
# ============================================
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, require_role
from app.models import EventTracking
from app.schemas import (
    BreakdownRow,
    EventBatch,
    EventIn,
    StatsOut,
    SuccessResponse,
)

logger = logging.getLogger("lumina.analytics")

router = APIRouter(tags=["埋点收集与统计"])


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()[:45]
    if request.client:
        return request.client.host
    return None


def _cell_uuid(value) -> uuid.UUID | None:
    """把可能的 UUID 字符串转 UUID；非法返回 None"""
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _resolve_user(request: Request, payload: EventIn) -> uuid.UUID | None:
    """身份解析：登录用户以 JWT 为准，游客用客户端 user_id（需合法 UUID）"""
    token = request.headers.get("authorization", "")
    if token.startswith("Bearer "):
        from app.security import decode_token
        data = decode_token(token[7:])
        if data and data.get("type") == "access" and data.get("sub"):
            try:
                return uuid.UUID(data["sub"])
            except ValueError:
                pass
    return _cell_uuid(payload.user_id)


def _to_row(request: Request, payload: EventIn, user_id: uuid.UUID | None) -> EventTracking:
    props = dict(payload.properties or {})
    course_id = _cell_uuid(props.get("course_id"))
    if course_id is not None:
        props.pop("course_id", None)   # 仅提升合法 UUID，非法保留在 properties
    return EventTracking(
        event_name=payload.event_name,
        user_id=user_id,
        session_id=payload.session_id,
        course_id=course_id,
        properties=props or None,
        page_url=payload.page_url,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )


# ─── 事件收集（游客可访问，fire-and-forget）───
@router.post("/events", response_model=SuccessResponse, status_code=202, summary="上报单条事件")
def ingest_event(
    payload: EventIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """上报埋点事件。登录用户由 JWT 覆盖身份；游客信任客户端 user_id。返回 202 不保证落库。"""
    user_id = _resolve_user(request, payload)
    db.add(_to_row(request, payload, user_id))
    db.commit()
    return SuccessResponse()


@router.post("/events/batch", response_model=SuccessResponse, status_code=202, summary="批量上报事件（≤100）")
def ingest_batch(
    payload: EventBatch,
    request: Request,
    db: Session = Depends(get_db),
):
    """批量落库，单事务。任一事件含 properties.course_id 会提升为列。"""
    rows = []
    for ev in payload.events:
        rows.append(_to_row(request, ev, _resolve_user(request, ev)))
    db.add_all(rows)
    db.commit()
    return SuccessResponse()


# ─── 统计查询（admin）───
@router.get("/events/stats", response_model=StatsOut, summary="事件统计概览（管理员）")
def stats(
    request: Request,
    admin: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    event_name: str | None = None,
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = db.query(
        func.count(EventTracking.id),
        func.count(func.distinct(EventTracking.user_id)),
        func.count(func.distinct(EventTracking.session_id)),
        func.min(EventTracking.created_at),
        func.max(EventTracking.created_at),
    ).filter(EventTracking.created_at >= since)
    if event_name:
        q = q.filter(EventTracking.event_name == event_name)
    (total, users, sessions, first_seen, last_seen) = q.first()
    return StatsOut(
        total=total or 0,
        distinct_users=users or 0,
        distinct_sessions=sessions or 0,
        first_seen=first_seen,
        last_seen=last_seen,
    )


@router.get("/events/breakdown", response_model=list[BreakdownRow], summary="事件类型分布（管理员）")
def breakdown(
    request: Request,
    admin: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(
            EventTracking.event_name,
            func.count(EventTracking.id).label("cnt"),
            func.count(func.distinct(EventTracking.user_id)).label("users"),
        )
        .filter(EventTracking.created_at >= since)
        .group_by(EventTracking.event_name)
        .order_by(func.count(EventTracking.id).desc())
        .limit(limit)
        .all()
    )
    return [BreakdownRow(event_name=r[0], count=r[1], distinct_users=r[2]) for r in rows]


# ═══════════════════════════════════════════════════════════════════
# D-05 · 学情分析 / 学生档案 / 风险预警
# 数据源：enrollments / assignments / submissions / grades /
#         grade_records / exam_attempts / live_attendees /
#         event_tracking / users / risk_alerts / learning_insights
# ═══════════════════════════════════════════════════════════════════
from fastapi import HTTPException, status
from sqlalchemy import and_, case, distinct, text as sa_text

from app.dependencies import AuthUser, get_current_user
from app.models import (
    Assignment,
    Course,
    CourseBrief,
    Enrollment,
    EventTracking,
    ExamAttempt,
    ExamPaper,
    Grade,
    GradeRecord,
    LearningInsight,
    LiveAttendee,
    LiveRoom,
    RiskAlert,
    Submission,
    TutoringSession,
    User,
)
from app.schemas import (
    AlertRuleIn,
    CourseDistributionOut,
    CourseInsightsOut,
    CourseOverviewOut,
    CourseProgressOut,
    CourseRisksOut,
    CourseTrendOut,
    DistributionBucket,
    InsightOut,
    ProgressStudent,
    RiskAlertOut,
    RiskStudent,
    StudentProfileOut,
    TrendPoint,
)

analytics_router = APIRouter(prefix="/analytics", tags=["学情分析（D-05）"])


# ─── 通用工具 ───
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_course(db: Session, course_id) -> CourseBrief:
    c = db.get(CourseBrief, course_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    return c


def _check_course_teacher(db: Session, course: CourseBrief, user: AuthUser) -> None:
    if user.role == "admin":
        return
    if user.role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅教师/管理员可查看学情")
    if str(course.teacher_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该课程学情")


def _is_enrolled(db: Session, course_id, student_id) -> bool:
    row = db.execute(
        sa_text("SELECT 1 FROM enrollments WHERE course_id = :c AND user_id = :s AND status='active'"),
        {"c": str(course_id), "s": str(student_id)},
    ).first()
    return bool(row)


def _iso_week(dt: datetime) -> str:
    """返回 ISO 周字符串 'YYYY-Www'"""
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


# ─── 1. 课程学情概览 ───
@analytics_router.get("/courses/{course_id}/overview", response_model=CourseOverviewOut,
                      summary="课程学情概览（教师）")
def course_overview(
    course_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, course_id)
    _check_course_teacher(db, course, user)

    # 选课学生数
    student_count = db.query(func.count(Enrollment.user_id)).filter(
        Enrollment.course_id == course_id,
        Enrollment.role == "student",
        Enrollment.status == "active",
    ).scalar() or 0

    # 均分（作业 + 考试）
    avg_grade = db.query(func.avg(Grade.total_score)).join(
        Submission, Submission.id == Grade.submission_id
    ).join(
        Assignment, Assignment.id == Submission.assignment_id
    ).filter(Assignment.course_id == course_id).scalar()
    avg_exam = db.query(func.avg(ExamAttempt.total_score)).filter(
        ExamAttempt.status == "submitted",
        ExamAttempt.paper_id.in_(
            db.query(ExamPaper.id).filter(ExamPaper.course_id == course_id)
        )
    ).scalar()
    # 综合均分：作业 0.6 + 考试 0.4（仅在有数据时）
    avg_score: float | None
    if avg_grade and avg_exam:
        avg_score = 0.6 * float(avg_grade) + 0.4 * float(avg_exam)
    elif avg_grade:
        avg_score = float(avg_grade)
    elif avg_exam:
        avg_score = float(avg_exam)
    else:
        avg_score = None

    # 出勤率（直播参加率）
    total_live = db.query(func.count(LiveAttendee.id)).join(
        LiveRoom, LiveRoom.id == LiveAttendee.room_id
    ).filter(LiveRoom.course_id == course_id, LiveAttendee.role == "student").scalar() or 0
    attend_rate = (total_live / max(student_count, 1)) if student_count else None
    if attend_rate and attend_rate > 1:
        attend_rate = min(attend_rate / max(1, db.query(func.count(LiveRoom.id)).filter(LiveRoom.course_id == course_id).scalar() or 1), 1.0)

    # 作业完成率
    total_subs = db.query(func.count(distinct(Submission.student_id))).join(
        Assignment, Assignment.id == Submission.assignment_id
    ).filter(Assignment.course_id == course_id).scalar() or 0
    submission_rate = min(total_subs / max(student_count, 1), 1.0) if student_count else None

    # 风险学生数
    risk_q = db.query(
        RiskAlert.level,
        func.count(distinct(RiskAlert.student_id)),
    ).filter(
        RiskAlert.course_id == course_id,
        RiskAlert.resolved == False,  # noqa: E712
    ).group_by(RiskAlert.level).all()
    risk_map = {lvl: cnt for lvl, cnt in risk_q}
    risk_high = risk_map.get("high", 0)
    risk_med = risk_map.get("med", 0)
    risk_low = risk_map.get("low", 0)

    return CourseOverviewOut(
        course_id=course_id,
        course_title=course.title,
        semester=course.semester,
        student_count=student_count,
        average_score=round(avg_score, 2) if avg_score else None,
        attendance_rate=round(attend_rate, 3) if attend_rate else None,
        submission_rate=round(submission_rate, 3) if submission_rate else None,
        risk_count=risk_high + risk_med + risk_low,
        risk_high=risk_high,
        risk_med=risk_med,
        risk_low=risk_low,
    )


# ─── 2. 学情趋势（近 N 周）───
@analytics_router.get("/courses/{course_id}/trend", response_model=CourseTrendOut,
                      summary="学情趋势（近 N 周）")
def course_trend(
    course_id: uuid.UUID,
    weeks: int = Query(8, ge=1, le=26),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, course_id)
    _check_course_teacher(db, course, user)

    since = _now() - timedelta(weeks=weeks)
    # 按周聚合均分（作业维度）
    rows = (
        db.query(
            func.date(Grade.graded_at).label("d"),
            func.avg(Grade.total_score).label("avg_s"),
            func.count(distinct(Submission.student_id)).label("submitters"),
        )
        .join(Submission, Submission.id == Grade.submission_id)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .filter(
            Assignment.course_id == course_id,
            Grade.graded_at >= since,
        )
        .group_by(func.date(Grade.graded_at))
        .order_by(func.date(Grade.graded_at))
        .all()
    )
    student_count = db.query(func.count(Enrollment.user_id)).filter(
        Enrollment.course_id == course_id, Enrollment.role == "student", Enrollment.status == "active"
    ).scalar() or 1

    # 按 ISO 周聚合
    week_map: dict[str, list] = {}
    for r in rows:
        if not r.d:
            continue
        wk = _iso_week(r.d if isinstance(r.d, datetime) else datetime.combine(r.d, datetime.min.time()))
        week_map.setdefault(wk, []).append(r)

    # 生成近 N 周序列
    out_weeks: list[TrendPoint] = []
    now = _now()
    for i in range(weeks - 1, -1, -1):
        wk_dt = now - timedelta(weeks=i)
        wk = _iso_week(wk_dt)
        entries = week_map.get(wk, [])
        if entries:
            avg = sum(float(e.avg_s or 0) for e in entries) / len(entries)
            total_sub = sum(int(e.submitters or 0) for e in entries)
            out_weeks.append(TrendPoint(
                week=wk,
                average_score=round(avg, 2),
                submission_rate=round(min(total_sub / max(student_count, 1), 1.0), 3),
            ))
        else:
            out_weeks.append(TrendPoint(week=wk))

    return CourseTrendOut(course_id=course_id, weeks=out_weeks)


# ─── 3. 成绩分布 ───
@analytics_router.get("/courses/{course_id}/distribution", response_model=CourseDistributionOut,
                      summary="成绩分布（按分数段）")
def course_distribution(
    course_id: uuid.UUID,
    assessment_type: str = Query("overall", pattern="^(overall|assignment|exam)$"),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, course_id)
    _check_course_teacher(db, course, user)

    # 聚合成绩列表
    scores: list[float] = []
    if assessment_type in ("overall", "assignment"):
        rows = db.query(Grade.total_score).join(
            Submission, Submission.id == Grade.submission_id
        ).join(
            Assignment, Assignment.id == Submission.assignment_id
        ).filter(Assignment.course_id == course_id, Grade.total_score.isnot(None)).all()
        scores.extend(float(r[0]) for r in rows)
    if assessment_type in ("overall", "exam"):
        rows = db.query(ExamAttempt.total_score).filter(
            ExamAttempt.status == "submitted",
            ExamAttempt.paper_id.in_(
                db.query(ExamPaper.id).filter(ExamPaper.course_id == course_id)
            ),
        ).all()
        scores.extend(float(r[0]) for r in rows)

    total = len(scores)
    buckets_def = [
        ("90-100", 90, 100),
        ("80-89",  80, 90),
        ("70-79",  70, 80),
        ("60-69",  60, 70),
        ("<60",     0, 60),
    ]
    buckets = []
    for label, lo, hi in buckets_def:
        cnt = sum(1 for s in scores if lo <= s < hi) if label != "90-100" else sum(1 for s in scores if lo <= s <= hi)
        buckets.append(DistributionBucket(
            range_label=label,
            count=cnt,
            percentage=round(cnt / total, 3) if total else 0.0,
        ))
    return CourseDistributionOut(
        course_id=course_id,
        assessment_type=assessment_type,
        total_students=total,
        buckets=buckets,
    )


# ─── 4. 关键洞察 ───
@analytics_router.get("/courses/{course_id}/insights", response_model=CourseInsightsOut,
                      summary="关键洞察（规则生成）")
def course_insights(
    course_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, course_id)
    _check_course_teacher(db, course, user)

    # 动态生成（V1 简化：不存库；后续可改为 LearningInsight 持久化）
    insights = _generate_insights(db, course_id)
    return CourseInsightsOut(
        course_id=course_id,
        insights=[InsightOut(
            id=uuid.uuid4(),
            week_start=_iso_week(_now()),
            content=txt,
            suggestion=sug,
            created_at=_now(),
        ) for txt, sug in insights],
    )


def _generate_insights(db: Session, course_id: uuid.UUID) -> list[tuple[str, str]]:
    """规则生成关键洞察"""
    out: list[tuple[str, str]] = []
    # 1. 风险学生数量
    risk_cnt = db.query(func.count(distinct(RiskAlert.student_id))).filter(
        RiskAlert.course_id == course_id,
        RiskAlert.resolved == False,  # noqa: E712
        RiskAlert.level == "high",
    ).scalar() or 0
    if risk_cnt > 0:
        out.append((f"本周有 <b>{risk_cnt}</b> 名高风险学生需关注", "安排一对一家谈"))

    # 2. 作业完成率
    student_count = db.query(func.count(Enrollment.user_id)).filter(
        Enrollment.course_id == course_id, Enrollment.role == "student", Enrollment.status == "active"
    ).scalar() or 1
    total_subs = db.query(func.count(distinct(Submission.student_id))).join(
        Assignment, Assignment.id == Submission.assignment_id
    ).filter(Assignment.course_id == course_id).scalar() or 0
    rate = total_subs / max(student_count, 1)
    if rate < 0.8:
        out.append((f"作业完成率仅 <b>{rate:.0%}</b>，低于预期", "考虑调整作业量/难度或提醒学生"))

    # 3. 考试均分偏低
    avg_exam = db.query(func.avg(ExamAttempt.total_score)).filter(
        ExamAttempt.status == "submitted",
        ExamAttempt.paper_id.in_(db.query(ExamPaper.id).filter(ExamPaper.course_id == course_id)),
    ).scalar()
    if avg_exam and float(avg_exam) < 70:
        out.append((f"近期考试均分 <b>{float(avg_exam):.1f}</b>，难度可能偏高", "安排补讲/答疑"))

    if not out:
        out.append(("本周学情整体平稳，无显著异常", "继续保持当前教学节奏"))
    return out


# ─── 5. 本周进步 ───
@analytics_router.get("/courses/{course_id}/progress", response_model=CourseProgressOut,
                      summary="本周进步学生 Top N")
def course_progress(
    course_id: uuid.UUID,
    top: int = Query(5, ge=1, le=20),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, course_id)
    _check_course_teacher(db, course, user)

    # 简化：以最近两次作业的成绩差异作为进步指标
    # 取每个学生的最近两次成绩
    rows = (
        db.query(
            Submission.student_id,
            User.name.label("student_name"),
            User.student_id.label("student_student_id"),
            Grade.total_score,
            Assignment.created_at,
        )
        .join(Grade, Grade.submission_id == Submission.id)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .join(User, User.id == Submission.student_id)
        .filter(Assignment.course_id == course_id, Grade.total_score.isnot(None))
        .order_by(Submission.student_id, Assignment.created_at.desc())
        .all()
    )
    # 聚合每个学生最新两次
    per_student: dict[str, list[float]] = {}
    names: dict[str, tuple[str, str | None]] = {}
    for r in rows:
        key = str(r.student_id)
        per_student.setdefault(key, []).append(float(r.total_score))
        if key not in names:
            names[key] = (r.student_name, r.student_student_id)
    improved: list[ProgressStudent] = []
    for sid, scores in per_student.items():
        if len(scores) < 2:
            continue
        latest, prev = scores[0], scores[1]
        delta = latest - prev
        if delta > 0:
            name, stid = names[sid]
            improved.append(ProgressStudent(
                student_id=uuid.UUID(sid),
                student_name=name,
                student_student_id=stid,
                delta=round(delta, 2),
                from_score=prev,
                to_score=latest,
            ))
    improved.sort(key=lambda x: x.delta, reverse=True)
    return CourseProgressOut(course_id=course_id, top_improved=improved[:top])


# ─── 6. 风险学生列表（实时计算）───
@analytics_router.get("/courses/{course_id}/risks", response_model=CourseRisksOut,
                      summary="风险学生列表")
def course_risks(
    course_id: uuid.UUID,
    level: str | None = Query(None, pattern="^(high|med|low)$"),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, course_id)
    _check_course_teacher(db, course, user)

    # 优先查库（已刷新的），否则实时计算
    q = db.query(RiskAlert).filter(RiskAlert.course_id == course_id, RiskAlert.resolved == False)  # noqa: E712
    if level:
        q = q.filter(RiskAlert.level == level)
    alerts = q.order_by(
        case((RiskAlert.level == "high", 1), (RiskAlert.level == "med", 2), else_=3),
        RiskAlert.created_at.desc(),
    ).all()

    if not alerts:
        # 实时计算一次并入库
        alerts = _refresh_risk_alerts(db, course_id, _default_rules())

    risks: list[RiskStudent] = []
    for a in alerts:
        if level and a.level != level:
            continue
        stu = db.get(User, a.student_id)
        reasons = a.reasons or []
        metrics = a.metrics or {}
        score_trend = metrics.get("latest_score")
        risks.append(RiskStudent(
            student_id=a.student_id,
            student_name=stu.name if stu else "未知",
            student_student_id=stu.student_id if stu else None,
            level=a.level,
            reasons=reasons,
            score_trend=score_trend,
        ))
    return CourseRisksOut(course_id=course_id, total=len(risks), risks=risks)


# ─── 7. 预警记录列表 ───
@analytics_router.get("/courses/{course_id}/alerts", response_model=list[RiskAlertOut],
                      summary="预警记录列表")
def course_alerts(
    course_id: uuid.UUID,
    resolved: bool | None = Query(None),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, course_id)
    _check_course_teacher(db, course, user)

    q = db.query(RiskAlert).filter(RiskAlert.course_id == course_id)
    if resolved is not None:
        q = q.filter(RiskAlert.resolved == resolved)
    alerts = q.order_by(RiskAlert.created_at.desc()).limit(100).all()
    out: list[RiskAlertOut] = []
    for a in alerts:
        stu = db.get(User, a.student_id)
        out.append(RiskAlertOut(
            id=a.id,
            student_id=a.student_id,
            student_name=stu.name if stu else None,
            student_student_id=stu.student_id if stu else None,
            course_id=a.course_id,
            level=a.level,
            reasons=a.reasons,
            resolved=a.resolved,
            resolved_at=a.resolved_at,
            created_at=a.created_at,
        ))
    return out


# ─── 8. 触发预警刷新 ───
@analytics_router.post("/courses/{course_id}/alerts/refresh",
                       response_model=list[RiskAlertOut],
                       summary="触发预警规则重算")
def refresh_alerts(
    course_id: uuid.UUID,
    rules: AlertRuleIn | None = None,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, course_id)
    _check_course_teacher(db, course, user)

    r = rules or _default_rules()
    alerts = _refresh_risk_alerts(db, course_id, r)
    out: list[RiskAlertOut] = []
    for a in alerts:
        stu = db.get(User, a.student_id)
        out.append(RiskAlertOut(
            id=a.id, student_id=a.student_id,
            student_name=stu.name if stu else None,
            student_student_id=stu.student_id if stu else None,
            course_id=a.course_id, level=a.level,
            reasons=a.reasons, resolved=a.resolved,
            resolved_at=a.resolved_at, created_at=a.created_at,
        ))
    return out


def _default_rules() -> AlertRuleIn:
    return AlertRuleIn()


def _refresh_risk_alerts(db: Session, course_id: uuid.UUID, rules: AlertRuleIn) -> list[RiskAlert]:
    """对选课学生重跑预警规则，把新的/升级的写入 risk_alerts（不删除历史，仅追加未解决）"""
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.course_id == course_id, Enrollment.role == "student", Enrollment.status == "active")
        .all()
    )
    new_alerts: list[RiskAlert] = []
    now = _now()
    for e in enrollments:
        level, reasons, metrics = _evaluate_student_risk(db, course_id, e.user_id, rules)
        if level == "none":
            continue
        # 检查是否有未解决的同类预警
        existing = db.query(RiskAlert).filter(
            RiskAlert.course_id == course_id,
            RiskAlert.student_id == e.user_id,
            RiskAlert.resolved == False,  # noqa: E712
        ).first()
        if existing:
            # 升级/更新
            existing.level = level
            existing.reasons = reasons
            existing.metrics = metrics
            existing.updated_at = now
        else:
            a = RiskAlert(
                student_id=e.user_id,
                course_id=course_id,
                level=level,
                reasons=reasons,
                metrics=metrics,
            )
            db.add(a)
            new_alerts.append(a)
    db.commit()
    # 返回所有未解决
    return (
        db.query(RiskAlert)
        .filter(RiskAlert.course_id == course_id, RiskAlert.resolved == False)  # noqa: E712
        .all()
    )


def _evaluate_student_risk(db: Session, course_id: uuid.UUID, student_id, rules: AlertRuleIn):
    """评估单个学生风险等级 · 返回 (level, reasons, metrics)"""
    reasons: list[str] = []
    metrics: dict = {}
    level_score = 0  # 累计：high=3 / med=2 / low=1
    # 1. 作业完成率
    total_assign = db.query(func.count(Assignment.id)).filter(Assignment.course_id == course_id).scalar() or 0
    done_assign = (
        db.query(func.count(distinct(Submission.assignment_id)))
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .filter(
            Assignment.course_id == course_id,
            Submission.student_id == student_id,
        )
        .scalar() or 0
    )
    rate = (done_assign / total_assign) if total_assign else 1.0
    metrics["submission_rate"] = round(rate, 3)
    if rate < rules.submission_low:
        reasons.append(f"作业完成率 {rate:.0%}（< {rules.submission_low:.0%}）")
        level_score = max(level_score, 3)
    elif rate < rules.submission_mid:
        reasons.append(f"作业完成率 {rate:.0%}（< {rules.submission_mid:.0%}）")
        level_score = max(level_score, 2)

    # 2. 成绩下降
    latest_grades = (
        db.query(Grade.total_score, Assignment.created_at)
        .join(Submission, Submission.id == Grade.submission_id)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .filter(
            Assignment.course_id == course_id,
            Submission.student_id == student_id,
            Grade.total_score.isnot(None),
        )
        .order_by(Assignment.created_at.desc())
        .limit(2)
        .all()
    )
    if len(latest_grades) >= 2:
        latest, prev = float(latest_grades[0][0]), float(latest_grades[1][0])
        metrics["latest_score"] = latest
        if prev > 0:
            drop = (prev - latest) / prev
            if drop >= rules.score_drop_high:
                reasons.append(f"成绩下降 {drop:.0%}（{prev}→{latest}）")
                level_score = max(level_score, 3)
            elif drop >= rules.score_drop_mid:
                reasons.append(f"成绩下降 {drop:.0%}（{prev}→{latest}）")
                level_score = max(level_score, 2)

    # 3. 最近登录
    user = db.get(User, student_id)
    if user and user.last_login_at:
        inactive_days = (_now() - user.last_login_at).days
        metrics["inactive_days"] = inactive_days
        if inactive_days >= rules.inactive_days_high:
            reasons.append(f"{inactive_days} 天未登录")
            level_score = max(level_score, 3)
        elif inactive_days >= rules.inactive_days_mid:
            reasons.append(f"{inactive_days} 天未登录")
            level_score = max(level_score, 2)

    if level_score == 0:
        return "none", [], metrics
    if level_score >= 3:
        return "high", reasons, metrics
    if level_score == 2:
        return "med", reasons, metrics
    return "low", reasons, metrics


# ─── 9. 预警处理 ───
@analytics_router.patch("/alerts/{alert_id}/resolve", response_model=RiskAlertOut,
                        summary="标记预警已处理")
def resolve_alert(
    alert_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅教师/管理员可处理预警")
    a = db.get(RiskAlert, alert_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预警不存在")
    a.resolved = True
    a.resolved_at = _now()
    a.resolved_by = user.id
    db.commit()
    db.refresh(a)
    stu = db.get(User, a.student_id)
    return RiskAlertOut(
        id=a.id, student_id=a.student_id,
        student_name=stu.name if stu else None,
        student_student_id=stu.student_id if stu else None,
        course_id=a.course_id, level=a.level,
        reasons=a.reasons, resolved=a.resolved,
        resolved_at=a.resolved_at, created_at=a.created_at,
    )


# ─── 10. 学生档案 ───
@analytics_router.get("/students/{student_id}/profile", response_model=StudentProfileOut,
                      summary="学生档案详情")
def student_profile(
    student_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 权限：本人 / 教师（所教学生）/ 管理员
    stu = db.get(User, student_id)
    if not stu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生不存在")
    if stu.role != "student":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非学生用户")
    if user.role == "admin" or str(user.id) == str(student_id):
        pass
    elif user.role == "teacher":
        # 校验是否为本教师所教学生
        is_my_student = db.query(Enrollment.id).join(
            Course, Course.id == Enrollment.course_id
        ).filter(
            Enrollment.user_id == student_id,
            Enrollment.role == "student",
            Course.teacher_id == user.id,
        ).first()
        if not is_my_student:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该学生档案")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看")

    # 选课
    enroll_rows = (
        db.query(Enrollment, Course)
        .join(Course, Course.id == Enrollment.course_id)
        .filter(Enrollment.user_id == student_id, Enrollment.role == "student")
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )
    enrolled_courses = []
    for e, c in enroll_rows:
        gr = db.query(GradeRecord).filter(
            GradeRecord.student_id == student_id,
            GradeRecord.course_id == c.id,
        ).first()
        enrolled_courses.append({
            "course_id": str(c.id),
            "title": c.title,
            "semester": c.semester,
            "final_score": float(gr.final_score) if gr and gr.final_score else None,
            "gpa_point": float(gr.gpa_point) if gr and gr.gpa_point else None,
        })

    # GPA
    gpa_rows = db.query(func.avg(GradeRecord.gpa_point)).filter(
        GradeRecord.student_id == student_id,
        GradeRecord.gpa_point.isnot(None),
    ).first()
    overall_gpa = float(gpa_rows[0]) if gpa_rows and gpa_rows[0] else None

    # 近期预警（未解决）
    active_alerts = (
        db.query(RiskAlert)
        .filter(RiskAlert.student_id == student_id, RiskAlert.resolved == False)  # noqa: E712
        .order_by(RiskAlert.created_at.desc())
        .limit(10)
        .all()
    )
    alert_out = []
    for a in active_alerts:
        alert_out.append(RiskAlertOut(
            id=a.id, student_id=a.student_id,
            student_name=stu.name, student_student_id=stu.student_id,
            course_id=a.course_id, level=a.level,
            reasons=a.reasons, resolved=a.resolved,
            resolved_at=a.resolved_at, created_at=a.created_at,
        ))

    # 近期辅导
    tutoring = (
        db.query(TutoringSession)
        .filter(TutoringSession.student_id == student_id)
        .order_by(TutoringSession.scheduled_at.desc())
        .limit(5)
        .all()
    )
    tutor_out = []
    for t in tutoring:
        c = db.get(CourseBrief, t.course_id) if t.course_id else None
        tutor = db.get(User, t.tutor_id)
        tutor_out.append({
            "id": str(t.id),
            "topic": t.topic,
            "mode": t.mode,
            "scheduled_at": t.scheduled_at.isoformat(),
            "duration_min": t.duration_min,
            "outcome": t.outcome,
            "tutor_name": tutor.name if tutor else None,
            "course_title": c.title if c else None,
        })

    return StudentProfileOut(
        student_id=stu.id,
        student_name=stu.name,
        student_student_id=stu.student_id,
        department=stu.department,
        grade=stu.grade,
        avatar_url=stu.avatar_url,
        email=stu.email,
        enrolled_courses=enrolled_courses,
        overall_gpa=round(overall_gpa, 2) if overall_gpa else None,
        active_alerts=alert_out,
        recent_tutoring=tutor_out,
    )


# ─── 11. 预警规则（管理员配置 · V1 占位，返回默认）───
@analytics_router.get("/alerts/rules", response_model=AlertRuleIn, summary="查看预警规则（默认）")
def get_alert_rules(user: AuthUser = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可配置规则")
    return _default_rules()


@analytics_router.post("/alerts/rules", response_model=AlertRuleIn, summary="配置预警规则（V1 仅回显）")
def set_alert_rules(
    rules: AlertRuleIn,
    user: AuthUser = Depends(get_current_user),
):
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可配置规则")
    # V1 不持久化，直接回显；后续可接 system_settings 表
    return rules


# ─── 12. 管理员事件统计（原 admin 端点，保持向下兼容）───
# 原 /events/stats /events/breakdown 已在上面定义，保留。