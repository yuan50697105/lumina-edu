# ============================================
# Lumina 墨光 · 辅导记录路由（V1.1 · D-05 · WBS-P 阶段 D）
# 教师/助教对学生的辅导纪要 CRUD
# 权限：教师（授课权）/ 管理员可写；学生仅可看自己的
# ============================================
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, get_current_user, require_role
from app.models import (
    Course,
    CourseBrief,
    Enrollment,
    TutoringSession,
    User,
)
from app.schemas import (
    Pagination,
    SuccessResponse,
    TutoringSessionCreate,
    TutoringSessionOut,
    TutoringSessionUpdate,
)

router = APIRouter(prefix="/tutoring", tags=["辅导记录（D-05）"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _check_can_write(db: Session, user: AuthUser, course_id: uuid.UUID | None) -> None:
    if user.role == "admin":
        return
    if user.role not in ("teacher",):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅教师可创建/编辑辅导记录")
    if course_id:
        c = db.get(CourseBrief, course_id)
        if not c:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
        if str(c.teacher_id) != str(user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权为该课程创建辅导记录")


def _check_can_read(db: Session, user: AuthUser, session_obj: TutoringSession) -> None:
    """读取权限：本人 / 辅导人 / 授课教师 / 管理员"""
    if user.role == "admin":
        return
    if str(user.id) == str(session_obj.student_id) or str(user.id) == str(session_obj.tutor_id):
        return
    if session_obj.course_id:
        c = db.get(CourseBrief, session_obj.course_id)
        if c and str(c.teacher_id) == str(user.id):
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该辅导记录")


def _to_out(db: Session, t: TutoringSession) -> TutoringSessionOut:
    stu = db.get(User, t.student_id)
    tutor = db.get(User, t.tutor_id)
    c = db.get(CourseBrief, t.course_id) if t.course_id else None
    return TutoringSessionOut(
        id=t.id,
        student_id=t.student_id,
        student_name=stu.name if stu else None,
        tutor_id=t.tutor_id,
        tutor_name=tutor.name if tutor else None,
        course_id=t.course_id,
        course_title=c.title if c else None,
        mode=t.mode,
        topic=t.topic,
        notes=t.notes,
        scheduled_at=t.scheduled_at,
        duration_min=t.duration_min,
        outcome=t.outcome,
        created_at=t.created_at,
    )


@router.get("/sessions", response_model=dict, summary="辅导记录列表")
def list_sessions(
    course_id: uuid.UUID | None = Query(None),
    student_id: uuid.UUID | None = Query(None),
    tutor_id: uuid.UUID | None = Query(None),
    outcome: str | None = Query(None, pattern="^(scheduled|completed|cancelled)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in ("teacher", "admin"):
        # 学生：仅能看自己
        if user.role != "student":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看")
        student_id = user.id

    q = db.query(TutoringSession)
    if course_id:
        q = q.filter(TutoringSession.course_id == course_id)
    if student_id:
        q = q.filter(TutoringSession.student_id == student_id)
    if tutor_id:
        q = q.filter(TutoringSession.tutor_id == tutor_id)
    if outcome:
        q = q.filter(TutoringSession.outcome == outcome)

    total = q.count()
    rows = q.order_by(TutoringSession.scheduled_at.desc()).offset(offset).limit(limit).all()
    return {
        "pagination": Pagination(
            offset=offset, limit=limit, total=total,
            has_more=(offset + limit) < total,
        ),
        "items": [_to_out(db, r) for r in rows],
    }


@router.post("/sessions", response_model=TutoringSessionOut, status_code=201,
             summary="新建辅导记录（教师）")
def create_session(
    payload: TutoringSessionCreate,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_can_write(db, user, payload.course_id)

    # 校验学生存在 & 在课程内（若指定课程）
    stu = db.get(User, payload.student_id)
    if not stu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生不存在")
    if stu.role != "student":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非学生用户")
    if payload.course_id:
        enrolled = db.query(Enrollment.id).filter(
            Enrollment.course_id == payload.course_id,
            Enrollment.user_id == payload.student_id,
            Enrollment.role == "student",
            Enrollment.status == "active",
        ).first()
        if not enrolled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="学生未选该课程")

    t = TutoringSession(
        student_id=payload.student_id,
        tutor_id=user.id,
        course_id=payload.course_id,
        mode=payload.mode,
        topic=payload.topic,
        notes=payload.notes,
        scheduled_at=payload.scheduled_at or _now(),
        duration_min=payload.duration_min,
        outcome="scheduled",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _to_out(db, t)


@router.get("/sessions/{session_id}", response_model=TutoringSessionOut, summary="辅导记录详情")
def get_session(
    session_id: uuid.UUID,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.get(TutoringSession, session_id)
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="辅导记录不存在")
    _check_can_read(db, user, t)
    return _to_out(db, t)


@router.patch("/sessions/{session_id}", response_model=TutoringSessionOut, summary="更新辅导记录")
def update_session(
    session_id: uuid.UUID,
    payload: TutoringSessionUpdate,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.get(TutoringSession, session_id)
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="辅导记录不存在")
    if user.role == "admin" or str(user.id) == str(t.tutor_id):
        pass
    elif user.role == "teacher":
        # 其他教师不能改
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅辅导人或管理员可编辑")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权编辑")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(t, field, value)
    db.commit()
    db.refresh(t)
    return _to_out(db, t)


@router.delete("/sessions/{session_id}", response_model=SuccessResponse, summary="删除辅导记录")
def delete_session(
    session_id: uuid.UUID,
    user: AuthUser = Depends(require_role("admin", "teacher")),
    db: Session = Depends(get_db),
):
    t = db.get(TutoringSession, session_id)
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="辅导记录不存在")
    if user.role != "admin" and str(user.id) != str(t.tutor_id):
        # 教师只能删自己的
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅辅导人或管理员可删除")
    db.delete(t)
    db.commit()
    return SuccessResponse()
