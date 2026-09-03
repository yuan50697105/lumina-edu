# ============================================
# Lumina 墨光 · D-10 运营监控路由
# Prometheus 指标 / 深度健康检查 / 业务指标
# ============================================
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, require_role
from app.models import (
    User, Course, Video, VideoWatchHistory,
    Assignment, Submission, ExamPaper, ExamAttempt,
    AICallLog, CheckInRecord, APILog,
)
from app.schemas import (
    ServiceHealth, DeepHealthCheckOut, PrometheusMetricsOut, BusinessMetricsOut,
)

router = APIRouter(prefix="/ops", tags=["运营监控（D-10）"])

# 启动时间（用于计算 uptime）
_start_time = time.time()
_version = "1.0.0"


# ═══════════════════════════════════════════════════════════════════
# 1. 深度健康检查
# ═══════════════════════════════════════════════════════════════════

@router.get("/health/deep", response_model=DeepHealthCheckOut, summary="深度健康检查")
def deep_health_check(
    db: Session = Depends(get_db),
):
    """深度健康检查：检查 DB / Redis（预留）等依赖服务状态"""
    services = []

    # 1. 数据库检查
    try:
        start = time.time()
        db.execute(func.now())
        latency = (time.time() - start) * 1000
        services.append(ServiceHealth(
            name="mysql",
            status="healthy",
            latency_ms=round(latency, 2),
            details={"type": "MySQL 9.7"},
        ))
        db_status = "healthy"
    except Exception as e:
        services.append(ServiceHealth(
            name="mysql",
            status="down",
            details={"error": str(e)},
        ))
        db_status = "down"

    # 2. Redis 检查（预留，当前未部署）
    services.append(ServiceHealth(
        name="redis",
        status="degraded",
        details={"note": "Redis 未部署，使用内存缓存"},
    ))

    # 3. 应用自身
    services.append(ServiceHealth(
        name="lumina-app",
        status="healthy",
        latency_ms=0,
        details={"version": _version},
    ))

    # 总体状态
    if db_status == "down":
        overall = "down"
    elif any(s.status == "degraded" for s in services):
        overall = "degraded"
    else:
        overall = "healthy"

    uptime = int(time.time() - _start_time)

    return DeepHealthCheckOut(
        status=overall,
        timestamp=datetime.now(timezone.utc),
        services=services,
        version=_version,
        uptime_seconds=uptime,
    )


# ═══════════════════════════════════════════════════════════════════
# 2. Prometheus 指标导出
# ═══════════════════════════════════════════════════════════════════

@router.get("/metrics", summary="Prometheus 指标导出")
def prometheus_metrics(
    db: Session = Depends(get_db),
):
    """导出 Prometheus 格式指标（文本格式）"""
    lines = []

    # HELP / TYPE 头
    lines.append("# HELP lumina_users_total Total number of users")
    lines.append("# TYPE lumina_users_total gauge")
    total_users = db.query(func.count(User.id)).scalar() or 0
    lines.append(f"lumina_users_total {total_users}")

    lines.append("# HELP lumina_courses_total Total number of courses")
    lines.append("# TYPE lumina_courses_total gauge")
    total_courses = db.query(func.count(Course.id)).scalar() or 0
    lines.append(f"lumina_courses_total {total_courses}")

    lines.append("# HELP lumina_videos_total Total number of videos")
    lines.append("# TYPE lumina_videos_total gauge")
    total_videos = db.query(func.count(Video.id)).scalar() or 0
    lines.append(f"lumina_videos_total {total_videos}")

    # API 请求计数（按状态码分组）
    lines.append("# HELP lumina_api_requests_total Total API requests by status")
    lines.append("# TYPE lumina_api_requests_total counter")
    status_counts = db.query(APILog.status_code, func.count(APILog.id)).group_by(APILog.status_code).all()
    for status, count in status_counts:
        lines.append(f'lumina_api_requests_total{{status="{status}"}} {count}')

    # 今日活跃用户
    lines.append("# HELP lumina_active_users_today Active users today")
    lines.append("# TYPE lumina_active_users_today gauge")
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    active_users = db.query(func.count(distinct(APILog.user_id))).filter(
        APILog.created_at >= today,
        APILog.user_id.isnot(None),
    ).scalar() or 0
    lines.append(f"lumina_active_users_today {active_users}")

    # AI 调用计数
    lines.append("# HELP lumina_ai_calls_total Total AI calls")
    lines.append("# TYPE lumina_ai_calls_total counter")
    ai_calls = db.query(func.count(AICallLog.id)).scalar() or 0
    lines.append(f"lumina_ai_calls_total {ai_calls}")

    # Uptime
    lines.append("# HELP lumina_uptime_seconds Application uptime in seconds")
    lines.append("# TYPE lumina_uptime_seconds gauge")
    uptime = int(time.time() - _start_time)
    lines.append(f"lumina_uptime_seconds {uptime}")

    content = "\n".join(lines)
    return PlainTextResponse(content, media_type="text/plain; version=0.0.4")


# ═══════════════════════════════════════════════════════════════════
# 3. 业务指标 API
# ═══════════════════════════════════════════════════════════════════

@router.get("/metrics/business", response_model=BusinessMetricsOut, summary="业务指标汇总（管理员）")
def business_metrics(
    user: AuthUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """获取业务指标汇总（仅管理员）"""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)

    # 用户
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users_today = db.query(func.count(distinct(APILog.user_id))).filter(
        APILog.created_at >= today,
        APILog.user_id.isnot(None),
    ).scalar() or 0

    # 课程
    total_courses = db.query(func.count(Course.id)).scalar() or 0
    from app.models import Enrollment
    active_courses = db.query(func.count(distinct(Enrollment.course_id))).filter(
        Enrollment.enrolled_at >= month_ago
    ).scalar() or 0

    # 视频
    total_videos = db.query(func.count(Video.id)).scalar() or 0
    videos_watched_today = db.query(func.count(distinct(VideoWatchHistory.video_id))).filter(
        VideoWatchHistory.last_watched_at >= today
    ).scalar() or 0

    # 作业
    total_assignments = db.query(func.count(Assignment.id)).scalar() or 0
    submissions_today = db.query(func.count(Submission.id)).filter(
        Submission.submitted_at >= today
    ).scalar() or 0

    # 考试
    total_exams = db.query(func.count(ExamPaper.id)).scalar() or 0
    exam_attempts_today = db.query(func.count(ExamAttempt.id)).filter(
        ExamAttempt.started_at >= today
    ).scalar() or 0

    # AI
    ai_calls_today = db.query(func.count(AICallLog.id)).filter(
        AICallLog.created_at >= today
    ).scalar() or 0

    # 打卡
    checkins_today = db.query(func.count(CheckInRecord.id)).filter(
        CheckInRecord.checkin_date >= today
    ).scalar() or 0

    return BusinessMetricsOut(
        total_users=total_users,
        active_users_today=active_users_today,
        total_courses=total_courses,
        active_courses=active_courses,
        total_videos=total_videos,
        videos_watched_today=videos_watched_today,
        total_assignments=total_assignments,
        submissions_today=submissions_today,
        total_exams=total_exams,
        exam_attempts_today=exam_attempts_today,
        ai_calls_today=ai_calls_today,
        checkins_today=checkins_today,
        timestamp=datetime.now(timezone.utc),
    )
