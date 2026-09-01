# ============================================
# Lumina 墨光 · 题库与考试路由（V1.1 · D-04 · WBS-P 阶段 D）
# 题库题目 / 试卷（组卷）/ 在线考试（自动评分）/ 统计 / 人工评分
# 权限：教师（授课权）管理题库与试卷；学生须已选课且卷已发布方可考试
# ============================================
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.instrumentation import (
    EVENT_EXAM_ATTEMPT_LIST,
    EVENT_EXAM_ATTEMPT_START,
    EVENT_EXAM_ATTEMPT_SUBMIT,
    EVENT_EXAM_ATTEMPT_VIEW,
    EVENT_EXAM_MANUAL_GRADE,
    EVENT_EXAM_PAPER_CLOSE,
    EVENT_EXAM_PAPER_CREATE,
    EVENT_EXAM_PAPER_DELETE,
    EVENT_EXAM_PAPER_GENERATE,
    EVENT_EXAM_PAPER_PUBLISH,
    EVENT_EXAM_PAPER_UPDATE,
    EVENT_EXAM_PAPER_VIEW,
    EVENT_EXAM_QUESTION_CREATE,
    EVENT_EXAM_QUESTION_DELETE,
    EVENT_EXAM_QUESTION_UPDATE,
    Instrumentation,
)
from app.models import (
    CourseBrief,
    ExamAttempt,
    ExamPaper,
    ExamPaperQuestion,
    ExamQuestion,
    UserBrief,
)
from app.modules.exam.scoring import is_objective, judge_answer, select_questions
from app.schemas import (
    AttemptOut,
    AttemptSubmitIn,
    AutoGenerateIn,
    ManualGradeIn,
    PaperCreate,
    PaperOut,
    PaperQuestionIn,
    PaperQuestionOut,
    PaperStatsOut,
    PaperUpdate,
    Pagination,
    QuestionCreate,
    QuestionOut,
    QuestionUpdate,
    StartAttemptOut,
    SuccessResponse,
)

router = APIRouter(prefix="", tags=["题库与考试"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── 通用工具 ───
def _get_course(db: Session, course_id) -> CourseBrief:
    c = db.get(CourseBrief, course_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")
    return c


def _check_teacher(db: Session, course: CourseBrief, user: UserBrief) -> None:
    """授课权限：本课教师或管理员"""
    if user.role == "admin":
        return
    if str(course.teacher_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该课程的题库/考试")


def _is_enrolled(db: Session, course_id, student_id) -> bool:
    from sqlalchemy import text
    row = db.execute(
        text("SELECT 1 FROM enrollments WHERE course_id = :c AND user_id = :s AND status = 'active'"),
        {"c": str(course_id), "s": str(student_id)},
    ).first()
    return bool(row)


def _get_question(db: Session, question_id) -> ExamQuestion:
    q = db.get(ExamQuestion, question_id)
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    return q


def _get_paper(db: Session, paper_id) -> ExamPaper:
    p = db.get(ExamPaper, paper_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")
    return p


def _check_paper_teacher(db: Session, paper: ExamPaper, user: UserBrief) -> None:
    _check_teacher(db, _get_course(db, paper.course_id), user)


def _get_attempt(db: Session, attempt_id) -> ExamAttempt:
    a = db.get(ExamAttempt, attempt_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考试记录不存在")
    return a


def _paper_rows(db: Session, paper_id):
    """试卷题目明细（pq, q）有序（分数表）"""
    return (
        db.query(ExamPaperQuestion, ExamQuestion)
        .join(ExamQuestion, ExamQuestion.id == ExamPaperQuestion.question_id)
        .filter(ExamPaperQuestion.paper_id == paper_id)
        .order_by(ExamPaperQuestion.order_num.asc())
        .all()
    )


def _paper_questions(db: Session, paper, include_answer: bool) -> list[PaperQuestionOut]:
    out = []
    for pq, q in _paper_rows(db, paper.id):
        out.append(PaperQuestionOut(
            id=pq.id, question_id=q.id, order_num=pq.order_num, score=pq.score,
            qtype=q.qtype, title=q.title, difficulty=q.difficulty,
            options=q.options, answer=q.answer if include_answer else None,
        ))
    return out


def _count_total(db: Session, paper_id) -> tuple[int, int]:
    items = db.query(ExamPaperQuestion).filter(ExamPaperQuestion.paper_id == paper_id).all()
    return len(items), sum(r.score or 0 for r in items)


def _my_attempt(db: Session, paper_id, user) -> dict | None:
    a = (
        db.query(ExamAttempt)
        .filter(ExamAttempt.paper_id == paper_id, ExamAttempt.student_id == user.id)
        .first()
    )
    if not a:
        return None
    return {
        "id": str(a.id),
        "status": a.status,
        "auto_score": a.auto_score or 0,
        "manual_score": a.manual_score or 0,
        "total_score": a.total_score or 0,
        "started_at": a.started_at.isoformat() if a.started_at else None,
        "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
    }


def _paper_out(db: Session, paper: ExamPaper, user: UserBrief) -> PaperOut:
    out = PaperOut.model_validate(paper)
    c = db.get(CourseBrief, paper.course_id)
    out.course_title = c.title if c else None
    out.question_count, out.total_score = _count_total(db, paper.id)
    if user.role in ("teacher", "admin"):
        out.questions = _paper_questions(db, paper, include_answer=True)
    else:
        out.questions = _paper_questions(db, paper, include_answer=False)
        out.my_attempt = _my_attempt(db, paper.id, user)
    return out


def _attempt_out(db: Session, a: ExamAttempt, with_answers: bool = False) -> AttemptOut:
    out = AttemptOut.model_validate(a)
    u = db.get(UserBrief, a.student_id)
    out.student_name = u.name if u else None
    p = db.get(ExamPaper, a.paper_id)
    out.paper_title = p.title if p else None
    out.question_count = _count_total(db, a.paper_id)[0]
    if not with_answers:
        out.answers = None
    return out


# ════════════════════════════════════════════
# 一、题库题目
# ════════════════════════════════════════════
@router.get("/courses/{course_id}/questions", response_model=dict, summary="题库列表（教师）")
def list_questions(
    course_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
    qtype: str | None = None,
    difficulty: str | None = None,
    tag: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """课程题库：教师/管理员可看（含答案）；普通用户凭课程参与查看题目（不含答案）"""
    course = _get_course(db, course_id)
    query = db.query(ExamQuestion).filter(ExamQuestion.course_id == course_id)
    if qtype:
        query = query.filter(ExamQuestion.qtype == qtype)
    if difficulty:
        query = query.filter(ExamQuestion.difficulty == difficulty)
    if tag:
        # 标签精确过滤（JSON 数组，取回后在 Python 过滤以保证跨库一致）
        rows = query.all()
        rows = [r for r in rows if tag in {str(t) for t in (r.tags or [])}]
        total = len(rows)
        items = rows[offset: offset + min(limit, 100)]
        has_more = offset + min(limit, 100) < total
    else:
        total = query.count()
        limit = min(limit, 100)
        items = query.order_by(ExamQuestion.created_at.desc()).offset(offset).limit(limit + 1).all()
        has_more = len(items) > limit
        items = items[:limit]

    include_answer = user.role in ("teacher", "admin")
    data = []
    for q in items:
        item = QuestionOut.model_validate(q)
        if not include_answer:
            item.answer = None
        data.append(item)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_PAPER_VIEW, course_id=str(course_id), scope="questions"
    )
    return {"code": 0, "data": data, "pagination": Pagination(offset=offset, limit=limit, total=total, has_more=has_more)}


@router.post("/courses/{course_id}/questions", response_model=QuestionOut, status_code=201, summary="新建题目（教师）")
def create_question(
    course_id: uuid.UUID,
    payload: QuestionCreate,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, course_id)
    _check_teacher(db, course, user)

    if is_objective(payload.qtype) and not payload.options:
        raise HTTPException(status_code=422, detail="客观题必须提供选项 options")
    if is_objective(payload.qtype) and not payload.answer:
        raise HTTPException(status_code=422, detail="客观题必须提供答案 answer")

    q = ExamQuestion(course_id=course_id, created_by=user.id, **payload.model_dump(exclude={"course_id"}))
    db.add(q)
    db.commit()
    db.refresh(q)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_QUESTION_CREATE, course_id=str(course_id), question_id=str(q.id),
        qtype=q.qtype, difficulty=q.difficulty,
    )
    return QuestionOut.model_validate(q)


@router.get("/questions/{question_id}", response_model=QuestionOut, summary="题目详情")
def get_question(
    question_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _get_question(db, question_id)
    out = QuestionOut.model_validate(q)
    if user.role not in ("teacher", "admin"):
        out.answer = None
        # 非教师查看题目需有课程参与
        if not _is_enrolled(db, q.course_id, user.id):
            raise HTTPException(status_code=403, detail="无权查看该题目")
    return out


@router.patch("/questions/{question_id}", response_model=QuestionOut, summary="更新题目（教师）")
def update_question(
    question_id: uuid.UUID,
    payload: QuestionUpdate,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _get_question(db, question_id)
    _check_teacher(db, _get_course(db, q.course_id), user)

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(q, key, value)
    db.commit()
    db.refresh(q)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_QUESTION_UPDATE, course_id=str(q.course_id), question_id=str(q.id), fields=list(data.keys())
    )
    return QuestionOut.model_validate(q)


@router.delete("/questions/{question_id}", response_model=SuccessResponse, summary="删除题目（教师）")
def delete_question(
    question_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _get_question(db, question_id)
    _check_teacher(db, _get_course(db, q.course_id), user)
    paper_links = (
        db.query(ExamPaperQuestion).filter(ExamPaperQuestion.question_id == question_id).all()
    )
    for link in paper_links:
        db.delete(link)
    db.delete(q)
    db.commit()
    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_QUESTION_DELETE, course_id=str(q.course_id), question_id=str(q.id)
    )
    return SuccessResponse()


# ════════════════════════════════════════════
# 二、试卷（组卷）
# ════════════════════════════════════════════
@router.get("/courses/{course_id}/papers", response_model=dict, summary="课程试卷列表")
def list_papers(
    course_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20,
    offset: int = 0,
):
    course = _get_course(db, course_id)
    query = db.query(ExamPaper).filter(ExamPaper.course_id == course_id)
    if user.role == "student":
        query = query.filter(ExamPaper.status == "published")
    elif user.role not in ("teacher", "admin"):
        # 其他参与角色只能看公开
        query = query.filter(ExamPaper.status == "published")

    total = query.count()
    limit = min(limit, 100)
    items = query.order_by(ExamPaper.created_at.desc()).offset(offset).limit(limit + 1).all()
    has_more = len(items) > limit
    items = items[:limit]

    data = []
    for p in items:
        out = PaperOut.model_validate(p)
        out.question_count, out.total_score = _count_total(db, p.id)
        c = db.get(CourseBrief, p.course_id)
        out.course_title = c.title if c else None
        if user.role in ("teacher", "admin"):
            out.questions = []
        else:
            out.questions = []
            out.my_attempt = _my_attempt(db, p.id, user)
        data.append(out)
    return {"code": 0, "data": data, "pagination": Pagination(offset=offset, limit=limit, total=total, has_more=has_more)}


@router.post("/courses/{course_id}/papers", response_model=PaperOut, status_code=201, summary="新建试卷（教师）")
def create_paper(
    course_id: uuid.UUID,
    payload: PaperCreate,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, course_id)
    _check_teacher(db, course, user)
    p = ExamPaper(course_id=course_id, created_by=user.id, **payload.model_dump(exclude={"course_id"}))
    db.add(p)
    db.commit()
    db.refresh(p)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_PAPER_CREATE, course_id=str(course_id), paper_id=str(p.id),
        duration_minutes=str(p.duration_minutes),
    )
    return _paper_out(db, p, user)


@router.get("/papers/{paper_id}", response_model=PaperOut, summary="试卷详情")
def get_paper(
    paper_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = _get_paper(db, paper_id)
    if user.role == "student" and p.status != "published":
        raise HTTPException(status_code=403, detail="试卷未发布")
    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_PAPER_VIEW, course_id=str(p.course_id), paper_id=str(p.id),
        role=user.role,
    )
    return _paper_out(db, p, user)


@router.patch("/papers/{paper_id}", response_model=PaperOut, summary="更新试卷（教师）")
def update_paper(
    paper_id: uuid.UUID,
    payload: PaperUpdate,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = _get_paper(db, paper_id)
    _check_paper_teacher(db, p, user)

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(p, key, value)
    db.commit()
    db.refresh(p)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_PAPER_UPDATE, course_id=str(p.course_id), paper_id=str(p.id), fields=list(data.keys())
    )
    return _paper_out(db, p, user)


@router.delete("/papers/{paper_id}", response_model=SuccessResponse, summary="删除试卷（教师）")
def delete_paper(
    paper_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = _get_paper(db, paper_id)
    _check_paper_teacher(db, p, user)
    db.delete(p)  # 级联删除 paper_questions / attempts（ondelete CASCADE）
    db.commit()
    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_PAPER_DELETE, course_id=str(p.course_id), paper_id=str(p.id)
    )
    return SuccessResponse()


@router.post("/papers/{paper_id}/questions", response_model=PaperOut, status_code=201, summary="加入题目（教师）")
def add_paper_question(
    paper_id: uuid.UUID,
    payload: PaperQuestionIn,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = _get_paper(db, paper_id)
    _check_paper_teacher(db, p, user)
    q = _get_question(db, payload.question_id)
    if str(q.course_id) != str(p.course_id):
        raise HTTPException(status_code=400, detail="题目不属于本课程")

    exists = (
        db.query(ExamPaperQuestion)
        .filter(ExamPaperQuestion.paper_id == paper_id, ExamPaperQuestion.question_id == payload.question_id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="该题已在试卷中")

    order = (
        db.query(ExamPaperQuestion)
        .filter(ExamPaperQuestion.paper_id == paper_id)
        .count()
    )
    link = ExamPaperQuestion(
        paper_id=paper_id, question_id=payload.question_id,
        order_num=order, score=payload.score or q.score,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return _paper_out(db, p, user)


@router.delete("/papers/{paper_id}/questions/{pq_id}", response_model=SuccessResponse, summary="移除题目（教师）")
def remove_paper_question(
    paper_id: uuid.UUID,
    pq_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = _get_paper(db, paper_id)
    _check_paper_teacher(db, p, user)
    link = db.get(ExamPaperQuestion, pq_id)
    if not link or str(link.paper_id) != str(paper_id):
        raise HTTPException(status_code=404, detail="试卷题目不存在")
    db.delete(link)
    db.commit()
    # 重排剩余 order_num
    rows = (
        db.query(ExamPaperQuestion)
        .filter(ExamPaperQuestion.paper_id == paper_id)
        .order_by(ExamPaperQuestion.order_num.asc())
        .all()
    )
    for idx, row in enumerate(rows):
        row.order_num = idx
    db.commit()
    return SuccessResponse()


@router.post("/papers/{paper_id}/generate", response_model=PaperOut, summary="智能组卷（教师 · 按条件抽题）")
def generate_paper(
    paper_id: uuid.UUID,
    payload: AutoGenerateIn,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按难度/题型/标签从课程题库随机抽题追加到试卷（不重复抽已存在题目）。"""
    p = _get_paper(db, paper_id)
    _check_paper_teacher(db, p, user)

    existing = {
        str(r.question_id) for r in
        db.query(ExamPaperQuestion).filter(ExamPaperQuestion.paper_id == paper_id).all()
    }
    candidates = db.query(ExamQuestion).filter(ExamQuestion.course_id == p.course_id).all()
    picked = select_questions(
        candidates,
        count=payload.count,
        difficulty=payload.difficulty,
        qtype_filter=payload.qtype_filter,
        tag=payload.tag,
        exclude_ids=existing,
    )
    order = len(existing)
    for q in picked:
        link = ExamPaperQuestion(
            paper_id=paper_id, question_id=q.id,
            order_num=order, score=payload.score or q.score,
        )
        db.add(link)
        order += 1
    db.commit()

    # 未随机到的过滤条件——仍按确定性优先抽题（保持上文 select_questions 不引入随机种子，
    # 保证同条件重复调用结果稳定）
    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_PAPER_GENERATE, course_id=str(p.course_id), paper_id=str(p.id),
        requested=str(payload.count), picked=str(len(picked)),
        difficulty=payload.difficulty, qtype=payload.qtype_filter, tag=payload.tag,
    )
    return _paper_out(db, p, user)


@router.post("/papers/{paper_id}/publish", response_model=PaperOut, summary="发布试卷（教师）")
def publish_paper(
    paper_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = _get_paper(db, paper_id)
    _check_paper_teacher(db, p, user)
    count, total = _count_total(db, paper_id)
    if count == 0:
        raise HTTPException(status_code=400, detail="试卷为空，请先组卷")
    p.status = "published"
    db.commit()
    db.refresh(p)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_PAPER_PUBLISH, course_id=str(p.course_id), paper_id=str(p.id),
        question_count=str(count), total_score=str(total),
    )
    return _paper_out(db, p, user)


@router.post("/papers/{paper_id}/close", response_model=PaperOut, summary="关闭试卷（教师）")
def close_paper(
    paper_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = _get_paper(db, paper_id)
    _check_paper_teacher(db, p, user)
    p.status = "closed"
    db.commit()
    db.refresh(p)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_PAPER_CLOSE, course_id=str(p.course_id), paper_id=str(p.id)
    )
    return _paper_out(db, p, user)


# ════════════════════════════════════════════
# 三、在线考试
# ════════════════════════════════════════════
@router.get("/papers/{paper_id}/attempt/me", response_model=dict, summary="我的考试状态（学生）")
def my_attempt_me(
    paper_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = _get_paper(db, paper_id)
    if not _is_enrolled(db, p.course_id, user.id):
        raise HTTPException(status_code=403, detail="请先选课再参加考试")
    a = (
        db.query(ExamAttempt)
        .filter(ExamAttempt.paper_id == paper_id, ExamAttempt.student_id == user.id)
        .first()
    )
    if not a:
        return {"my_attempt": None}
    return {"my_attempt": _attempt_out(db, a, with_answers=True)}


@router.post("/papers/{paper_id}/start", response_model=StartAttemptOut, status_code=201, summary="开始考试（学生）")
def start_attempt(
    paper_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    p = _get_paper(db, paper_id)
    course = _get_course(db, p.course_id)
    if not _is_enrolled(db, p.course_id, user.id):
        raise HTTPException(status_code=403, detail="请先选课再参加考试")
    if p.status != "published":
        raise HTTPException(status_code=403, detail="试卷未发布，不能参加")
    now = _now()
    if p.start_at and now < p.start_at:
        raise HTTPException(status_code=403, detail="考试尚未开始")
    if p.end_at and now > p.end_at:
        raise HTTPException(status_code=403, detail="考试已结束")

    a = (
        db.query(ExamAttempt)
        .filter(ExamAttempt.paper_id == paper_id, ExamAttempt.student_id == user.id)
        .first()
    )
    if a and a.status == "submitted":
        raise HTTPException(status_code=409, detail="已提交过，不能重复考试")
    if not a:
        a = ExamAttempt(paper_id=paper_id, student_id=user.id, status="in_progress")
        db.add(a)
        db.commit()
        db.refresh(a)

    # 截止 = 开始 + 时长 与 试卷 end_at 的较早期
    start = a.started_at or now
    end_at = start + timedelta(minutes=p.duration_minutes or 60)
    if p.end_at and end_at > p.end_at:
        end_at = p.end_at

    questions = _paper_questions(db, p, include_answer=False)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_ATTEMPT_START, course_id=str(p.course_id), paper_id=str(paper_id),
        attempt_id=str(a.id), question_count=str(len(questions)),
    )
    return StartAttemptOut(
        attempt_id=a.id, started_at=start, end_at=end_at,
        duration_minutes=p.duration_minutes or 60, questions=questions,
    )


@router.post("/papers/{paper_id}/submit", response_model=AttemptOut, summary="提交作答（学生 · 自动评分）")
def submit_attempt(
    paper_id: uuid.UUID,
    payload: AttemptSubmitIn,
    request: Request,
    user: UserBrief = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    p = _get_paper(db, paper_id)
    a = (
        db.query(ExamAttempt)
        .filter(ExamAttempt.paper_id == paper_id, ExamAttempt.student_id == user.id)
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="请先开始考试")
    if a.status == "submitted":
        raise HTTPException(status_code=409, detail="已提交，不能重复提交")

    rows = _paper_rows(db, paper_id)
    valid = {str(q.id): (pq, q) for pq, q in rows}
    for item in payload.answers:
        if str(item.question_id) not in valid:
            raise HTTPException(status_code=400, detail="作答包含不在本试卷中的题目")

    entries = []
    auto_score = 0
    for item in payload.answers:
        pq, q = valid[str(item.question_id)]
        correct = judge_answer(q.qtype, q.answer, item.answer)
        entry: dict = {"question_id": str(q.id), "answer": item.answer, "correct": correct,
                       "score": pq.score or q.score}
        if correct is True:
            auto_score += (pq.score or q.score)
        entries.append(entry)

    a.answers = entries
    a.auto_score = auto_score
    a.submitted_at = _now()
    a.status = "submitted"
    a.total_score = auto_score + (a.manual_score or 0)
    db.commit()
    db.refresh(a)

    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_ATTEMPT_SUBMIT, course_id=str(p.course_id), paper_id=str(p.id),
        attempt_id=str(a.id), answered=str(len(entries)), auto_score=str(auto_score),
    )
    return _attempt_out(db, a, with_answers=True)


@router.get("/papers/{paper_id}/attempts", response_model=list[AttemptOut], summary="提交列表（教师）")
def list_attempts(
    paper_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = _get_paper(db, paper_id)
    _check_paper_teacher(db, p, user)
    items = (
        db.query(ExamAttempt)
        .filter(ExamAttempt.paper_id == paper_id)
        .order_by(ExamAttempt.submitted_at.desc())
        .all()
    )
    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_ATTEMPT_LIST, course_id=str(p.course_id), paper_id=str(p.id),
        count=str(len(items)),
    )
    return [_attempt_out(db, a) for a in items]


@router.get("/attempts/{attempt_id}", response_model=AttemptOut, summary="答卷详情（本人/教师）")
def get_attempt(
    attempt_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a = _get_attempt(db, attempt_id)
    if user.role not in ("teacher", "admin") and str(a.student_id) != str(user.id):
        raise HTTPException(status_code=403, detail="无权查看他人答卷")
    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_ATTEMPT_VIEW, paper_id=str(a.paper_id), attempt_id=str(a.id)
    )
    return _attempt_out(db, a, with_answers=True)


@router.post("/attempts/{attempt_id}/manual-grade", response_model=AttemptOut, summary="主观题人工评分（教师）")
def manual_grade(
    attempt_id: uuid.UUID,
    payload: ManualGradeIn,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    a = _get_attempt(db, attempt_id)
    p = _get_paper(db, a.paper_id)
    _check_paper_teacher(db, p, user)
    if a.status != "submitted":
        raise HTTPException(status_code=400, detail="该考生尚未交卷")

    q = _get_question(db, payload.question_id)
    if is_objective(q.qtype):
        raise HTTPException(status_code=400, detail="客观题自动评分，无需人工评分")
    # 该题满分上限
    link = (
        db.query(ExamPaperQuestion)
        .filter(ExamPaperQuestion.paper_id == a.paper_id, ExamPaperQuestion.question_id == payload.question_id)
        .first()
    )
    if not link:
        raise HTTPException(status_code=400, detail="该题不在本次试卷中")
    if payload.score > (link.score or q.score):
        raise HTTPException(status_code=400, detail=f"分值超出该题满分 {link.score or q.score}")

    answers = a.answers or []
    target = next((e for e in answers if str(e.get("question_id")) == str(payload.question_id)), None)
    if not target:
        raise HTTPException(status_code=404, detail="该考生未作答此题")

    target["manual_score"] = payload.score
    a.answers = answers
    a.manual_score = sum(e.get("manual_score") or 0 for e in answers)
    a.total_score = (a.auto_score or 0) + a.manual_score
    db.commit()
    db.refresh(a)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_MANUAL_GRADE, course_id=str(p.course_id), paper_id=str(p.id),
        attempt_id=str(a.id), question_id=str(payload.question_id), score=str(payload.score),
    )
    return _attempt_out(db, a, with_answers=True)


# ════════════════════════════════════════════
# 四、统计
# ════════════════════════════════════════════
@router.get("/papers/{paper_id}/stats", response_model=PaperStatsOut, summary="考试统计（教师）")
def paper_stats(
    paper_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = _get_paper(db, paper_id)
    _check_paper_teacher(db, p, user)

    attempts = (
        db.query(ExamAttempt)
        .filter(ExamAttempt.paper_id == paper_id, ExamAttempt.status == "submitted")
        .all()
    )
    scores = [a.total_score or 0 for a in attempts]
    rows = _paper_rows(db, paper_id)

    question_stats = []
    for pq, q in rows:
        qid = str(q.id)
        answered = correct = manual_sum = manual_n = 0
        for a in attempts:
            for entry in (a.answers or []):
                if str(entry.get("question_id")) != qid:
                    continue
                answered += 1
                if entry.get("correct") is True:
                    correct += 1
                m = entry.get("manual_score")
                if m is not None:
                    manual_sum += int(m)
                    manual_n += 1
        question_stats.append({
            "question_id": qid,
            "title": q.title,
            "qtype": q.qtype,
            "score": pq.score,
            "answered_count": answered,
            "correct_count": correct,
            "accuracy": round(correct / answered, 4) if answered else None,
            "avg_manual_score": round(manual_sum / manual_n, 2) if manual_n else None,
        })

    Instrumentation(db, request, str(user.id)).track(
        EVENT_EXAM_PAPER_VIEW, course_id=str(p.course_id), paper_id=str(p.id), scope="stats"
    )
    return PaperStatsOut(
        paper_id=p.id,
        submitted_count=len(attempts),
        average_score=round(sum(scores) / len(scores), 2) if scores else 0,
        highest_score=max(scores) if scores else 0,
        lowest_score=min(scores) if scores else 0,
        question_stats=question_stats,
    )