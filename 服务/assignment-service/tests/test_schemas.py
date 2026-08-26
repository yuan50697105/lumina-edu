# ============================================
# Lumina 墨光 · 作业服务 单元测试
# Schema 校验 / 分数字母映射（无需数据库）
# ============================================
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta, timezone

from app.schemas import AssignmentCreate, AssignmentUpdate, GradeCreate
from app.routers.assignments import _is_late, _letter


class TestAssignmentSchema:
    def test_create_basic(self):
        a = AssignmentCreate(
            title="第四章习题", description="P120-P125",
            due_at=datetime.now(timezone.utc), max_score=100,
            ai_grading=True,
            rubric=[{"criteria": "解题过程完整", "weight": 0.4}, {"criteria": "答案正确", "weight": 0.6}],
        )
        assert a.max_score == 100 and a.ai_grading is True
        assert len(a.rubric) == 2

    def test_title_required(self):
        with pytest.raises(Exception):
            AssignmentCreate()

    def test_max_score_range(self):
        with pytest.raises(Exception):
            AssignmentCreate(title="超限", max_score=0)
        with pytest.raises(Exception):
            AssignmentCreate(title="超限", max_score=250)

    def test_update_status_pattern(self):
        for ok in ["draft", "published", "closed"]:
            AssignmentUpdate(status=ok)
        with pytest.raises(Exception):
            AssignmentUpdate(status="deleted")


class TestGradeSchema:
    def test_grade_scores(self):
        g = GradeCreate(total_score=88.5, feedback="很好", grade_letter="B")
        assert float(g.total_score) == 88.5

    def test_grade_letter_pattern(self):
        with pytest.raises(Exception):
            GradeCreate(total_score=10, grade_letter="X")


class TestGradeLogic:
    """迟交判定 + 分数字母映射"""

    def test_late_judgement(self):
        due = datetime(2026, 9, 1, 23, 59, tzinfo=timezone.utc)
        before = due - timedelta(hours=1)
        after = due + timedelta(hours=1)
        assert _is_late(due, before) is False
        assert _is_late(due, after) is True

    def test_late_no_due_never_late(self):
        assert _is_late(None, datetime.now(timezone.utc)) is False

    def test_letter_mapping(self):
        assert _letter(95, 100) == "A"
        assert _letter(85, 100) == "B"
        assert _letter(75, 100) == "C"
        assert _letter(65, 100) == "D"
        assert _letter(50, 100) == "F"
        assert _letter(9, 10) == "A"