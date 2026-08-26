# ============================================
# Lumina 墨光 · 成绩服务 单元测试
# GPA/字母映射 / Schema 校验（无需数据库）
# ============================================
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.routers.grades import gpa_from_score, letter_from_score
from app.schemas import GradeRecordCreate, GradeStats


class TestGpaMapping:
    def test_excellent(self):
        assert float(gpa_from_score(95)) == 4.0
        assert float(gpa_from_score(90)) == 4.0

    def test_good(self):
        assert float(gpa_from_score(88)) == 3.7
        assert float(gpa_from_score(83)) == 3.3

    def test_mid(self):
        assert float(gpa_from_score(79)) == 3.0
        assert float(gpa_from_score(76)) == 2.7
        assert float(gpa_from_score(73)) == 2.3

    def test_pass_band(self):
        assert float(gpa_from_score(69)) == 2.0
        assert float(gpa_from_score(65)) == 1.5
        assert float(gpa_from_score(60)) == 1.0

    def test_fail(self):
        assert float(gpa_from_score(59)) == 0.0
        assert float(gpa_from_score(0)) == 0.0


class TestLetterMapping:
    def test_full_range(self):
        assert letter_from_score(92) == "A"
        assert letter_from_score(85) == "B"
        assert letter_from_score(75) == "C"
        assert letter_from_score(62) == "D"
        assert letter_from_score(58) == "F"
        assert letter_from_score(100) == "A"
        assert letter_from_score(0) == "F"


class TestGradeSchema:
    def test_record_create(self):
        r = GradeRecordCreate(student_id="00000000-0000-0000-0000-000000000001",
                              final_score=88.5, semester="2026-1")
        assert float(r.final_score) == 88.5
        assert r.gpa_point is None

    def test_score_range(self):
        with pytest.raises(Exception):
            GradeRecordCreate(student_id="00000000-0000-0000-0000-000000000001",
                              final_score=101, semester="2026-1")
        with pytest.raises(Exception):
            GradeRecordCreate(student_id="00000000-0000-0000-0000-000000000001",
                              final_score=-1, semester="2026-1")

    def test_gpa_custom_override(self):
        r = GradeRecordCreate(student_id="00000000-0000-0000-0000-000000000001",
                              final_score=95, semester="2026-1", gpa_point=3.5)
        assert float(r.gpa_point) == 3.5

    def test_stats_defaults(self):
        s = GradeStats()
        assert s.count == 0
        assert s.average is None