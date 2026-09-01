# ============================================
# Lumina 墨光 · 题库与考试模块单元测试（V1.1 · D-04）
# 表结构 / schema 校验 / 自动评分逻辑 / 智能组卷算法 / OpenAPI 注册
# 纯内存断言，不连数据库
# ============================================
import uuid
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from app.database import Base
from app.instrumentation import (
    EVENT_EXAM_ATTEMPT_START,
    EVENT_EXAM_ATTEMPT_SUBMIT,
    EVENT_EXAM_MANUAL_GRADE,
    EVENT_EXAM_PAPER_CREATE,
    EVENT_EXAM_PAPER_GENERATE,
    EVENT_EXAM_PAPER_PUBLISH,
    EVENT_EXAM_QUESTION_CREATE,
)
from app.main import app
from app.models import ExamAttempt, ExamPaper, ExamPaperQuestion, ExamQuestion
from app.modules.exam.scoring import is_objective, judge_answer, select_questions
from app.schemas import (
    AutoGenerateIn,
    QuestionCreate,
    QuestionOut,
    PaperCreate,
    PaperOut,
    StartAttemptOut,
)


@pytest.fixture(scope="module")
def tables():
    return set(Base.metadata.tables.keys())


class TestTableDefinitions:
    """exam 表定义测试"""

    def test_question_table_exists(self, tables):
        assert "exam_questions" in tables
        assert "exam_papers" in tables
        assert "exam_paper_questions" in tables
        assert "exam_attempts" in tables

    def test_question_columns(self):
        mapper = inspect(ExamQuestion)
        cols = {c.key for c in mapper.columns}
        required = {"id", "course_id", "qtype", "title", "score", "difficulty", "created_by", "created_at"}
        assert required.issubset(cols)
        # 客观题选项/答案可空（主观题）
        for key in ("options", "answer", "tags", "chapter_id"):
            assert mapper.columns[key].nullable, f"{key} 应可空"

    def test_paper_columns(self):
        mapper = inspect(ExamPaper)
        cols = {c.key for c in mapper.columns}
        assert {"title", "duration_minutes", "total_score", "status", "created_by"}.issubset(cols)

    def test_paper_question_unique(self):
        names = [getattr(c, "name", "") for c in ExamPaperQuestion.__table__.constraints if hasattr(c, "columns")]
        assert "uq_paper_question" in names

    def test_attempt_unique(self):
        names = [getattr(c, "name", "") for c in ExamAttempt.__table__.constraints if hasattr(c, "columns")]
        assert "uq_exam_attempt" in names

    def test_attempt_columns(self):
        mapper = inspect(ExamAttempt)
        cols = {c.key for c in mapper.columns}
        assert {"paper_id", "student_id", "status", "answers", "auto_score", "manual_score", "total_score"}.issubset(cols)


class TestSchemas:
    """exam schema 校验"""

    def test_question_create_defaults(self):
        q = QuestionCreate(title="1 + 1 = ?", answer=["A"], options=[{"key": "A", "text": "2"}])
        assert q.qtype == "single"
        assert q.difficulty == "medium"
        assert q.score == 5

    def test_question_create_bad_type(self):
        with pytest.raises(ValidationError):
            QuestionCreate(title="x", qtype="essay")

    def test_question_create_bad_difficulty(self):
        with pytest.raises(ValidationError):
            QuestionCreate(title="x", difficulty="nightmare")

    def test_question_create_score_range(self):
        with pytest.raises(ValidationError):
            QuestionCreate(title="x", score=0)
        with pytest.raises(ValidationError):
            QuestionCreate(title="x", score=101)

    def test_question_out_from_orm(self):
        q = ExamQuestion(
            id=uuid.uuid4(), course_id=uuid.uuid4(), qtype="single", title="t",
            answer=["A"], score=5, difficulty="easy", created_by=uuid.uuid4(),
            created_at="2026-08-31T12:00:00+08:00",
        )
        out = QuestionOut.model_validate(q)
        assert out.answer == ["A"]

    def test_paper_create_duration_range(self):
        p = PaperCreate(title="期中考试")
        assert p.duration_minutes == 60
        with pytest.raises(ValidationError):
            PaperCreate(title="x", duration_minutes=1)

    def test_paper_out_defaults(self):
        p = PaperOut(
            id=uuid.uuid4(), course_id=uuid.uuid4(), title="t",
            duration_minutes=60, total_score=0, status="draft",
            created_by=uuid.uuid4(), created_at="2026-08-31T12:00:00+08:00",
        )
        assert p.question_count == 0
        assert p.my_attempt is None

    def test_auto_generate_constraints(self):
        g = AutoGenerateIn(count=10)
        assert g.count == 10
        with pytest.raises(ValidationError):
            AutoGenerateIn(count=0)

    def test_start_attempt_out(self):
        out = StartAttemptOut(
            attempt_id=uuid.uuid4(), started_at="2026-08-31T12:00:00+08:00",
            duration_minutes=60, end_at=None, questions=[],
        )
        assert out.duration_minutes == 60
        assert out.questions == []


class TestScoring:
    """自动评分纯函数"""

    def test_is_objective(self):
        assert is_objective("single")
        assert is_objective("multiple")
        assert is_objective("true_false")
        assert not is_objective("short_answer")

    def test_judge_single_correct(self):
        assert judge_answer("single", ["A"], ["A"]) is True

    def test_judge_single_wrong(self):
        assert judge_answer("single", ["A"], ["B"]) is False

    def test_judge_multiple_order_insensitive(self):
        assert judge_answer("multiple", ["A", "B"], ["B", "A"]) is True

    def test_judge_multiple_partial_wrong(self):
        assert judge_answer("multiple", ["A", "B"], ["A"]) is False

    def test_judge_true_false(self):
        assert judge_answer("true_false", ["T"], ["T"]) is True
        assert judge_answer("true_false", ["T"], ["F"]) is False

    def test_judge_short_answer_not_auto(self):
        assert judge_answer("short_answer", None, [{"text": "答案"}]) is None

    def test_judge_unanswered(self):
        assert judge_answer("single", ["A"], []) is False

    def test_judge_empty_correct_is_false(self):
        # 未配置答案的题不应判对
        assert judge_answer("single", None, ["A"]) is False


def _q(qid, difficulty="medium", qtype="single", tags=None):
    return SimpleNamespace(
        id=qid, difficulty=difficulty, qtype=qtype, tags=tags or []
    )


class TestSmartGenerate:
    """智能组卷算法"""

    def test_select_limited_by_count(self):
        qs = [_q(str(i)) for i in range(20)]
        picked = select_questions(qs, count=5)
        assert len(picked) == 5

    def test_select_filters_difficulty(self):
        qs = [_q("1", difficulty="easy"), _q("2", difficulty="hard"), _q("3", difficulty="easy")]
        picked = select_questions(qs, count=10, difficulty="easy")
        assert [str(q.id) for q in picked] == ["1", "3"]

    def test_select_filters_qtype(self):
        qs = [_q("1", qtype="single"), _q("2", qtype="multiple"), _q("3", qtype="single")]
        picked = select_questions(qs, count=10, qtype_filter="multiple")
        assert [str(q.id) for q in picked] == ["2"]

    def test_select_filters_tag(self):
        qs = [_q("1", tags=["期中"]), _q("2", tags=["期末"]), _q("3", tags=["期中", "易"])]
        picked = select_questions(qs, count=10, tag="期中")
        assert [str(q.id) for q in picked] == ["1", "3"]

    def test_select_excludes_existing(self):
        qs = [_q("1"), _q("2"), _q("3")]
        picked = select_questions(qs, count=10, exclude_ids={"1"})
        assert "1" not in {str(q.id) for q in picked}

    def test_select_insufficient_returns_all(self):
        qs = [_q("1"), _q("2")]
        picked = select_questions(qs, count=50)
        assert len(picked) == 2

    def test_select_empty_pool(self):
        assert select_questions([], count=5) == []

    def test_select_no_match_tag(self):
        qs = [_q("1", tags=["期中"])]
        assert select_questions(qs, count=5, tag="期末") == []

    def test_select_stable_when_count_ge_pool(self):
        qs = [_q("1"), _q("2"), _q("3")]
        a = select_questions(qs, count=3, seed=42)
        b = select_questions(qs, count=3, seed=42)
        assert [str(q.id) for q in a] == [str(q.id) for q in b]


class TestEvents:
    """exam 埋点常量存在"""

    def test_event_constants(self):
        assert EVENT_EXAM_QUESTION_CREATE == "exam.question_create"
        assert EVENT_EXAM_PAPER_CREATE == "exam.paper_create"
        assert EVENT_EXAM_PAPER_GENERATE == "exam.paper_generate"
        assert EVENT_EXAM_PAPER_PUBLISH == "exam.paper_publish"
        assert EVENT_EXAM_ATTEMPT_START == "exam.attempt_start"
        assert EVENT_EXAM_ATTEMPT_SUBMIT == "exam.attempt_submit"
        assert EVENT_EXAM_MANUAL_GRADE == "exam.manual_grade"


class TestOpenAPI:
    """OpenAPI 注册回归"""

    def test_exam_paths_registered(self):
        spec = app.openapi()
        paths = spec["paths"]
        for p in (
            "/api/v1/courses/{course_id}/questions",
            "/api/v1/questions/{question_id}",
            "/api/v1/courses/{course_id}/papers",
            "/api/v1/papers/{paper_id}",
            "/api/v1/papers/{paper_id}/generate",
            "/api/v1/papers/{paper_id}/publish",
            "/api/v1/papers/{paper_id}/start",
            "/api/v1/papers/{paper_id}/submit",
            "/api/v1/papers/{paper_id}/attempts",
            "/api/v1/attempts/{attempt_id}/manual-grade",
            "/api/v1/papers/{paper_id}/stats",
        ):
            assert p in paths, f"缺少路径 {p}"