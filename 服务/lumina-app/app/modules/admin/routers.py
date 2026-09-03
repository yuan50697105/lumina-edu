# ============================================
# Lumina 墨光 · 管理端路由（V1.1 · D-07/D-08）
# 监控大盘 / 课程审批 / 内容举报
# 权限：admin（部分端点 teacher 可访问提交）
# ============================================
import csv
import io
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, text as sa_text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, get_current_user, require_role
from app.models import (
    AuditLog,
    ContentReport,
    Course,
    CourseApproval,
    CourseBrief,
    Enrollment,
    EventTracking,
    User,
)
from app.schemas import (
    CourseApprovalOut,
    CourseApprovalReview,
    CourseApprovalStatusOut,
    CourseApprovalSubmit,
    DashboardGrowth,
    DashboardHealth,
    DashboardOverview,
    DashboardRecentActivity,
    GrowthPoint,
    HealthMetric,
    RecentActivityItem,
    ReportCreate,
    ReportOut,
    ReportResolve,
    SuccessResponse,
)

router = APIRouter(prefix="/admin", tags=["管理端（D-07/D-08）"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_admin(user: AuthUser) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可访问")
    return user


# ═══════════════════════════════════════════════════════════════════
# 1. 监控大盘
# ═══════════════════════════════════════════════════════════════════
@router.get("/dashboard/overview", response_model=DashboardOverview,
            summary="监控大盘总览（管理员）")
def dashboard_overview(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    now = _now()
    day_ago = now - timedelta(days=1)
    month_ago = now - timedelta(days=30)

    total_users = db.query(func.count(User.id)).scalar() or 0
    total_students = db.query(func.count(User.id)).filter(User.role == "student").scalar() or 0
    total_teachers = db.query(func.count(User.id)).filter(User.role == "teacher").scalar() or 0
    total_courses = db.query(func.count(Course.id)).scalar() or 0
    active_courses = db.query(func.count(func.distinct(Enrollment.course_id))).filter(
        Enrollment.enrolled_at >= month_ago
    ).scalar() or 0
    # 日活跃：近 1 天有登录或有事件
    dau = db.query(func.count(func.distinct(EventTracking.user_id))).filter(
        EventTracking.created_at >= day_ago,
        EventTracking.user_id.isnot(None),
    ).scalar() or 0
    mau = db.query(func.count(func.distinct(EventTracking.user_id))).filter(
        EventTracking.created_at >= month_ago,
        EventTracking.user_id.isnot(None),
    ).scalar() or 0
    pending_approvals = db.query(func.count(CourseApproval.id)).filter(
        CourseApproval.status == "pending"
    ).scalar() or 0
    pending_reports = db.query(func.count(ContentReport.id)).filter(
        ContentReport.status == "pending"
    ).scalar() or 0
    today_regs = db.query(func.count(User.id)).filter(
        User.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0)
    ).scalar() or 0

    return DashboardOverview(
        total_users=total_users,
        total_students=total_students,
        total_teachers=total_teachers,
        total_courses=total_courses,
        active_courses=active_courses,
        dau=dau,
        mau=mau,
        pending_approvals=pending_approvals,
        pending_reports=pending_reports,
        today_registrations=today_regs,
    )


@router.get("/dashboard/growth", response_model=DashboardGrowth,
            summary="用户/课程增长（近 12 月 · 管理员）")
def dashboard_growth(
    months: int = Query(12, ge=1, le=36),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    now = _now()
    out: list[GrowthPoint] = []
    for i in range(months - 1, -1, -1):
        # 当月第一天
        y, m = now.year, now.month - i
        while m <= 0:
            m += 12
            y -= 1
        start = datetime(y, m, 1, tzinfo=timezone.utc)
        # 下个月第一天
        nm = m + 1
        ny = y
        if nm > 12:
            nm = 1
            ny += 1
        end = datetime(ny, nm, 1, tzinfo=timezone.utc)
        new_users = db.query(func.count(User.id)).filter(
            User.created_at >= start, User.created_at < end
        ).scalar() or 0
        new_courses = db.query(func.count(Course.id)).filter(
            Course.created_at >= start, Course.created_at < end
        ).scalar() or 0
        active = db.query(func.count(func.distinct(EventTracking.user_id))).filter(
            EventTracking.created_at >= start,
            EventTracking.created_at < end,
            EventTracking.user_id.isnot(None),
        ).scalar() or 0
        out.append(GrowthPoint(
            month=f"{y}-{m:02d}",
            new_users=new_users,
            new_courses=new_courses,
            active_users=active,
        ))
    return DashboardGrowth(months=out)


@router.get("/dashboard/health", response_model=DashboardHealth,
            summary="系统健康度 / SLA（管理员）")
def dashboard_health(
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    now = _now()
    day_ago = now - timedelta(days=1)
    metrics: list[HealthMetric] = []

    # API 健康（基于 api_logs 近 24h）
    try:
        from app.models import APILog
        total_api = db.query(func.count(APILog.id)).filter(APILog.created_at >= day_ago).scalar() or 0
        err_5xx = db.query(func.count(APILog.id)).filter(
            APILog.created_at >= day_ago,
            APILog.status_code >= 500,
        ).scalar() or 0
        avg_ms = db.query(func.avg(APILog.duration_ms)).filter(
            APILog.created_at >= day_ago
        ).scalar()
        error_rate = err_5xx / total_api if total_api else 0
        api_status = "healthy" if error_rate < 0.01 else ("degraded" if error_rate < 0.05 else "down")
        metrics.append(HealthMetric(
            name="api",
            status=api_status,
            uptime_pct=round((1 - error_rate) * 100, 3),
            avg_latency_ms=round(float(avg_ms or 0), 2),
            error_rate=round(error_rate, 4),
        ))
    except Exception:
        metrics.append(HealthMetric(name="api", status="unknown"))

    # DB 健康
    try:
        db.execute(sa_text("SELECT 1"))
        metrics.append(HealthMetric(name="db", status="healthy", uptime_pct=100.0))
    except Exception:
        metrics.append(HealthMetric(name="db", status="down"))

    # AI 健康（基于 ai_call_logs 近 24h）
    try:
        from app.models import AICallLog
        total_ai = db.query(func.count(AICallLog.id)).filter(AICallLog.created_at >= day_ago).scalar() or 0
        ok_ai = db.query(func.count(AICallLog.id)).filter(
            AICallLog.created_at >= day_ago, AICallLog.ok == True  # noqa: E712
        ).scalar() or 0
        ai_rate = ok_ai / total_ai if total_ai else 1.0
        ai_status = "healthy" if ai_rate > 0.95 else ("degraded" if ai_rate > 0.8 else "down")
        metrics.append(HealthMetric(
            name="ai",
            status=ai_status if total_ai > 0 else "healthy",
            uptime_pct=round(ai_rate * 100, 3) if total_ai else 100.0,
        ))
    except Exception:
        metrics.append(HealthMetric(name="ai", status="unknown"))

    # 整体
    has_down = any(m.status == "down" for m in metrics)
    has_degraded = any(m.status == "degraded" for m in metrics)
    overall = "down" if has_down else ("degraded" if has_degraded else "healthy")
    return DashboardHealth(metrics=metrics, sla_target=99.9, overall_status=overall)


@router.get("/dashboard/recent-activity", response_model=DashboardRecentActivity,
            summary="最近活动（审计+举报+审批 · 管理员）")
def dashboard_recent_activity(
    limit: int = Query(20, ge=1, le=100),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)

    items: list[RecentActivityItem] = []
    # 审计日志
    audits = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    for a in audits:
        actor = db.get(User, a.actor_id) if a.actor_id else None
        items.append(RecentActivityItem(
            id=a.id if isinstance(a.id, uuid.UUID) else uuid.UUID(int=a.id),
            type="audit",
            action=a.action,
            actor_name=actor.name if actor else "系统",
            target=f"{a.target_type}:{a.target_id}" if a.target_type else None,
            created_at=a.created_at,
        ))
    # 举报
    reports = db.query(ContentReport).order_by(ContentReport.created_at.desc()).limit(limit).all()
    for r in reports:
        reporter = db.get(User, r.reporter_id)
        items.append(RecentActivityItem(
            id=r.id,
            type="report",
            action=f"report.{r.reason}",
            actor_name=reporter.name if reporter else "匿名",
            target=f"{r.target_type}:{r.target_id}",
            created_at=r.created_at,
        ))
    # 审批
    approvals = db.query(CourseApproval).order_by(CourseApproval.submitted_at.desc()).limit(limit).all()
    for ap in approvals:
        submitter = db.get(User, ap.submitted_by)
        course = db.get(CourseBrief, ap.course_id)
        items.append(RecentActivityItem(
            id=ap.id,
            type="approval",
            action=f"approval.{ap.status}",
            actor_name=submitter.name if submitter else "未知",
            target=course.title if course else str(ap.course_id),
            created_at=ap.submitted_at,
        ))
    # 合并按时间倒序，截断
    items.sort(key=lambda x: x.created_at, reverse=True)
    return DashboardRecentActivity(items=items[:limit])


# ═══════════════════════════════════════════════════════════════════
# 2. 课程审批
# ═══════════════════════════════════════════════════════════════════
@router.get("/approvals/courses", response_model=list[CourseApprovalOut],
            summary="课程审批队列（管理员）")
def list_course_approvals(
    status_filter: str | None = Query(None, alias="status", pattern="^(pending|approved|rejected)$"),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    q = db.query(CourseApproval)
    if status_filter:
        q = q.filter(CourseApproval.status == status_filter)
    approvals = q.order_by(CourseApproval.submitted_at.desc()).limit(100).all()
    out = []
    for ap in approvals:
        submitter = db.get(User, ap.submitted_by)
        reviewer = db.get(User, ap.reviewer_id) if ap.reviewer_id else None
        course = db.get(CourseBrief, ap.course_id)
        out.append(CourseApprovalOut(
            id=ap.id, course_id=ap.course_id,
            course_title=course.title if course else None,
            course_code=course.code if course else None,
            submitted_by=ap.submitted_by,
            submitter_name=submitter.name if submitter else None,
            reviewer_id=ap.reviewer_id,
            reviewer_name=reviewer.name if reviewer else None,
            status=ap.status,
            comment=ap.comment,
            submitted_at=ap.submitted_at,
            reviewed_at=ap.reviewed_at,
        ))
    return out


@router.get("/approvals/courses/{approval_id}", response_model=CourseApprovalOut,
            summary="审批详情（管理员）")
def get_course_approval(
    approval_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    ap = db.get(CourseApproval, approval_id)
    if not ap:
        raise HTTPException(status_code=404, detail="审批记录不存在")
    submitter = db.get(User, ap.submitted_by)
    reviewer = db.get(User, ap.reviewer_id) if ap.reviewer_id else None
    course = db.get(CourseBrief, ap.course_id)
    return CourseApprovalOut(
        id=ap.id, course_id=ap.course_id,
        course_title=course.title if course else None,
        course_code=course.code if course else None,
        submitted_by=ap.submitted_by,
        submitter_name=submitter.name if submitter else None,
        reviewer_id=ap.reviewer_id,
        reviewer_name=reviewer.name if reviewer else None,
        status=ap.status,
        comment=ap.comment,
        submitted_at=ap.submitted_at,
        reviewed_at=ap.reviewed_at,
    )


@router.post("/approvals/courses/{approval_id}/approve", response_model=CourseApprovalOut,
             summary="通过课程审批（管理员）")
def approve_course(
    approval_id: uuid.UUID,
    payload: CourseApprovalReview,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    admin = _require_admin(user)
    ap = db.get(CourseApproval, approval_id)
    if not ap:
        raise HTTPException(status_code=404, detail="审批记录不存在")
    if ap.status != "pending":
        raise HTTPException(status_code=400, detail=f"审批已处理（当前状态：{ap.status}）")
    ap.status = "approved"
    ap.comment = payload.comment
    ap.reviewer_id = admin.id
    ap.reviewed_at = _now()
    # 课程状态流转 draft → published
    course = db.get(Course, ap.course_id)
    if course and course.status == "draft":
        course.status = "published"
    # 审计
    db.add(AuditLog(
        actor_id=admin.id,
        action="course.approve",
        target_type="course",
        target_id=ap.course_id,
        details={"approval_id": str(ap.id), "comment": payload.comment},
    ))
    db.commit()
    db.refresh(ap)
    submitter = db.get(User, ap.submitted_by)
    course_brief = db.get(CourseBrief, ap.course_id)
    return CourseApprovalOut(
        id=ap.id, course_id=ap.course_id,
        course_title=course_brief.title if course_brief else None,
        course_code=course_brief.code if course_brief else None,
        submitted_by=ap.submitted_by,
        submitter_name=submitter.name if submitter else None,
        reviewer_id=ap.reviewer_id,
        reviewer_name=admin.name,
        status=ap.status,
        comment=ap.comment,
        submitted_at=ap.submitted_at,
        reviewed_at=ap.reviewed_at,
    )


@router.post("/approvals/courses/{approval_id}/reject", response_model=CourseApprovalOut,
             summary="驳回课程审批（管理员）")
def reject_course(
    approval_id: uuid.UUID,
    payload: CourseApprovalReview,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    admin = _require_admin(user)
    ap = db.get(CourseApproval, approval_id)
    if not ap:
        raise HTTPException(status_code=404, detail="审批记录不存在")
    if ap.status != "pending":
        raise HTTPException(status_code=400, detail=f"审批已处理（当前状态：{ap.status}）")
    ap.status = "rejected"
    ap.comment = payload.comment
    ap.reviewer_id = admin.id
    ap.reviewed_at = _now()
    db.add(AuditLog(
        actor_id=admin.id,
        action="course.reject",
        target_type="course",
        target_id=ap.course_id,
        details={"approval_id": str(ap.id), "comment": payload.comment},
    ))
    db.commit()
    db.refresh(ap)
    submitter = db.get(User, ap.submitted_by)
    course_brief = db.get(CourseBrief, ap.course_id)
    return CourseApprovalOut(
        id=ap.id, course_id=ap.course_id,
        course_title=course_brief.title if course_brief else None,
        course_code=course_brief.code if course_brief else None,
        submitted_by=ap.submitted_by,
        submitter_name=submitter.name if submitter else None,
        reviewer_id=ap.reviewer_id,
        reviewer_name=admin.name,
        status=ap.status,
        comment=ap.comment,
        submitted_at=ap.submitted_at,
        reviewed_at=ap.reviewed_at,
    )


# ── 教师端：提交审批 / 查询状态 ──
@router.post("/courses/{course_id}/submit-for-approval", response_model=CourseApprovalOut,
             status_code=201, summary="教师提交课程审批")
def submit_course_for_approval(
    course_id: uuid.UUID,
    payload: CourseApprovalSubmit,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="仅教师可提交审批")
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    if user.role == "teacher" and str(course.teacher_id) != str(user.id):
        raise HTTPException(status_code=403, detail="无权操作他人课程")
    # 检查是否已提交
    existing = db.query(CourseApproval).filter(CourseApproval.course_id == course_id).first()
    if existing:
        if existing.status == "pending":
            raise HTTPException(status_code=400, detail="已有待审批记录")
        # 已审核过，可重新提交
        existing.status = "pending"
        existing.comment = None
        existing.reviewer_id = None
        existing.reviewed_at = None
        existing.submitted_at = _now()
        ap = existing
    else:
        ap = CourseApproval(
            course_id=course_id,
            submitted_by=user.id,
            status="pending",
        )
        db.add(ap)
    db.add(AuditLog(
        actor_id=user.id,
        action="course.submit_for_approval",
        target_type="course",
        target_id=course_id,
        details={"note": payload.note},
    ))
    db.commit()
    db.refresh(ap)
    return CourseApprovalOut(
        id=ap.id, course_id=ap.course_id,
        course_title=course.title, course_code=course.code,
        submitted_by=ap.submitted_by, submitter_name=user.name,
        reviewer_id=ap.reviewer_id, reviewer_name=None,
        status=ap.status, comment=ap.comment,
        submitted_at=ap.submitted_at, reviewed_at=ap.reviewed_at,
    )


@router.get("/courses/{course_id}/approval-status", response_model=CourseApprovalStatusOut,
            summary="查询课程审批状态")
def get_course_approval_status(
    course_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = db.get(CourseBrief, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    # 教师看自己课程 / admin 看所有
    if user.role == "teacher" and str(course.teacher_id) != str(user.id):
        raise HTTPException(status_code=403, detail="无权查看")
    ap = db.query(CourseApproval).filter(CourseApproval.course_id == course_id).first()
    if not ap:
        return CourseApprovalStatusOut(course_id=course_id, has_approval=False)
    return CourseApprovalStatusOut(
        course_id=course_id,
        has_approval=True,
        status=ap.status,
        approval_id=ap.id,
        submitted_at=ap.submitted_at,
        reviewed_at=ap.reviewed_at,
        comment=ap.comment,
    )


# ═══════════════════════════════════════════════════════════════════
# 3. 内容举报
# ═══════════════════════════════════════════════════════════════════
@router.post("/reports", response_model=ReportOut, status_code=201,
             summary="用户举报内容")
def create_report(
    payload: ReportCreate,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 举报目标存在性校验（V1 简化：仅校验 target_id 合法 UUID 即可）
    r = ContentReport(
        reporter_id=user.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
        description=payload.description,
        status="pending",
    )
    db.add(r)
    db.add(AuditLog(
        actor_id=user.id,
        action="report.create",
        target_type=payload.target_type,
        target_id=payload.target_id,
        details={"reason": payload.reason},
    ))
    db.commit()
    db.refresh(r)
    return ReportOut(
        id=r.id, reporter_id=r.reporter_id, reporter_name=user.name,
        target_type=r.target_type, target_id=r.target_id,
        reason=r.reason, description=r.description,
        status=r.status, created_at=r.created_at,
    )


@router.get("/reports", response_model=list[ReportOut],
            summary="举报列表（管理员）")
def list_reports(
    status_filter: str | None = Query(None, alias="status", pattern="^(pending|reviewing|resolved|dismissed)$"),
    target_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(user)
    q = db.query(ContentReport)
    if status_filter:
        q = q.filter(ContentReport.status == status_filter)
    if target_type:
        q = q.filter(ContentReport.target_type == target_type)
    reports = q.order_by(ContentReport.created_at.desc()).limit(limit).all()
    out = []
    for r in reports:
        reporter = db.get(User, r.reporter_id)
        reviewer = db.get(User, r.reviewer_id) if r.reviewer_id else None
        out.append(ReportOut(
            id=r.id, reporter_id=r.reporter_id,
            reporter_name=reporter.name if reporter else None,
            target_type=r.target_type, target_id=r.target_id,
            reason=r.reason, description=r.description,
            status=r.status, reviewer_id=r.reviewer_id,
            reviewer_name=reviewer.name if reviewer else None,
            resolution=r.resolution,
            created_at=r.created_at, reviewed_at=r.reviewed_at,
        ))
    return out


@router.post("/reports/{report_id}/resolve", response_model=ReportOut,
             summary="处理举报（管理员）")
def resolve_report(
    report_id: uuid.UUID,
    payload: ReportResolve,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    admin = _require_admin(user)
    r = db.get(ContentReport, report_id)
    if not r:
        raise HTTPException(status_code=404, detail="举报不存在")
    if r.status in ("resolved", "dismissed"):
        raise HTTPException(status_code=400, detail=f"举报已处理（当前状态：{r.status}）")
    r.status = payload.status
    r.resolution = payload.resolution
    r.reviewer_id = admin.id
    r.reviewed_at = _now()
    db.add(AuditLog(
        actor_id=admin.id,
        action=f"report.{payload.status}",
        target_type=r.target_type,
        target_id=r.target_id,
        details={"report_id": str(r.id), "resolution": payload.resolution},
    ))
    db.commit()
    db.refresh(r)
    reporter = db.get(User, r.reporter_id)
    return ReportOut(
        id=r.id, reporter_id=r.reporter_id,
        reporter_name=reporter.name if reporter else None,
        target_type=r.target_type, target_id=r.target_id,
        reason=r.reason, description=r.description,
        status=r.status, reviewer_id=r.reviewer_id,
        reviewer_name=admin.name, resolution=r.resolution,
        created_at=r.created_at, reviewed_at=r.reviewed_at,
    )
