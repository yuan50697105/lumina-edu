# ============================================
# Lumina 墨光 · 课程服务 单元测试
# Schema 校验 / 工具逻辑（无需数据库）
# ============================================
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.schemas import (
    AnnouncementCreate,
    ChapterCreate,
    ChapterUpdate,
    CourseCreate,
    CourseUpdate,
)


class TestCourseSchema:
    def test_course_create_basic(self):
        course = CourseCreate(
            code="CS201", title="高等数学", semester="2026-1",
            credits=4.0, schedule=[{"day": 1, "start": "08:00", "end": "09:40", "room": "教三201"}],
        )
        assert course.code == "CS201"
        assert course.credits == 4.0

    def test_course_create_code_required(self):
        with pytest.raises(Exception):
            CourseCreate(title="无编号课程", semester="2026-1")

    def test_course_create_credits_range(self):
        with pytest.raises(Exception):
            CourseCreate(code="X1", title="超学分", semester="2026-1", credits=25)

    def test_course_create_semester_required(self):
        with pytest.raises(Exception):
            CourseCreate(code="X1", title="无学期")

    def test_course_update_status_pattern(self):
        CourseUpdate(status="published")
        CourseUpdate(status="archived")
        with pytest.raises(Exception):
            CourseUpdate(status="deleted")

    def test_course_update_partial(self):
        u = CourseUpdate(description="仅更新描述")
        assert u.title is None


class TestChapterSchema:
    def test_chapter_create(self):
        c = ChapterCreate(title="第一章", content="# 概述", order_num=1)
        assert c.order_num == 1

    def test_chapter_create_title_required(self):
        with pytest.raises(Exception):
            ChapterCreate(content="no title")

    def test_chapter_update_partial(self):
        u = ChapterUpdate(order_num=3)
        assert u.title is None and u.order_num == 3


class TestAnnouncementSchema:
    def test_announcement_create(self):
        a = AnnouncementCreate(title="调课通知", content="下周三停课", pinned=True)
        assert a.pinned is True

    def test_announcement_create_defaults(self):
        a = AnnouncementCreate(title="普通公告")
        assert a.pinned is False and a.content is None