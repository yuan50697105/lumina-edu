# ============================================
# Lumina 墨光 · AI 批阅服务单元测试
# 纯逻辑：提示词引擎 / JSON 容错解析 / Schema 校验
# 无需 PostgreSQL / 无需 AI 网关
# ============================================
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.prompt import (
    GRADING_SYSTEM_PROMPT,
    build_grading_messages,
    build_rubric_text,
    extract_json,
    parse_grade_result,
)
from app.schemas import GradeRequest, RubricItem


RUBRIC = [
    {"criteria": "解题过程完整", "weight": 0.4, "max_score": 40},
    {"criteria": "答案正确", "weight": 0.4, "max_score": 40},
    {"criteria": "书写规范", "weight": 0.2, "max_score": 20},
]


class TestPromptEngine:
    def test_rubric_text(self):
        txt = build_rubric_text(RUBRIC)
        assert "解题过程完整" in txt
        assert "权重 0.4" in txt
        assert "满分 40" in txt

    def test_empty_rubric_fallback(self):
        assert "未提供" in build_rubric_text([])

    def test_build_messages_structure(self):
        msgs = build_grading_messages(
            assignment_title="第四章习题",
            assignment_desc="完成 P120-P125",
            rubric=RUBRIC,
            answer_text="解：令 u=x^2",
        )
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert GRADING_SYSTEM_PROMPT in msgs[0]["content"]
        assert msgs[1]["role"] == "user"
        body = msgs[1]["content"]
        assert "第四章习题" in body
        assert "解：令 u=x^2" in body
        assert "返回 JSON" in body

    def test_build_messages_file_attachments(self):
        msgs = build_grading_messages(
            assignment_title="手写卷", assignment_desc="", rubric=RUBRIC,
            answer_text="", file_urls=["https://cdn/x.pdf"],
        )
        assert "x.pdf" in msgs[1]["content"]
        assert "附件形式" in msgs[1]["content"]  # 无文本时提示

    def test_build_user_prompt_max_scores(self):
        msgs = build_grading_messages(assignment_title="题", assignment_desc="",
                                      rubric=[{"criteria": "A", "weight": 1, "max_score": 10}],
                                      answer_text="答")
        assert "满分 10" in msgs[1]["content"]


class TestExtractJson:
    def test_bare_json(self):
        assert extract_json('{"a":1}') == {"a": 1}

    def test_fenced_json(self):
        txt = '```json\n{"total":88,"feedback":"好"}\n```'
        obj = extract_json(txt)
        assert obj["total"] == 88

    def test_preface_text(self):
        txt = '好的，以下是评分结果：\n{"total": 90}'
        assert extract_json(txt)["total"] == 90

    def test_trailing_comment(self):
        txt = '{"total": 70}\n（如需要可再批阅一次）'
        assert extract_json(txt)["total"] == 70

    def test_no_object_raises(self):
        with pytest.raises(ValueError):
            extract_json("抱歉，我无法评分。")

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError):
            extract_json("{total: 88}")   # 非标准 JSON

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            extract_json("")


class TestParseGradeResult:
    def test_normal(self):
        obj = {"scores": [
            {"criteria": "解题过程完整", "score": 36, "max": 40, "comment": "完整"},
            {"criteria": "答案正确", "score": 40, "max": 40, "comment": "正确"},
        ], "total": 76, "feedback": "整体不错", "confidence": 0.92}
        r = parse_grade_result(obj)
        assert r["total"] == 76
        assert r["confidence"] == 0.92
        assert len(r["scores"]) == 2
        assert r["scores"][0]["max"] == 40

    def test_score_clamped(self):
        obj = {"scores": [{"criteria": "A", "score": 999, "max": 40, "comment": ""}],
               "total": 999, "feedback": "", "confidence": 1.99}
        r = parse_grade_result(obj)
        assert r["scores"][0]["score"] == 40        # 不超过满分
        assert r["total"] == 40
        assert r["confidence"] == 1.0               # clamp 到 1

    def test_missing_fields_defaults(self):
        r = parse_grade_result({})
        assert r["scores"] == []
        assert r["total"] == 0
        assert r["feedback"] == ""
        assert r["confidence"] == 0.0

    def test_bad_entries_skipped(self):
        obj = {"scores": [{"criteria": "ok", "score": 5, "max": 10, "comment": ""},
                          "not-a-dict"],
               "total": 5}
        r = parse_grade_result(obj)
        assert len(r["scores"]) == 1

    def test_wrong_confidence_type(self):
        r = parse_grade_result({"confidence": "高"})
        assert r["confidence"] == 0.0


class TestGradeRequestSchema:
    def test_valid(self):
        req = GradeRequest(assignment_id=uuid.uuid4(), submission_id=uuid.uuid4(),
                           rubric=[RubricItem(criteria="x", weight=0.5, max_score=50)])
        assert req.rubric[0].max_score == 50

    def test_public_model_valid(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            RubricItem(criteria="", weight=0.5)          # criteria 必填
        with pytest.raises(ValidationError):
            RubricItem(criteria="x", weight=1.5)          # weight > 1