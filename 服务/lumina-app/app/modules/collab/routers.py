# ============================================
# Lumina 墨光 · 协作工具路由（V1.1 · D-02 · WBS-P 阶段 D）
# 小组 / 成员 / 项目 / 看板（列·卡片）/ 共享文件 / 组内讨论
# 挂在课程（course）→ 小组（group）树；文件 V1.1 简化存本地 uploads
# ============================================
import datetime
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.instrumentation import (
    EVENT_COLLAB_CARD_MOVE,
    EVENT_COLLAB_FILE_DOWNLOAD,
    EVENT_COLLAB_FILE_UPLOAD,
    EVENT_COLLAB_GROUP_CREATE,
    EVENT_COLLAB_GROUP_JOIN,
    EVENT_COLLAB_GROUP_LEAVE,
    EVENT_COLLAB_PROJECT_CREATE,
    EVENT_COLLAB_REPLY_CREATE,
    EVENT_COLLAB_TOPIC_CREATE,
    Instrumentation,
)
from app.models import (
    CollabProject,
    CourseBrief,
    DiscussionReply,
    DiscussionTopic,
    Enrollment,
    GroupMember,
    KanbanCard,
    KanbanColumn,
    ProjectGroup,
    SharedFile,
    UserBrief,
)
from app.schemas import (
    BoardOut,
    CardCreate,
    CardOut,
    CardUpdate,
    ColumnCreate,
    ColumnOut,
    ColumnUpdate,
    FileOut,
    GroupCreate,
    GroupMemberOut,
    GroupOut,
    GroupUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    ReplyIn,
    ReplyOut,
    SuccessResponse,
    TopicCreate,
    TopicOut,
)

router = APIRouter(prefix="", tags=["协作"])

UPLOAD_ROOT = Path(__file__).resolve().parents[3] / "uploads" / "collab"


# ─── 工具 ───
def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _get_course(db: Session, course_id) -> CourseBrief:
    course = db.get(CourseBrief, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return course


def _get_group(db: Session, group_id) -> ProjectGroup:
    group = db.get(ProjectGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="小组不存在")
    return group


def _get_project(db: Session, project_id) -> CollabProject:
    project = db.get(CollabProject, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def _is_teacher(db: Session, course_id, user: UserBrief) -> bool:
    if user.role == "admin":
        return True
    course = db.get(CourseBrief, course_id)
    return bool(course and course.teacher_id == user.id)


def _enrolled(db: Session, user_id, course_id) -> bool:
    return bool(
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == user_id,
            Enrollment.course_id == course_id,
            Enrollment.status == "active",
        )
        .first()
    )


def _is_member(db: Session, group_id, user_id) -> bool:
    return bool(
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        .first()
    )


def _check_view(db: Session, group: ProjectGroup, user: UserBrief) -> None:
    """查看权限：授课教师/管理员，或小组成员"""
    if _is_teacher(db, group.course_id, user) or _is_member(db, group.id, user.id):
        return
    raise HTTPException(status_code=403, detail="不是小组成员，无权访问")


def _check_manage(db: Session, group: ProjectGroup, user: UserBrief) -> None:
    """管理权限：授课教师/管理员，或组长"""
    if _is_teacher(db, group.course_id, user) or group.leader_id == user.id:
        return
    raise HTTPException(status_code=403, detail="只有组长或授课教师可管理")


def _track(db: Session, request: Request, user: UserBrief, event: str, **props) -> None:
    Instrumentation(db, request, str(user.id)).track(event, **props)


def _member_out(db: Session, m: GroupMember) -> GroupMemberOut:
    u = db.get(UserBrief, m.user_id)
    out = GroupMemberOut.model_validate(m)
    out.name = u.name if u else "已注销"
    return out


def _group_out(db: Session, g: ProjectGroup, user: UserBrief) -> GroupOut:
    course = db.get(CourseBrief, g.course_id)
    leader = db.get(UserBrief, g.leader_id)
    members = (
        db.query(GroupMember).filter(GroupMember.group_id == g.id).order_by(GroupMember.joined_at).all()
    )
    project_count = (
        db.query(func.count(CollabProject.id)).filter(CollabProject.group_id == g.id).scalar() or 0
    )
    out = GroupOut(
        id=g.id,
        course_id=g.course_id,
        name=g.name,
        description=g.description,
        leader_id=g.leader_id,
        member_count=len(members),
        project_count=project_count,
        created_at=g.created_at,
        members=[_member_out(db, m) for m in members],
        is_member=_is_member(db, g.id, user.id),
    )
    out.course_title = course.title if course else None
    out.leader_name = leader.name if leader else None
    return out


def _card_out(db: Session, c: KanbanCard) -> CardOut:
    out = CardOut.model_validate(c)
    if c.assignee_id:
        u = db.get(UserBrief, c.assignee_id)
        out.assignee_name = u.name if u else None
    return out


def _column_out(db: Session, col: KanbanColumn, cards: list[KanbanCard] | None = None) -> ColumnOut:
    if cards is None:
        cards = (
            db.query(KanbanCard)
            .filter(KanbanCard.column_id == col.id)
            .order_by(KanbanCard.order_num, KanbanCard.id)
            .all()
        )
    out = ColumnOut.model_validate(col)
    out.cards = [_card_out(db, c) for c in cards]
    return out


def _board_out(db: Session, project: CollabProject) -> BoardOut:
    cols = (
        db.query(KanbanColumn)
        .filter(KanbanColumn.project_id == project.id)
        .order_by(KanbanColumn.order_num, KanbanColumn.id)
        .all()
    )
    return BoardOut(project_id=project.id, columns=[_column_out(db, col) for col in cols])


def _topic_out(db: Session, t: DiscussionTopic) -> TopicOut:
    author = db.get(UserBrief, t.author_id)
    replies = (
        db.query(DiscussionReply)
        .filter(DiscussionReply.topic_id == t.id)
        .order_by(DiscussionReply.created_at)
        .all()
    )
    out = TopicOut(
        id=t.id,
        group_id=t.group_id,
        author_id=t.author_id,
        title=t.title,
        content=t.content,
        reply_count=len(replies),
        created_at=t.created_at,
        replies=[],
    )
    out.author_name = author.name if author else None
    out.replies = [_reply_out(db, r) for r in replies]
    return out


def _reply_out(db: Session, r: DiscussionReply) -> ReplyOut:
    author = db.get(UserBrief, r.author_id)
    out = ReplyOut.model_validate(r)
    out.author_name = author.name if author else None
    return out


def _next_order(db: Session, model, **filters) -> int:
    mx = db.query(func.max(model.order_num)).filter_by(**filters).scalar()
    return (mx if mx is not None else -1) + 1


# ─── 小组 ───
@router.get("/groups/me", response_model=list[GroupOut])
def my_groups(
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """我的小组（学生视角，含课程名）"""
    rows = (
        db.query(ProjectGroup)
        .join(GroupMember, GroupMember.group_id == ProjectGroup.id)
        .filter(GroupMember.user_id == user.id)
        .order_by(ProjectGroup.created_at.desc())
        .all()
    )
    return [_group_out(db, g, user) for g in rows]


@router.get("/courses/{course_id}/groups", response_model=list[GroupOut])
def course_groups(
    course_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """课程的协作小组列表（选课学生/教师可见）"""
    course = _get_course(db, course_id)
    if not (_is_teacher(db, course_id, user) or _enrolled(db, user.id, course_id)):
        raise HTTPException(status_code=403, detail="未选课，无法查看小组")
    groups = (
        db.query(ProjectGroup).filter(ProjectGroup.course_id == course_id).order_by(ProjectGroup.created_at).all()
    )
    return [_group_out(db, g, user) for g in groups]


@router.post("/courses/{course_id}/groups", response_model=GroupOut, status_code=201)
def create_group(
    course_id: uuid.UUID,
    payload: GroupCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """创建小组（授课教师/管理员）"""
    _get_course(db, course_id)
    if not _is_teacher(db, course_id, user):
        raise HTTPException(status_code=403, detail="只有授课教师可创建小组")
    leader_id = payload.leader_id or user.id
    if payload.leader_id and not db.get(UserBrief, payload.leader_id):
        raise HTTPException(status_code=400, detail="组长用户不存在")
    g = ProjectGroup(
        course_id=course_id,
        name=payload.name,
        description=payload.description,
        leader_id=leader_id,
        created_by=user.id,
    )
    db.add(g)
    db.flush()
    db.add(GroupMember(group_id=g.id, user_id=leader_id))  # 组长默认入组
    db.commit()
    db.refresh(g)
    _track(db, request, user, EVENT_COLLAB_GROUP_CREATE, course_id=str(course_id),
           properties={"group_id": str(g.id), "group_name": g.name})
    return _group_out(db, g, user)


@router.get("/groups/{group_id}", response_model=GroupOut)
def group_detail(
    group_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """小组详情（成员 / 项目数）"""
    g = _get_group(db, group_id)
    _check_view(db, g, user)
    return _group_out(db, g, user)


@router.patch("/groups/{group_id}", response_model=GroupOut)
def update_group(
    group_id: uuid.UUID,
    payload: GroupUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """更新小组（组长/授课教师/管理员）"""
    g = _get_group(db, group_id)
    _check_manage(db, g, user)
    if payload.name is not None:
        g.name = payload.name
    if payload.description is not None:
        g.description = payload.description
    if payload.leader_id is not None:
        if not db.get(UserBrief, payload.leader_id):
            raise HTTPException(status_code=400, detail="组长用户不存在")
        g.leader_id = payload.leader_id
        if not _is_member(db, g.id, payload.leader_id):
            db.add(GroupMember(group_id=g.id, user_id=payload.leader_id))
    db.commit()
    db.refresh(g)
    return _group_out(db, g, user)


@router.delete("/groups/{group_id}", response_model=SuccessResponse)
def delete_group(
    group_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """删除小组（授课教师/管理员）"""
    g = _get_group(db, group_id)
    if not _is_teacher(db, g.course_id, user):
        raise HTTPException(status_code=403, detail="只有授课教师可删除小组")
    db.delete(g)
    db.commit()
    return SuccessResponse(message="小组已删除")


@router.post("/groups/{group_id}/members", response_model=GroupOut, status_code=201)
def join_group(
    group_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """加入小组（已选课学生）"""
    g = _get_group(db, group_id)
    if not _is_teacher(db, g.course_id, user) and not _enrolled(db, user.id, g.course_id):
        raise HTTPException(status_code=403, detail="未选课，无法加入小组")
    if _is_member(db, g.id, user.id):
        raise HTTPException(status_code=409, detail="已在小组中")
    db.add(GroupMember(group_id=g.id, user_id=user.id))
    db.commit()
    _track(db, request, user, EVENT_COLLAB_GROUP_JOIN, course_id=str(g.course_id),
           properties={"group_id": str(g.id), "user_id": str(user.id)})
    return _group_out(db, g, user)


@router.delete("/groups/{group_id}/members/{user_id}", response_model=SuccessResponse)
def leave_group(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """移出小组成员（组长/授课教师；可移自己）"""
    g = _get_group(db, group_id)
    if user_id != user.id:
        _check_manage(db, g, user)
    if g.leader_id == user_id:
        raise HTTPException(status_code=409, detail="请先变更组长再移出")
    row = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="该用户不是小组成员")
    db.delete(row)
    db.commit()
    _track(db, request, user, EVENT_COLLAB_GROUP_LEAVE, course_id=str(g.course_id),
           properties={"group_id": str(g.id), "user_id": str(user_id)})
    return SuccessResponse(message="已移出小组")


# ─── 项目 / 看板 ───
@router.get("/groups/{group_id}/projects", response_model=list[ProjectOut])
def group_projects(
    group_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """小组项目列表"""
    g = _get_group(db, group_id)
    _check_view(db, g, user)
    return (
        db.query(CollabProject)
        .filter(CollabProject.group_id == group_id)
        .order_by(CollabProject.created_at)
        .all()
    )


@router.post("/groups/{group_id}/projects", response_model=ProjectOut, status_code=201)
def create_project(
    group_id: uuid.UUID,
    payload: ProjectCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """创建项目（组成员/授课教师）"""
    g = _get_group(db, group_id)
    _check_view(db, g, user)
    if not _is_teacher(db, g.course_id, user) and not _is_member(db, g.id, user.id):
        raise HTTPException(status_code=403, detail="不是小组成员，无法创建项目")
    p = CollabProject(
        group_id=group_id,
        course_id=g.course_id,
        title=payload.title,
        description=payload.description,
        deadline=payload.deadline,
        created_by=user.id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    _track(db, request, user, EVENT_COLLAB_PROJECT_CREATE, course_id=str(g.course_id),
           properties={"project_id": str(p.id), "group_id": str(group_id), "title": p.title})
    return p


@router.get("/projects/{project_id}", response_model=ProjectOut)
def project_detail(
    project_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    p = _get_project(db, project_id)
    _check_view(db, _get_group(db, p.group_id), user)
    return p


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """更新项目（组成员/授课教师）"""
    p = _get_project(db, project_id)
    _check_view(db, _get_group(db, p.group_id), user)
    for field in ("title", "description", "status", "deadline"):
        v = getattr(payload, field)
        if v is not None:
            setattr(p, field, v)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/projects/{project_id}", response_model=SuccessResponse)
def delete_project(
    project_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    g = _get_group(db, _get_project(db, project_id).group_id)
    _check_manage(db, g, user)
    db.delete(_get_project(db, project_id))
    db.commit()
    return SuccessResponse(message="项目已删除")


@router.get("/projects/{project_id}/board", response_model=BoardOut)
def project_board(
    project_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """项目看板（列 + 卡片聚合）"""
    p = _get_project(db, project_id)
    _check_view(db, _get_group(db, p.group_id), user)
    return _board_out(db, p)


@router.post("/projects/{project_id}/columns", response_model=ColumnOut, status_code=201)
def create_column(
    project_id: uuid.UUID,
    payload: ColumnCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """新建看板列"""
    p = _get_project(db, project_id)
    _check_view(db, _get_group(db, p.group_id), user)
    col = KanbanColumn(
        project_id=project_id,
        title=payload.title,
        order_num=_next_order(db, KanbanColumn, project_id=project_id),
    )
    db.add(col)
    db.commit()
    db.refresh(col)
    return _column_out(db, col, [])


@router.patch("/columns/{column_id}", response_model=ColumnOut)
def update_column(
    column_id: uuid.UUID,
    payload: ColumnUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    col = db.get(KanbanColumn, column_id)
    if not col:
        raise HTTPException(status_code=404, detail="看板列不存在")
    _check_view(db, _get_group(db, _get_project(db, col.project_id).group_id), user)
    if payload.title is not None:
        col.title = payload.title
    if payload.order_num is not None:
        col.order_num = payload.order_num
    db.commit()
    db.refresh(col)
    return _column_out(db, col)


@router.delete("/columns/{column_id}", response_model=SuccessResponse)
def delete_column(
    column_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    col = db.get(KanbanColumn, column_id)
    if not col:
        raise HTTPException(status_code=404, detail="看板列不存在")
    _check_view(db, _get_group(db, _get_project(db, col.project_id).group_id), user)
    db.delete(col)
    db.commit()
    return SuccessResponse(message="看板列已删除")


@router.post("/columns/{column_id}/cards", response_model=CardOut, status_code=201)
def create_card(
    column_id: uuid.UUID,
    payload: CardCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """新建卡片（任务卡）"""
    col = db.get(KanbanColumn, column_id)
    if not col:
        raise HTTPException(status_code=404, detail="看板列不存在")
    _check_view(db, _get_group(db, _get_project(db, col.project_id).group_id), user)
    card = KanbanCard(
        column_id=column_id,
        title=payload.title,
        description=payload.description,
        assignee_id=payload.assignee_id,
        due_date=payload.due_date,
        order_num=_next_order(db, KanbanCard, column_id=column_id),
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return _card_out(db, card)


@router.patch("/cards/{card_id}", response_model=CardOut)
def update_card(
    card_id: uuid.UUID,
    payload: CardUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """更新卡片（含拖拽换列：column_id + order_num）"""
    card = db.get(KanbanCard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    col = db.get(KanbanColumn, card.column_id)
    if not col:
        raise HTTPException(status_code=500, detail="卡片所属列异常")
    g = _get_group(db, _get_project(db, col.project_id).group_id)
    _check_view(db, g, user)

    moved = False
    if payload.column_id is not None and payload.column_id != card.column_id:
        new_col = db.get(KanbanColumn, payload.column_id)
        if not new_col or new_col.project_id != col.project_id:
            raise HTTPException(status_code=400, detail="新列不属于同一项目")
        card.column_id = payload.column_id
        card.order_num = _next_order(db, KanbanCard, column_id=payload.column_id)
        moved = True
    if payload.order_num is not None and not moved:
        card.order_num = payload.order_num
    if payload.title is not None:
        card.title = payload.title
    if payload.description is not None:
        card.description = payload.description
    if payload.assignee_id is not None:
        card.assignee_id = payload.assignee_id
    if payload.due_date is not None:
        card.due_date = payload.due_date
    db.commit()
    db.refresh(card)
    if moved:
        _track(db, request, user, EVENT_COLLAB_CARD_MOVE, course_id=str(g.course_id),
               properties={"card_id": str(card.id), "column_id": str(card.column_id)})
    return _card_out(db, card)


@router.delete("/cards/{card_id}", response_model=SuccessResponse)
def delete_card(
    card_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    card = db.get(KanbanCard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    col = db.get(KanbanColumn, card.column_id)
    _check_view(db, _get_group(db, _get_project(db, col.project_id).group_id), user)
    db.delete(card)
    db.commit()
    return SuccessResponse(message="卡片已删除")


# ─── 共享文件 ───
@router.get("/groups/{group_id}/files", response_model=list[FileOut])
def group_files(
    group_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """小组共享文件列表"""
    g = _get_group(db, group_id)
    _check_view(db, g, user)
    files = db.query(SharedFile).filter(SharedFile.group_id == group_id).order_by(SharedFile.created_at.desc()).all()
    out = []
    for f in files:
        o = FileOut.model_validate(f)
        u = db.get(UserBrief, f.uploader_id)
        o.uploader_name = u.name if u else None
        out.append(o)
    return out


@router.post("/groups/{group_id}/files", response_model=FileOut, status_code=201)
async def upload_file(
    group_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """上传共享文件（组成员/授课教师；存本地 uploads）"""
    g = _get_group(db, group_id)
    _check_view(db, g, user)
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    content = await file.read()
    safe = "".join(c for c in file.filename if c not in '/\\:*?"<>|')
    key = f"{uuid.uuid4().hex}_{safe}"
    dest_dir = UPLOAD_ROOT / str(group_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / key
    dest.write_bytes(content)

    rec = SharedFile(
        group_id=group_id,
        course_id=g.course_id,
        uploader_id=user.id,
        filename=file.filename,
        stored_path=str(dest),
        size=len(content),
        content_type=file.content_type or "application/octet-stream",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    _track(db, request, user, EVENT_COLLAB_FILE_UPLOAD, course_id=str(g.course_id),
           properties={"file_id": str(rec.id), "filename": rec.filename, "size": rec.size})
    o = FileOut.model_validate(rec)
    o.uploader_name = user.name
    return o


@router.get("/files/{file_id}/download", response_class=FileResponse)
def download_file(
    file_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """下载共享文件"""
    f = db.get(SharedFile, file_id)
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    g = _get_group(db, f.group_id)
    _check_view(db, g, user)
    _track(db, request, user, EVENT_COLLAB_FILE_DOWNLOAD, course_id=str(g.course_id),
           properties={"file_id": str(f.id), "filename": f.filename})
    if f.stored_path and Path(f.stored_path).exists():
        return FileResponse(f.stored_path, filename=f.filename, media_type=f.content_type)
    # mock 占位（本地文件缺失时仍可返回文本）
    return Response(content="Lumina 共享文件（占位）", media_type="text/plain; charset=utf-8")


# ─── 组内讨论 ───
@router.get("/groups/{group_id}/topics", response_model=list[TopicOut])
def group_topics(
    group_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """小组讨论主题列表"""
    g = _get_group(db, group_id)
    _check_view(db, g, user)
    topics = (
        db.query(DiscussionTopic)
        .filter(DiscussionTopic.group_id == group_id)
        .order_by(DiscussionTopic.created_at.desc())
        .all()
    )
    return [_topic_out(db, t) for t in topics]


@router.post("/groups/{group_id}/topics", response_model=TopicOut, status_code=201)
def create_topic(
    group_id: uuid.UUID,
    payload: TopicCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """发表讨论主题"""
    g = _get_group(db, group_id)
    _check_view(db, g, user)
    t = DiscussionTopic(group_id=group_id, author_id=user.id, title=payload.title, content=payload.content)
    db.add(t)
    db.commit()
    db.refresh(t)
    _track(db, request, user, EVENT_COLLAB_TOPIC_CREATE, course_id=str(g.course_id),
           properties={"topic_id": str(t.id), "group_id": str(group_id)})
    return _topic_out(db, t)


@router.get("/topics/{topic_id}", response_model=TopicOut)
def topic_detail(
    topic_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """讨论主题（含回复）"""
    t = db.get(DiscussionTopic, topic_id)
    if not t:
        raise HTTPException(status_code=404, detail="讨论主题不存在")
    _check_view(db, _get_group(db, t.group_id), user)
    return _topic_out(db, t)


@router.post("/topics/{topic_id}/replies", response_model=ReplyOut, status_code=201)
def create_reply(
    topic_id: uuid.UUID,
    payload: ReplyIn,
    request: Request,
    db: Session = Depends(get_db),
    user: UserBrief = Depends(get_current_user),
):
    """回复讨论"""
    t = db.get(DiscussionTopic, topic_id)
    if not t:
        raise HTTPException(status_code=404, detail="讨论主题不存在")
    _check_view(db, _get_group(db, t.group_id), user)
    r = DiscussionReply(topic_id=topic_id, author_id=user.id, content=payload.content)
    db.add(r)
    db.commit()
    db.refresh(r)
    _track(db, request, user, EVENT_COLLAB_REPLY_CREATE,
           properties={"topic_id": str(topic_id), "group_id": str(t.group_id)})
    return _reply_out(db, r)