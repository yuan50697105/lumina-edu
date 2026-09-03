# ============================================
# Lumina 墨光 · 课程路由
# /courses 列表/详情/创建 · 章节 · 选课 · 公告
# ============================================
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.instrumentation import (
    EVENT_ANNOUNCEMENT_CREATED,
    EVENT_CHAPTER_CREATED,
    EVENT_CHAPTER_VIEW,
    EVENT_COURSE_CREATED,
    EVENT_COURSE_DROP,
    EVENT_COURSE_ENROLL,
    EVENT_COURSE_UPDATED,
    EVENT_COURSE_VIEW,
    Instrumentation,
)
from app.models import Announcement, Chapter, Course, Enrollment, StudentGroup, StudentGroupMember, User, UserBrief
from app.schemas import (
    AnnouncementCreate,
    AnnouncementOut,
    ChapterCreate,
    ChapterOut,
    ChapterUpdate,
    CourseCreate,
    CourseOut,
    CourseUpdate,
    EnrollmentOut,
    Pagination,
    StudentGroupCreate,
    StudentGroupMemberOut,
    StudentGroupOut,
    StudentGroupUpdate,
    StudentOut,
    SuccessResponse,
)

router = APIRouter(prefix="/courses", tags=["课程"])


# ─── 工具函数 ───
def _get_course_or_404(db: Session, course_id: uuid.UUID) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return course


def _teacher_brief(db: Session, teacher_id) -> dict:
    teacher = db.get(UserBrief, teacher_id)
    return {"id": str(teacher_id), "name": teacher.name if teacher else None,
            "avatar_url": teacher.avatar_url if teacher else None}


def _course_out(db: Session, course: Course) -> CourseOut:
    teacher = _teacher_brief(db, course.teacher_id)
    return CourseOut(
        id=course.id,
        code=course.code,
        title=course.title,
        description=course.description,
        teacher=teacher,
        department=course.department,
        credits=course.credits,
        semester=course.semester,
        schedule=course.schedule,
        students_count=course.students_count,
        status=course.status,
        created_at=course.created_at,
    )


def _check_course_teacher(db: Session, course: Course, user_id, role) -> None:
    """课程管理权限：授课教师本人或管理员"""
    if role == "admin":
        return
    if course.teacher_id != user_id:
        raise HTTPException(status_code=403, detail="无权操作该课程")


# ─── 课程列表 / 详情 ───
@router.get("", response_model=dict, summary="课程列表")
def list_courses(
    request: Request,
    db: Session = Depends(get_db),
    _user: UserBrief = Depends(get_current_user),
    semester: str | None = None,
    department: str | None = None,
    status_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """课程列表，支持学期 / 院系筛选，分页返回"""
    query = db.query(Course)
    if semester:
        query = query.filter(Course.semester == semester)
    if department:
        query = query.filter(Course.department == department)
    if status_filter:
        query = query.filter(Course.status == status_filter)
    else:
        # 默认只展示已发布课程
        query = query.filter(Course.status == "published")

    total = query.count()
    limit = min(limit, 100)
    courses = query.order_by(Course.created_at.desc()).offset(offset).limit(limit + 1).all()
    has_more = len(courses) > limit
    courses = courses[:limit]

    data = [_course_out(db, c) for c in courses]
    Instrumentation(db, request, str(_user.id)).track(
        EVENT_COURSE_VIEW, course_id=None,
        properties={"semester": semester, "department": department, "offset": offset},
    )
    return {
        "code": 0,
        "data": data,
        "pagination": Pagination(offset=offset, limit=limit, total=total, has_more=has_more),
    }


@router.get("/me/enrolled", response_model=list[EnrollmentOut], summary="我的课程（当前用户）")
def my_courses(
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """当前用户的课程：学生=已选，教师=开设"""
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user.id, Enrollment.status == "active")
        .all()
    )
    result = []
    for e in enrollments:
        course = db.get(Course, e.course_id)
        if course:
            result.append(EnrollmentOut(
                course_id=e.course_id, role=e.role, status=e.status,
                enrolled_at=e.enrolled_at, course=_course_out(db, course),
            ))
    return result


@router.get("/{course_id}", response_model=CourseOut, summary="课程详情")
def get_course(
    course_id: uuid.UUID,
    request: Request,
    _user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course_or_404(db, course_id)
    Instrumentation(db, request, str(_user.id)).track(EVENT_COURSE_VIEW, course_id=str(course_id))
    return _course_out(db, course)


@router.post("", response_model=CourseOut, status_code=201, summary="创建课程（教师）")
def create_course(
    payload: CourseCreate,
    request: Request,
    teacher: UserBrief = Depends(require_role("teacher", "admin")),
    db: Session = Depends(get_db),
):
    if db.query(Course).filter(Course.code == payload.code).first():
        raise HTTPException(status_code=409, detail="课程编号已存在")

    course = Course(**payload.model_dump(), teacher_id=teacher.id, status="draft")
    db.add(course)
    db.commit()
    db.refresh(course)

    # 教师自动加入选课记录（role=teacher），用于"我的课程"查询
    if not db.query(Enrollment).filter_by(user_id=teacher.id, course_id=course.id).first():
        db.add(Enrollment(user_id=teacher.id, course_id=course.id, role="teacher"))
        db.commit()

    Instrumentation(db, request, str(teacher.id)).track(
        EVENT_COURSE_CREATED, course_id=str(course.id), code=course.code
    )
    return _course_out(db, course)


@router.patch("/{course_id}", response_model=CourseOut, summary="更新课程（教师/管理员）")
def update_course(
    course_id: uuid.UUID,
    payload: CourseUpdate,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course_or_404(db, course_id)
    _check_course_teacher(db, course, user.id, user.role)

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(course, key, value)
    db.commit()
    db.refresh(course)

    Instrumentation(db, request, str(user.id)).track(
        EVENT_COURSE_UPDATED, course_id=str(course_id), fields=list(data.keys())
    )
    return _course_out(db, course)


# ─── 章节 ───
@router.get("/{course_id}/chapters", response_model=list[ChapterOut], summary="章节列表")
def list_chapters(
    course_id: uuid.UUID,
    request: Request,
    _user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_course_or_404(db, course_id)
    chapters = (
        db.query(Chapter)
        .filter(Chapter.course_id == course_id)
        .order_by(Chapter.order_num, Chapter.created_at)
        .all()
    )
    Instrumentation(db, request, str(_user.id)).track(
        EVENT_CHAPTER_VIEW, course_id=str(course_id)
    )
    return chapters


@router.post("/{course_id}/chapters", response_model=ChapterOut, status_code=201, summary="新增章节（教师）")
def create_chapter(
    course_id: uuid.UUID,
    payload: ChapterCreate,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course_or_404(db, course_id)
    _check_course_teacher(db, course, user.id, user.role)

    chapter = Chapter(course_id=course_id, **payload.model_dump())
    db.add(chapter)
    db.commit()
    db.refresh(chapter)

    Instrumentation(db, request, str(user.id)).track(
        EVENT_CHAPTER_CREATED, course_id=str(course_id), chapter_id=str(chapter.id)
    )
    return chapter


@router.patch("/{course_id}/chapters/{chapter_id}", response_model=ChapterOut, summary="更新章节（教师）")
def update_chapter(
    course_id: uuid.UUID,
    chapter_id: uuid.UUID,
    payload: ChapterUpdate,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course_or_404(db, course_id)
    _check_course_teacher(db, course, user.id, user.role)

    chapter = db.get(Chapter, chapter_id)
    if not chapter or chapter.course_id != course_id:
        raise HTTPException(status_code=404, detail="章节不存在")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(chapter, key, value)
    db.commit()
    db.refresh(chapter)
    return chapter


@router.delete("/{course_id}/chapters/{chapter_id}", response_model=SuccessResponse, summary="删除章节（教师）")
def delete_chapter(
    course_id: uuid.UUID,
    chapter_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course_or_404(db, course_id)
    _check_course_teacher(db, course, user.id, user.role)

    chapter = db.get(Chapter, chapter_id)
    if not chapter or chapter.course_id != course_id:
        raise HTTPException(status_code=404, detail="章节不存在")

    db.delete(chapter)
    db.commit()
    return SuccessResponse()


# ─── 选课 / 退课 ───
@router.post("/{course_id}/enroll", response_model=EnrollmentOut, summary="选课（学生）")
def enroll(
    course_id: uuid.UUID,
    request: Request,
    student: UserBrief = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    course = _get_course_or_404(db, course_id)
    if course.status != "published":
        raise HTTPException(status_code=400, detail="课程未开放选课")

    existing = (
        db.query(Enrollment)
        .filter_by(user_id=student.id, course_id=course_id)
        .first()
    )
    if existing and existing.status == "active":
        raise HTTPException(status_code=409, detail="已选修该课程")
    if existing:  # dropped/completed → 重新激活
        existing.status = "active"
        db.commit()
        db.refresh(existing)
        enrollment = existing
    else:
        enrollment = Enrollment(user_id=student.id, course_id=course_id, role="student")
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)

    course.students_count += 1
    db.commit()

    Instrumentation(db, request, str(student.id)).track(
        EVENT_COURSE_ENROLL, course_id=str(course_id)
    )
    return EnrollmentOut(
        course_id=course.id,
        role=enrollment.role or "student",
        status=enrollment.status or "active",
        enrolled_at=enrollment.enrolled_at,
        course=_course_out(db, course),
    )


@router.delete("/{course_id}/enroll", response_model=SuccessResponse, summary="退课（学生）")
def drop(
    course_id: uuid.UUID,
    request: Request,
    student: UserBrief = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    course = _get_course_or_404(db, course_id)
    enrollment = (
        db.query(Enrollment)
        .filter_by(user_id=student.id, course_id=course_id, status="active")
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="未选修该课程")

    enrollment.status = "dropped"
    course.students_count = max(0, course.students_count - 1)
    db.commit()

    Instrumentation(db, request, str(student.id)).track(
        EVENT_COURSE_DROP, course_id=str(course_id)
    )
    return SuccessResponse()


@router.get("/{course_id}/students", response_model=list[StudentOut], summary="选课学生列表（教师）")
def list_students(
    course_id: uuid.UUID,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course_or_404(db, course_id)
    _check_course_teacher(db, course, user.id, user.role)

    rows = (
        db.query(Enrollment, UserBrief)
        .join(UserBrief, UserBrief.id == Enrollment.user_id)
        .filter(Enrollment.course_id == course_id, Enrollment.status == "active")
        .order_by(Enrollment.enrolled_at)
        .all()
    )
    Instrumentation(db, request, str(user.id)).track(
        EVENT_COURSE_VIEW, course_id=str(course_id), scope="students"
    )
    return [
        StudentOut(
            id=u.id, name=u.name, avatar_url=u.avatar_url,
            role=e.role, enrolled_at=e.enrolled_at, status=e.status,
        )
        for e, u in rows
    ]


# ─── 公告 ───
@router.get("/{course_id}/announcements", response_model=list[AnnouncementOut], summary="课程公告")
def list_announcements(
    course_id: uuid.UUID,
    request: Request,
    _user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_course_or_404(db, course_id)
    announcements = (
        db.query(Announcement)
        .filter(Announcement.course_id == course_id)
        .order_by(Announcement.pinned.desc(), Announcement.created_at.desc())
        .all()
    )
    return announcements


@router.post("/{course_id}/announcements", response_model=AnnouncementOut, status_code=201, summary="发布公告（教师）")
def create_announcement(
    course_id: uuid.UUID,
    payload: AnnouncementCreate,
    request: Request,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course_or_404(db, course_id)
    _check_course_teacher(db, course, user.id, user.role)

    announcement = Announcement(course_id=course_id, author_id=user.id, **payload.model_dump())
    db.add(announcement)
    db.commit()
    db.refresh(announcement)

    Instrumentation(db, request, str(user.id)).track(
        EVENT_ANNOUNCEMENT_CREATED, course_id=str(course_id), announcement_id=str(announcement.id)
    )
    return announcement


# ═══════════════════════════════════════════════════════════════════
# D-05 · 教学分组（课程级）
# ═══════════════════════════════════════════════════════════════════
@router.get("/{course_id}/student-groups", response_model=list[StudentGroupOut],
            summary="教学分组列表")
def list_student_groups(
    course_id: uuid.UUID,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course_or_404(db, course_id)
    # 教师/管理员可见，选课学生也可见（看分组名单）
    if user.role not in ("admin", "teacher", "student"):
        raise HTTPException(status_code=403, detail="无权查看")
    if user.role == "student":
        enrolled = db.query(Enrollment.id).filter(
            Enrollment.course_id == course_id, Enrollment.user_id == user.id,
            Enrollment.role == "student", Enrollment.status == "active",
        ).first()
        if not enrolled:
            raise HTTPException(status_code=403, detail="未选课")

    groups = db.query(StudentGroup).filter(StudentGroup.course_id == course_id).all()
    out = []
    for g in groups:
        members = (
            db.query(StudentGroupMember, User)
            .join(User, User.id == StudentGroupMember.user_id)
            .filter(StudentGroupMember.group_id == g.id)
            .all()
        )
        teacher = db.get(User, g.teacher_id)
        out.append(StudentGroupOut(
            id=g.id,
            course_id=g.course_id,
            name=g.name,
            description=g.description,
            teacher_id=g.teacher_id,
            teacher_name=teacher.name if teacher else None,
            member_count=len(members),
            members=[
                StudentGroupMemberOut(
                    user_id=m.user_id,
                    name=u.name,
                    student_id=u.student_id,
                    joined_at=m.joined_at,
                )
                for m, u in members
            ],
            created_at=g.created_at,
        ))
    return out


@router.post("/{course_id}/student-groups", response_model=StudentGroupOut, status_code=201,
             summary="创建教学分组（教师）")
def create_student_group(
    course_id: uuid.UUID,
    payload: StudentGroupCreate,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course_or_404(db, course_id)
    _check_course_teacher(db, course, user.id, user.role)

    g = StudentGroup(
        course_id=course_id,
        teacher_id=user.id,
        name=payload.name,
        description=payload.description,
    )
    db.add(g)
    db.flush()

    # 加成员（需为选课学生）
    if payload.member_ids:
        _add_group_members(db, g.id, course_id, payload.member_ids)

    db.commit()
    db.refresh(g)

    members = (
        db.query(StudentGroupMember, User)
        .join(User, User.id == StudentGroupMember.user_id)
        .filter(StudentGroupMember.group_id == g.id)
        .all()
    )
    teacher = db.get(User, g.teacher_id)
    return StudentGroupOut(
        id=g.id, course_id=g.course_id, name=g.name, description=g.description,
        teacher_id=g.teacher_id, teacher_name=teacher.name if teacher else None,
        member_count=len(members),
        members=[
            StudentGroupMemberOut(user_id=m.user_id, name=u.name,
                                  student_id=u.student_id, joined_at=m.joined_at)
            for m, u in members
        ],
        created_at=g.created_at,
    )


@router.patch("/{course_id}/student-groups/{group_id}", response_model=StudentGroupOut,
              summary="更新教学分组")
def update_student_group(
    course_id: uuid.UUID,
    group_id: uuid.UUID,
    payload: StudentGroupUpdate,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course_or_404(db, course_id)
    _check_course_teacher(db, course, user.id, user.role)

    g = db.get(StudentGroup, group_id)
    if not g or str(g.course_id) != str(course_id):
        raise HTTPException(status_code=404, detail="分组不存在")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(g, field, value)
    db.commit()
    db.refresh(g)

    members = (
        db.query(StudentGroupMember, User)
        .join(User, User.id == StudentGroupMember.user_id)
        .filter(StudentGroupMember.group_id == g.id)
        .all()
    )
    teacher = db.get(User, g.teacher_id)
    return StudentGroupOut(
        id=g.id, course_id=g.course_id, name=g.name, description=g.description,
        teacher_id=g.teacher_id, teacher_name=teacher.name if teacher else None,
        member_count=len(members),
        members=[
            StudentGroupMemberOut(user_id=m.user_id, name=u.name,
                                  student_id=u.student_id, joined_at=m.joined_at)
            for m, u in members
        ],
        created_at=g.created_at,
    )


@router.delete("/{course_id}/student-groups/{group_id}", response_model=SuccessResponse,
               summary="删除教学分组")
def delete_student_group(
    course_id: uuid.UUID,
    group_id: uuid.UUID,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course_or_404(db, course_id)
    _check_course_teacher(db, course, user.id, user.role)

    g = db.get(StudentGroup, group_id)
    if not g or str(g.course_id) != str(course_id):
        raise HTTPException(status_code=404, detail="分组不存在")
    db.delete(g)
    db.commit()
    return SuccessResponse()


@router.post("/{course_id}/student-groups/{group_id}/members",
             response_model=list[StudentGroupMemberOut], status_code=201,
             summary="添加组成员")
def add_group_members(
    course_id: uuid.UUID,
    group_id: uuid.UUID,
    user_ids: list[uuid.UUID],
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course_or_404(db, course_id)
    _check_course_teacher(db, course, user.id, user.role)

    g = db.get(StudentGroup, group_id)
    if not g or str(g.course_id) != str(course_id):
        raise HTTPException(status_code=404, detail="分组不存在")

    added = _add_group_members(db, g.id, course_id, user_ids)
    db.commit()
    return [
        StudentGroupMemberOut(
            user_id=m.user_id,
            name=u.name,
            student_id=u.student_id,
            joined_at=m.joined_at,
        )
        for m, u in added
    ]


@router.delete("/{course_id}/student-groups/{group_id}/members/{user_id}",
               response_model=SuccessResponse, summary="移除组成员")
def remove_group_member(
    course_id: uuid.UUID,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    user: UserBrief = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = _get_course_or_404(db, course_id)
    _check_course_teacher(db, course, user.id, user.role)

    g = db.get(StudentGroup, group_id)
    if not g or str(g.course_id) != str(course_id):
        raise HTTPException(status_code=404, detail="分组不存在")

    m = db.query(StudentGroupMember).filter(
        StudentGroupMember.group_id == g.id,
        StudentGroupMember.user_id == user_id,
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail="成员不在该分组")
    db.delete(m)
    db.commit()
    return SuccessResponse()


def _add_group_members(db: Session, group_id, course_id, user_ids):
    """添加组成员，校验必须是选课学生；返回 [(member, user), ...]"""
    added = []
    for uid in user_ids:
        enrolled = db.query(Enrollment.id).filter(
            Enrollment.course_id == course_id,
            Enrollment.user_id == uid,
            Enrollment.role == "student",
            Enrollment.status == "active",
        ).first()
        if not enrolled:
            raise HTTPException(status_code=400, detail=f"用户 {uid} 未选该课程")
        # 幂等：已存在则跳过
        existing = db.query(StudentGroupMember).filter(
            StudentGroupMember.group_id == group_id,
            StudentGroupMember.user_id == uid,
        ).first()
        if existing:
            continue
        m = StudentGroupMember(group_id=group_id, user_id=uid)
        db.add(m)
        db.flush()
        u = db.get(User, uid)
        added.append((m, u))
    return added
