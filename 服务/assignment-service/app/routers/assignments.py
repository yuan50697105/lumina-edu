# ============================================
# Lumina 墨光 · 作业路由
# /assignments 列表/详情/提交/批阅 · 教师发布
# ============================================
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..dependencies import get_current_user, require_role
from ..instrumentation import (
    EVENT_ASSIGNMENT_CREATED,
    EVENT_ASSIGNMENT_GRADED,
    EVENT_ASSIGNMENT_SUBMITTED,
    EVENT_ASSIGNMENT_UPDATED,
    EVENT_ASSIGNMENT_VIEW,
    Instrumentation,
)
from ..models import Assignment, CourseBrief, Grade, Submission, UserBrief
from ..schemas import (
    AssignmentCreate,
    AssignmentOut,
    AssignmentUpdate,
    GradeCreate,
    GradeOut,
    Pagination,
    SubmissionOut,
    SuccessResponse,
)

router = APIRouter(prefix="/assignments", tags=["作业"])
course_router = APIRouter(prefix="/courses", tags=["作业·课程"])


# ─── 工具函数 ───
def _get_assignment(db: Session, assignment_id) -> Assignment:
    a = db.get(Assignment, assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="作业不存在")
    return a


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
        raise HTTPException(status_code=403, detail="无权操作该课程的作业")


def _is_enrolled(db: Session, course_id, student_id) -> bool:
    """学生是否已选课（active）"""
    row = db.execute(
        text("SELECT 1 FROM enrollments WHERE course_id = :c AND user_id = :s AND status = 'active'"),
        {"c": str(course_id), "s": str(student_id)},
    ).first()
    return bool(row)


def _is_late(due_at: datetime | None, submitted_at: datetime) -> bool:
    if not due_at:
        return False
    return submitted_at > due_at


def _course_title(db: Session, course_id) -> str | None:
    c = db.get(CourseBrief, course_id)
    return c.title if c else None


def _grade_for(db: Session, submission_id) -> GradeOut | None:
    grade = db.query(Grade).filter(Grade.submission_id == submission_id).first()
    if not grade:
        return None
    return GradeOut.model_validate(grade)


def _assignment_out(db: Session, a: Assignment, user: UserBrief, my_status=True) -> AssignmentOut:
    out = AssignmentOut.model_validate(a)
    out.course_title = _course_title(db, a.course_id)
    out.submission_count = db.query(Submission).filter(Submission.assignment_id == a.id).count()
    if my_status and user.role == "student":
        sub = (db.query(Submission)
               .filter(Submission.assignment_id == a.id, Submission.student_id == user.id)
               .first())
        out.my_status = "graded" if (sub and _grade_for(db, sub.id)) else ("submitted" if sub else "not_submitted")
    return out


def _submission_out(db: Session, s: Submission) -> SubmissionOut:
    out = SubmissionOut.model_validate(s)
    u = db.get(UserBrief, s.student_id)
    out.student_name = u.name if u else None
    grade = db.query(Grade).filter(Grade.submission_id == s.id).first()
    out.graded = bool(grade)
    if grade:
        out.grade = GradeOut.model_validate(grade)
    return out


# ─── 作业列表 / 详情 ───
@router.get("", response_model=dict, summary="作业列表")
def list_assignments(
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
    course_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """作业列表：学生只看 published；教师/管理员看自己课程的（含 draft）"""
    query = db.query(Assignment)
    if course_id:
        query = query.filter(Assignment.course_id == course_id)
    if status_filter:
        query = query.filter(Assignment.status == status_filter)
    elif user.role == "student":
        query = query.filter(Assignment.status == "published")

    if user.role == "teacher":
        teacher_courses = db.execute(
            text("SELECT id FROM courses WHERE teacher_id = :t"), {"t": str(user.id)}
        ).all()
        ids = [r[0] for r in teacher_courses]
        if not ids:
            return {"code": 0, "data": [], "pagination": Pagination(offset=offset, limit=limit, total=0, has_more=False)}
        query = query.filter(Assignment.course_id.in_(ids))

    total = query.count()
    limit = min(limit, 100)
    items = query.order_by(Assignment.created_at.desc()).offset(offset).limit(limit + 1).all()
    has_more = len(items) > limit
    items = items[:limit]

    data = [_assignment_out(db, a, user) for a in items]
    Instrumentation(db, request, str(user.id)).track(
        EVENT_ASSIGNMENT_VIEW, course_id=str(course_id) if course_id else None
    )
    return {"code": 0, "data": data, "pagination": Pagination(offset=offset, limit=limit, total=total, has_more=has_more)}


@router.get("/{assignment_id}", response_model=AssignmentOut, summary="作业详情")
def get_assignment(
    assignment_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a = _get_assignment(db, assignment_id)
    if a.status != "published" and user.role == "student":
        raise HTTPException(status_code=403, detail="作业未发布")
    Instrumentation(db, request, str(user.id)).track(
        EVENT_ASSIGNMENT_VIEW, assignment_id=str(assignment_id), course_id=str(a.course_id)
    )
    return _assignment_out(db, a, user)


# ─── 教师：发布 / 更新 / 删除 ───
@course_router.post("/{course_id}/assignments", response_model=AssignmentOut, status_code=201, summary="发布作业（教师）")
def create_assignment(
    course_id: uuid.UUID,
    payload: AssignmentCreate,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, course_id)
    _check_teacher(db, course, user)

    if user.role == "teacher" and course.status != "published":
        raise HTTPException(status_code=400, detail="课程未发布，不能发布作业")

    a = Assignment(course_id=course_id, **payload.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)

    Instrumentation(db, request, str(user.id)).track(
        EVENT_ASSIGNMENT_CREATED, course_id=str(course_id), assignment_id=str(a.id), ai_grading=a.ai_grading
    )
    return _assignment_out(db, a, user)


@router.patch("/{assignment_id}", response_model=AssignmentOut, summary="更新作业（教师）")
def update_assignment(
    assignment_id: uuid.UUID,
    payload: AssignmentUpdate,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a = _get_assignment(db, assignment_id)
    _check_teacher(db, _get_course(db, a.course_id), user)

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(a, key, value)
    db.commit()
    db.refresh(a)

    Instrumentation(db, request, str(user.id)).track(
        EVENT_ASSIGNMENT_UPDATED, course_id=str(a.course_id), assignment_id=str(a.id), fields=list(data.keys())
    )
    return _assignment_out(db, a, user)


@router.delete("/{assignment_id}", response_model=SuccessResponse, summary="删除作业（教师）")
def delete_assignment(
    assignment_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a = _get_assignment(db, assignment_id)
    _check_teacher(db, _get_course(db, a.course_id), user)
    db.delete(a)
    db.commit()
    return SuccessResponse()


# ─── 学生：提交 ───
@router.post("/{assignment_id}/submit", response_model=SubmissionOut, status_code=201, summary="提交作业（学生）")
async def submit_assignment(
    assignment_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(require_role("student")),
    db: Session = Depends(get_db),
    text_answer: str | None = Form(None),
    submission_note: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    a = _get_assignment(db, assignment_id)
    if a.status == "closed":
        raise HTTPException(status_code=400, detail="作业已关闭，不能提交")
    if not _is_enrolled(db, a.course_id, user.id):
        raise HTTPException(status_code=403, detail="请先选课再提交作业")

    # 文件持久化（临时本地存储，正式环境接 MinIO）
    file_urls = []
    if file and file.filename:
        file.filename = os.path.basename(file.filename)
        safe_name = f"{uuid.uuid4().hex}-{file.filename}"
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        dest = os.path.join(settings.UPLOAD_DIR, safe_name)
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail="文件超过大小限制")
        with open(dest, "wb") as f:
            f.write(content)
        file_urls.append(f"/files/{safe_name}")

    now = datetime.now(timezone.utc)
    existing = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id, Submission.student_id == user.id)
        .first()
    )
    if existing:
        # 覆盖更新（重交一次计一条，最新覆盖）
        existing.file_urls = file_urls or existing.file_urls
        existing.text_answer = text_answer if text_answer is not None else existing.text_answer
        existing.submission_note = submission_note if submission_note is not None else existing.submission_note
        existing.submitted_at = now
        existing.late = _is_late(a.due_at, now)
        db.commit()
        db.refresh(existing)
        sub = existing
    else:
        sub = Submission(
            assignment_id=assignment_id,
            student_id=user.id,
            file_urls=file_urls or None,
            text_answer=text_answer,
            submission_note=submission_note,
            submitted_at=now,
            late=_is_late(a.due_at, now),
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

    Instrumentation(db, request, str(user.id)).track(
        EVENT_ASSIGNMENT_SUBMITTED, course_id=str(a.course_id), assignment_id=str(assignment_id),
        submission_id=str(sub.id), late=str(sub.late),
    )
    return _submission_out(db, sub)


# ─── 提交查看 ───
@router.get("/{assignment_id}/submissions", response_model=list[SubmissionOut], summary="提交列表（教师）")
def list_submissions(
    assignment_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a = _get_assignment(db, assignment_id)
    _check_teacher(db, _get_course(db, a.course_id), user)

    subs = (db.query(Submission)
            .filter(Submission.assignment_id == assignment_id)
            .order_by(Submission.submitted_at)
            .all())
    return [_submission_out(db, s) for s in subs]


@router.get("/{assignment_id}/submissions/me", response_model=SubmissionOut | None, summary="我的提交（学生）")
def my_submission(
    assignment_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a = _get_assignment(db, assignment_id)
    sub = (db.query(Submission)
           .filter(Submission.assignment_id == assignment_id, Submission.student_id == user.id)
           .first())
    if not sub:
        return None
    return _submission_out(db, sub)


# ─── 批阅（教师手动；AI 批阅由 2.7 接入）───
@router.post("/{assignment_id}/grade", response_model=GradeOut, summary="批阅作业（教师/AI）")
def grade_submission(
    assignment_id: uuid.UUID,
    payload: GradeCreate,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
    submission_id: uuid.UUID | None = None,
):
    """批阅指定学生作业：
    - 提交体带 total_score/feedback
    - 通过 query 参数 submission_id 指定被批提交
    """
    a = _get_assignment(db, assignment_id)
    course = _get_course(db, a.course_id)
    _check_teacher(db, course, user)

    if not submission_id:
        raise HTTPException(status_code=400, detail="缺少参数 submission_id")

    sub = db.get(Submission, submission_id)
    if not sub or sub.assignment_id != assignment_id:
        raise HTTPException(status_code=404, detail="提交记录不存在")

    if payload.total_score > a.max_score:
        raise HTTPException(status_code=400, detail=f"分数超出满分 {a.max_score}")

    grade = db.query(Grade).filter(Grade.submission_id == submission_id).first()
    if grade:
        # 更新批阅
        grade.total_score = payload.total_score
        grade.grade_letter = payload.grade_letter or _letter(payload.total_score, a.max_score)
        grade.feedback = payload.feedback if payload.feedback is not None else grade.feedback
        grade.rubric_scores = payload.rubric_scores if payload.rubric_scores is not None else grade.rubric_scores
        grade.graded_at = datetime.now(timezone.utc)
    else:
        grade = Grade(
            submission_id=submission_id,
            total_score=payload.total_score,
            grade_letter=payload.grade_letter or _letter(payload.total_score, a.max_score),
            feedback=payload.feedback,
            rubric_scores=payload.rubric_scores,
            graded_by="teacher",
            grader_id=user.id,
        )
        db.add(grade)
    db.commit()
    db.refresh(grade)

    Instrumentation(db, request, str(user.id)).track(
        EVENT_ASSIGNMENT_GRADED, course_id=str(a.course_id), assignment_id=str(assignment_id),
        submission_id=str(submission_id), graded_by="teacher", score=str(payload.total_score),
    )
    return GradeOut.model_validate(grade)


def _letter(score, max_score) -> str:
    """按百分比例映射 A-F（与成绩模块一致）"""
    ratio = float(score) / max_score if max_score else 0
    if ratio >= 0.9: return "A"
    if ratio >= 0.8: return "B"
    if ratio >= 0.7: return "C"
    if ratio >= 0.6: return "D"
    return "F"