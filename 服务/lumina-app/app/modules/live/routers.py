# ============================================
# Lumina 墨光 · 直播课堂路由（V1.1 · D-01 · WBS-P 阶段 D）
# 房间 / 参与 / 举手 / 聊天 / 点名 / 答题
# 轻量方案：实时通过轮询（after_id 增量拉取）+ 埋点；流媒体走可插拔适配层
# ============================================
import datetime
import json
import random
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.instrumentation import (
    EVENT_LIVE_CALL,
    EVENT_LIVE_CALL_RESPOND,
    EVENT_LIVE_CHAT,
    EVENT_LIVE_JOIN,
    EVENT_LIVE_LEAVE,
    EVENT_LIVE_QUIZ_ANSWER,
    EVENT_LIVE_QUIZ_CLOSE,
    EVENT_LIVE_QUIZ_START,
    EVENT_LIVE_RAISE_HAND,
    EVENT_LIVE_ROOM_CREATE,
    EVENT_LIVE_ROOM_END,
    EVENT_LIVE_ROOM_START,
    Instrumentation,
)
from app.models import (
    CourseBrief,
    Enrollment,
    LiveAttendee,
    LiveMessage,
    LiveQuiz,
    LiveQuizAnswer,
    LiveRoom,
    UserBrief,
)
from app.schemas import (
    LiveCallIn,
    LiveCallOut,
    LiveMessageCreate,
    LiveMessageOut,
    LiveQuizAnswerIn,
    LiveQuizAnswerOut,
    LiveQuizCreate,
    LiveQuizOut,
    LiveQuizResult,
    LiveRaiseOut,
    LiveRaiseRequest,
    LiveRoomCreate,
    LiveRoomOut,
    SuccessResponse,
)

router = APIRouter(prefix="/live", tags=["直播"])
course_router = APIRouter(prefix="/courses", tags=["直播·课程"])

# ─── 工具 ───
def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _get_room(db: Session, room_id) -> LiveRoom:
    room = db.get(LiveRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="直播房间不存在")
    return room


def _get_course(db: Session, course_id) -> CourseBrief:
    course = db.get(CourseBrief, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return course


def _check_teacher(db: Session, room: LiveRoom, user: UserBrief) -> None:
    """直播控制权限：授课教师或管理员"""
    if user.role == "admin":
        return
    course = db.get(CourseBrief, room.course_id)
    if not course or course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权管理该直播")


def _check_access(db: Session, room: LiveRoom, user: UserBrief) -> CourseBrief:
    """加入权限：授课教师/管理员，或已选课学生"""
    course = db.get(CourseBrief, room.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    if user.role == "admin" or course.teacher_id == user.id:
        return course
    enrolled = (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == user.id,
            Enrollment.course_id == course.id,
            Enrollment.status == "active",
        )
        .first()
    )
    if not enrolled:
        raise HTTPException(status_code=403, detail="未选课，无法加入直播")
    return course


def _online_count(db: Session, room_id) -> int:
    return (
        db.query(func.count(LiveAttendee.id))
        .filter(LiveAttendee.room_id == room_id, LiveAttendee.left_at.is_(None))
        .scalar()
        or 0
    )


def _stream_url(room: LiveRoom) -> str | None:
    """流播放地址：配置了媒体服务器前缀则返回 HLS 地址，否则 mock:// 占位"""
    if room.status != "live":
        return None
    key = room.stream_key or str(room.id)
    if settings.LIVE_STREAM_BASE:
        return f"{settings.LIVE_STREAM_BASE.rstrip('/')}/{key}.m3u8"
    return f"mock://live/{key}"


def _room_out(db: Session, room: LiveRoom) -> LiveRoomOut:
    course = db.get(CourseBrief, room.course_id)
    teacher = db.get(UserBrief, room.teacher_id)
    out = LiveRoomOut(
        id=room.id,
        course_id=room.course_id,
        teacher_id=room.teacher_id,
        title=room.title,
        status=room.status,
        viewer_count=room.viewer_count or 0,
        online_count=_online_count(db, room.id),
        active_call=room.active_call,
        started_at=room.started_at,
        ended_at=room.ended_at,
    )
    out.course_title = course.title if course else None
    out.teacher_name = teacher.name if teacher else None
    out.stream_url = _stream_url(room)
    return out


def _message_out(db: Session, msg: LiveMessage) -> LiveMessageOut:
    u = db.get(UserBrief, msg.user_id) if msg.user_id else None
    out = LiveMessageOut.model_validate(msg)
    out.user_name = u.name if u else None
    out.role = u.role if u else None
    return out


def _broadcast(db: Session, room_id, msg_type: str, content, user_id=None) -> LiveMessage:
    msg = LiveMessage(room_id=room_id, user_id=user_id, msg_type=msg_type, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


# ─── 房间管理 ───

@router.post("/rooms", response_model=LiveRoomOut, status_code=201, summary="创建直播房间（教师）")
def create_room(
    payload: LiveRoomCreate,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course(db, payload.course_id)
    if user.role != "admin" and course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="仅授课教师可创建直播")

    room = LiveRoom(
        course_id=course.id,
        teacher_id=user.id,
        title=payload.title or f"{course.title} 直播",
        status="scheduled",
        stream_key=f"room{str(uuid.uuid4())[:8]}",
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    track = Instrumentation(db, request, str(user.id))
    track.track(EVENT_LIVE_ROOM_CREATE, course_id=str(course.id), properties={"title": room.title})
    return _room_out(db, room)


@router.get("/rooms/{room_id}", response_model=LiveRoomOut, summary="直播房间详情")
def room_detail(
    room_id: uuid.UUID,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room(db, room_id)
    _check_access(db, room, user)
    return _room_out(db, room)


@router.post("/rooms/{room_id}/start", response_model=LiveRoomOut, summary="开播（教师）")
def start_room(
    room_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room(db, room_id)
    _check_teacher(db, room, user)
    if room.status == "ended":
        raise HTTPException(status_code=400, detail="直播已结束，无法重新开播")
    room.status = "live"
    room.started_at = room.started_at or _now()
    db.commit()
    db.refresh(room)
    _broadcast(db, room.id, "system", "🎬 直播已开始", user_id=user.id)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_LIVE_ROOM_START, course_id=str(room.course_id),
        properties={"room_id": str(room.id), "title": room.title},
    )
    return _room_out(db, room)


@router.post("/rooms/{room_id}/end", response_model=LiveRoomOut, summary="结束直播（教师）")
def end_room(
    room_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room(db, room_id)
    _check_teacher(db, room, user)
    room.status = "ended"
    room.ended_at = _now()
    room.active_call = None
    db.commit()
    db.refresh(room)
    _broadcast(db, room.id, "system", "🔚 直播已结束", user_id=user.id)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_LIVE_ROOM_END, course_id=str(room.course_id),
        properties={"room_id": str(room.id), "duration_s": int(
            (room.ended_at - (room.started_at or room.ended_at)).total_seconds()
        )},
    )
    return _room_out(db, room)


@course_router.get("/{course_id}/live/rooms", response_model=list[LiveRoomOut], summary="课程直播列表")
def course_rooms(
    course_id: uuid.UUID,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    rooms = (
        db.query(LiveRoom)
        .filter(LiveRoom.course_id == course_id)
        .order_by(LiveRoom.created_at.desc())
        .all()
    )
    return [_room_out(db, r) for r in rooms]


# ─── 参与 ───

@router.post("/rooms/{room_id}/join", response_model=LiveRoomOut, summary="加入直播")
def join_room(
    room_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room(db, room_id)
    _check_access(db, room, user)
    if room.status == "ended":
        raise HTTPException(status_code=400, detail="直播已结束")

    attendee = (
        db.query(LiveAttendee)
        .filter(LiveAttendee.room_id == room.id, LiveAttendee.user_id == user.id)
        .first()
    )
    if attendee:
        if attendee.left_at is not None:
            attendee.left_at = None          # 重新入会
        db.commit()
    else:
        db.add(LiveAttendee(
            room_id=room.id, user_id=user.id,
            role="teacher" if user.role == "teacher" else "student",
        ))
        room.viewer_count = (room.viewer_count or 0) + 1
        db.commit()

    Instrumentation(db, request, str(user.id)).track(
        EVENT_LIVE_JOIN, course_id=str(room.course_id), properties={"room_id": str(room.id)},
    )
    return _room_out(db, room)


@router.post("/rooms/{room_id}/leave", response_model=SuccessResponse, summary="离开直播")
def leave_room(
    room_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room(db, room_id)
    attendee = (
        db.query(LiveAttendee)
        .filter(LiveAttendee.room_id == room.id, LiveAttendee.user_id == user.id)
        .first()
    )
    if attendee and attendee.left_at is None:
        attendee.left_at = _now()
        attendee.raise_hand = False
        db.commit()
    Instrumentation(db, request, str(user.id)).track(
        EVENT_LIVE_LEAVE, course_id=str(room.course_id), properties={"room_id": str(room.id)},
    )
    return SuccessResponse()


@router.put("/rooms/{room_id}/raise", response_model=SuccessResponse, summary="举手 / 取消举手")
def toggle_raise(
    room_id: uuid.UUID,
    payload: LiveRaiseRequest,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room(db, room_id)
    _check_access(db, room, user)
    attendee = (
        db.query(LiveAttendee)
        .filter(LiveAttendee.room_id == room.id, LiveAttendee.user_id == user.id)
        .first()
    )
    if not attendee or attendee.left_at is not None:
        raise HTTPException(status_code=400, detail="请先加入直播再举手")
    attendee.raise_hand = payload.active
    attendee.raised_at = _now() if payload.active else None
    db.commit()
    Instrumentation(db, request, str(user.id)).track(
        EVENT_LIVE_RAISE_HAND, course_id=str(room.course_id),
        properties={"room_id": str(room.id), "active": payload.active},
    )
    return SuccessResponse()


@router.get("/rooms/{room_id}/raises", response_model=list[LiveRaiseOut], summary="举手队列（教师）")
def list_raises(
    room_id: uuid.UUID,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room(db, room_id)
    _check_teacher(db, room, user)
    rows = (
        db.query(LiveAttendee)
        .filter(
            LiveAttendee.room_id == room.id,
            LiveAttendee.left_at.is_(None),
            LiveAttendee.raise_hand.is_(True),
        )
        .order_by(LiveAttendee.raised_at.asc())
        .all()
    )
    result = []
    for a in rows:
        u = db.get(UserBrief, a.user_id)
        result.append(LiveRaiseOut(
            id=a.id, user_id=a.user_id, name=u.name if u else None, raised_at=a.raised_at,
        ))
    return result


# ─── 互动 ───

@router.post("/rooms/{room_id}/messages", response_model=LiveMessageOut, status_code=201, summary="发送消息（聊天/系统）")
def send_message(
    room_id: uuid.UUID,
    payload: LiveMessageCreate,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room(db, room_id)
    _check_access(db, room, user)
    if room.status == "ended":
        raise HTTPException(status_code=400, detail="直播已结束")
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    msg = LiveMessage(room_id=room.id, user_id=user.id, msg_type=payload.msg_type, content=payload.content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    if payload.msg_type in ("chat", "call", "system"):
        Instrumentation(db, request, str(user.id)).track(
            EVENT_LIVE_CHAT, course_id=str(room.course_id),
            properties={"room_id": str(room.id), "msg_type": payload.msg_type},
        )
    return _message_out(db, msg)


@router.get("/rooms/{room_id}/messages", response_model=list[LiveMessageOut], summary="拉取消息（after_id 增量）")
def list_messages(
    room_id: uuid.UUID,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
    after_id: int = 0,
    limit: int = 100,
):
    room = _get_room(db, room_id)
    _check_access(db, room, user)
    limit = max(1, min(limit, 200))
    msgs = (
        db.query(LiveMessage)
        .filter(LiveMessage.room_id == room.id, LiveMessage.id > after_id)
        .order_by(LiveMessage.id.asc())
        .limit(limit)
        .all()
    )
    return [_message_out(db, m) for m in msgs]


@router.post("/rooms/{room_id}/call", response_model=LiveCallOut, summary="举手点名（教师）")
def random_call(
    room_id: uuid.UUID,
    payload: LiveCallIn,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room(db, room_id)
    _check_teacher(db, room, user)

    target_id = payload.user_id
    target = db.get(UserBrief, target_id) if target_id else None
    if target is None:
        # 随机选一个在线学生
        students = (
            db.query(LiveAttendee)
            .filter(
                LiveAttendee.room_id == room.id,
                LiveAttendee.left_at.is_(None),
                LiveAttendee.role == "student",
            )
            .all()
        )
        if not students:
            raise HTTPException(status_code=400, detail="暂无在线学生可点名")
        attendee = random.choice(students)
        target = db.get(UserBrief, attendee.user_id)
    if not target or target.role not in ("student", "teacher"):
        raise HTTPException(status_code=400, detail="点名对象无效")

    now = _now()
    room.active_call = {"user_id": str(target.id), "name": target.name, "called_at": now.isoformat()}
    db.commit()
    _broadcast(db, room.id, "call", json.dumps(room.active_call, ensure_ascii=False), user_id=user.id)

    if request:
        Instrumentation(db, request, str(user.id)).track(
            EVENT_LIVE_CALL, course_id=str(room.course_id),
            properties={"room_id": str(room.id), "target_id": str(target.id)},
        )
    return LiveCallOut(user_id=target.id, name=target.name or "", called_at=now)


@router.post("/rooms/{room_id}/call/respond", response_model=SuccessResponse, summary="应答点名（学生）")
def respond_call(
    room_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room(db, room_id)
    if not room.active_call:
        raise HTTPException(status_code=400, detail="当前无点名")
    if str(room.active_call.get("user_id")) != str(user.id):
        raise HTTPException(status_code=403, detail="该点名不属于你")
    room.active_call = None
    db.commit()
    _broadcast(db, room.id, "system", f"🙋 {user.name} 已回应点名", user_id=user.id)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_LIVE_CALL_RESPOND, course_id=str(room.course_id),
        properties={"room_id": str(room.id)},
    )
    return SuccessResponse()


# ─── 答题 ───

@router.post("/rooms/{room_id}/quizzes", response_model=LiveQuizOut, status_code=201, summary="发起答题（教师）")
def create_quiz(
    room_id: uuid.UUID,
    payload: LiveQuizCreate,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room(db, room_id)
    _check_teacher(db, room, user)
    if not payload.options:
        raise HTTPException(status_code=400, detail="请至少设置一个选项")
    if payload.answer and payload.answer not in [o.get("key") for o in payload.options]:
        raise HTTPException(status_code=400, detail="正确答案不在选项中")

    quiz = LiveQuiz(
        room_id=room.id, teacher_id=user.id, question=payload.question,
        options=payload.options, answer=payload.answer, status="active",
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    _broadcast(db, room.id, "system", f"📝 答题已发布：{payload.question}", user_id=user.id)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_LIVE_QUIZ_START, course_id=str(room.course_id),
        properties={"room_id": str(room.id), "quiz_id": str(quiz.id)},
    )
    return quiz


@router.post("/rooms/{room_id}/quizzes/{quiz_id}/answer", response_model=LiveQuizAnswerOut, summary="作答（学生）")
def submit_answer(
    room_id: uuid.UUID,
    quiz_id: uuid.UUID,
    payload: LiveQuizAnswerIn,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room(db, room_id)
    _check_access(db, room, user)
    quiz = db.get(LiveQuiz, quiz_id)
    if not quiz or quiz.room_id != room.id:
        raise HTTPException(status_code=404, detail="答题不存在")
    if quiz.status != "active":
        raise HTTPException(status_code=400, detail="答题已关闭")
    if payload.choice not in [o.get("key") for o in (quiz.options or [])]:
        raise HTTPException(status_code=400, detail="选项无效")

    answer = (
        db.query(LiveQuizAnswer)
        .filter(LiveQuizAnswer.quiz_id == quiz.id, LiveQuizAnswer.user_id == user.id)
        .first()
    )
    if answer:
        answer.choice = payload.choice
        answer.submitted_at = _now()
    else:
        answer = LiveQuizAnswer(quiz_id=quiz.id, user_id=user.id, choice=payload.choice)
        db.add(answer)
    db.commit()
    db.refresh(answer)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_LIVE_QUIZ_ANSWER, course_id=str(room.course_id),
        properties={"room_id": str(room.id), "quiz_id": str(quiz.id), "choice": payload.choice},
    )
    return LiveQuizAnswerOut(quiz_id=quiz.id, choice=answer.choice, submitted_at=answer.submitted_at)


@router.post("/rooms/{room_id}/quizzes/{quiz_id}/close", response_model=LiveQuizOut, summary="关闭答题（教师）")
def close_quiz(
    room_id: uuid.UUID,
    quiz_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room(db, room_id)
    _check_teacher(db, room, user)
    quiz = db.get(LiveQuiz, quiz_id)
    if not quiz or quiz.room_id != room.id:
        raise HTTPException(status_code=404, detail="答题不存在")
    quiz.status = "closed"
    quiz.closed_at = _now()
    db.commit()
    db.refresh(quiz)
    Instrumentation(db, request, str(user.id)).track(
        EVENT_LIVE_QUIZ_CLOSE, course_id=str(room.course_id),
        properties={"room_id": str(room.id), "quiz_id": str(quiz.id)},
    )
    return quiz


@router.get("/rooms/{room_id}/quizzes/{quiz_id}/result", response_model=LiveQuizResult, summary="答题统计（教师）")
def quiz_result(
    room_id: uuid.UUID,
    quiz_id: uuid.UUID,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = _get_room(db, room_id)
    _check_teacher(db, room, user)
    quiz = db.get(LiveQuiz, quiz_id)
    if not quiz or quiz.room_id != room.id:
        raise HTTPException(status_code=404, detail="答题不存在")

    answers = (
        db.query(LiveQuizAnswer)
        .filter(LiveQuizAnswer.quiz_id == quiz.id)
        .all()
    )
    result = LiveQuizResult(quiz_id=quiz.id, question=quiz.question, total=len(answers))
    distribution = {}
    for a in answers:
        distribution[a.choice] = distribution.get(a.choice, 0) + 1
    result.distribution = distribution
    if quiz.answer:
        result.correct_count = distribution.get(quiz.answer, 0)
        result.correct_rate = round(result.correct_count / result.total, 4) if result.total else 0.0
    return result