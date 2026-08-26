# ============================================
# Lumina 墨光 · 成绩路由
# /grades/me 成绩单 · /grades/statistics 统计 · /courses/{id}/grades 课程成绩
# ============================================
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.instrumentation import (
    EVENT_GRADE_RECORDED,
    EVENT_GRADE_STATS,
    EVENT_GRADE_UPDATED,
    EVENT_GRADE_VIEW,
    Instrumentation,
)
from app.models import CourseBrief, GradeRecord, UserBrief
from app.schemas import (
    GradeRecordCreate,
    GradeRecordOut,
    GradeStats,
    MyCourseGrade,
    MyGrades,
    SuccessResponse,
)

router = APIRouter(prefix="/grades", tags=["成绩"])
course_router = APIRouter(prefix="/courses", tags=["成绩·课程"])

# ─── 成绩工具 ───
def gpa_from_score(score) -> Decimal:
    """百分制 → 4.0 制绩点（中国高校通用映射）"""
    s = float(score)
    if s >= 90: return Decimal("4.0")
    if s >= 85: return Decimal("3.7")
    if s >= 82: return Decimal("3.3")
    if s >= 78: return Decimal("3.0")
    if s >= 75: return Decimal("2.7")
    if s >= 72: return Decimal("2.3")
    if s >= 68: return Decimal("2.0")
    if s >= 64: return Decimal("1.5")
    if s >= 60: return Decimal("1.0")
    return Decimal("0.0")


def letter_from_score(score) -> str:
    """百分制 → A-F 等级"""
    s = float(score)
    if s >= 90: return "A"
    if s >= 80: return "B"
    if s >= 70: return "C"
    if s >= 60: return "D"
    return "F"


def _get_course(db: Session, course_id) -> CourseBrief:
    c = db.get(CourseBrief, course_id)
    if not c:
        raise HTTPException(status_code=404, detail="课程不存在")
    return c


def _check_teacher(db: Session, course: CourseBrief, user: UserBrief) -> None:
    """课程授课权限：教师本课或管理员"""
    if user.role == "admin":
        return
    if course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作该课程成绩")


def _record_out(db: Session, r: GradeRecord) -> GradeRecordOut:
    u = db.get(UserBrief, r.student_id)
    out = GradeRecordOut.model_validate(r)
    out.student_name = u.name if u else None
    out.student_no = u.student_id if u else None
    out.grade_letter = letter_from_score(r.final_score) if r.final_score is not None else None
    return out


# ─── 我的成绩单 ───
@router.get("/me", response_model=MyGrades, summary="我的成绩单")
def my_grades(
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """学生成绩单：课程明细 + 加权 GPA + 总学分"""
    records = (
        db.query(GradeRecord)
        .filter(GradeRecord.student_id == user.id)
        .order_by(GradeRecord.semester.desc())
        .all()
    )

    result = MyGrades()
    weighted = Decimal("0.0")
    credit_sum = Decimal("0.0")
    for r in records:
        course = db.get(CourseBrief, r.course_id)
        credit = course.credits if course else Decimal("0.0")
        gpa = r.gpa_point if r.gpa_point is not None else (gpa_from_score(r.final_score) if r.final_score is not None else None)
        result.courses.append(MyCourseGrade(
            course_id=r.course_id,
            title=course.title if course else "(已删除课程)",
            credit=credit,
            score=r.final_score,
            grade=letter_from_score(r.final_score) if r.final_score is not None else None,
            semester=r.semester,
        ))
        if gpa is not None and credit:
            weighted += Decimal(gpa) * credit
            credit_sum += credit

    result.course_count = len(result.courses)
    if credit_sum > 0:
        result.gpa = (weighted / credit_sum).quantize(Decimal("0.01"))
    result.total_credits = credit_sum

    Instrumentation(db, request, str(user.id)).track(EVENT_GRADE_VIEW, scope="me")
    return result


@router.get("/statistics", response_model=GradeStats, summary="成绩统计")
def grade_statistics(
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
    course_id: uuid.UUID | None = None,
    semester: str | None = None,
):
    """成绩统计：平均/最高/最低/及格率/A-F 分布"""
    query = db.query(GradeRecord)
    if course_id:
        query = query.filter(GradeRecord.course_id == course_id)
    if semester:
        query = query.filter(GradeRecord.semester == semester)

    records = query.all()
    scores = [float(r.final_score) for r in records if r.final_score is not None]

    stats = GradeStats()
    stats.count = len(scores)
    if scores:
        stats.average = Decimal(sum(scores) / len(scores)).quantize(Decimal("0.1"))
        stats.highest = Decimal(max(scores))
        stats.lowest = Decimal(min(scores))
        passed = sum(1 for s in scores if s >= 60)
        stats.pass_rate = Decimal(passed / len(scores)).quantize(Decimal("0.01"))
        stats.distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for r in records:
            if r.final_score is not None:
                lv = letter_from_score(r.final_score)
                stats.distribution[lv] = stats.distribution.get(lv, 0) + 1

    Instrumentation(db, request, str(user.id)).track(
        EVENT_GRADE_STATS, course_id=str(course_id) if course_id else None,
        properties={"semester": semester, "count": stats.count},
    )
    return stats


# ─── 课程成绩（教师）───
@course_router.get("/{course_id}/grades", response_model=list[GradeRecordOut], summary="课程成绩列表（教师）")
def list_course_grades(
    course_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, course_id)
    _check_teacher(db, course, user)

    records = (
        db.query(GradeRecord)
        .filter(GradeRecord.course_id == course_id)
        .order_by(GradeRecord.student_id)
        .all()
    )
    Instrumentation(db, request, str(user.id)).track(
        EVENT_GRADE_VIEW, course_id=str(course_id), scope="course"
    )
    return [_record_out(db, r) for r in records]


@course_router.post("/{course_id}/grades", response_model=GradeRecordOut, status_code=201, summary="录入/更新成绩（教师）")
def record_grade(
    course_id: uuid.UUID,
    payload: GradeRecordCreate,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, course_id)
    _check_teacher(db, course, user)

    student = db.get(UserBrief, payload.student_id)
    if not student or student.role != "student":
        raise HTTPException(status_code=400, detail="学生不存在或不是学生角色")

    gpa = payload.gpa_point if payload.gpa_point is not None else gpa_from_score(payload.final_score)

    existing = (
        db.query(GradeRecord)
        .filter(
            GradeRecord.student_id == payload.student_id,
            GradeRecord.course_id == course_id,
            GradeRecord.semester == payload.semester,
        )
        .first()
    )
    if existing:
        before = float(existing.final_score or 0)
        existing.final_score = payload.final_score
        existing.gpa_point = gpa
        db.commit()
        db.refresh(existing)
        Instrumentation(db, request, str(user.id)).track(
            EVENT_GRADE_UPDATED, course_id=str(course_id),
            student_id=str(payload.student_id),
            properties={"before": str(before), "after": str(payload.final_score)},
        )
    else:
        record = GradeRecord(
            student_id=payload.student_id,
            course_id=course_id,
            semester=payload.semester,
            final_score=payload.final_score,
            gpa_point=gpa,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        Instrumentation(db, request, str(user.id)).track(
            EVENT_GRADE_RECORDED, course_id=str(course_id),
            student_id=str(payload.student_id), score=str(payload.final_score),
        )
        existing = record

    return _record_out(db, existing)


@course_router.delete("/{course_id}/grades/{student_id}", response_model=SuccessResponse, summary="删除成绩（教师）")
def delete_grade(
    course_id: uuid.UUID,
    student_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
    semester: str | None = None,
):
    course = _get_course(db, course_id)
    _check_teacher(db, course, user)

    query = db.query(GradeRecord).filter(
        GradeRecord.course_id == course_id,
        GradeRecord.student_id == student_id,
    )
    if semester:
        query = query.filter(GradeRecord.semester == semester)
    record = query.first()
    if not record:
        raise HTTPException(status_code=404, detail="成绩记录不存在")
    db.delete(record)
    db.commit()
    return SuccessResponse()