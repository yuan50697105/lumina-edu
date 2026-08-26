# ============================================
# Lumina 墨光 · AI 批阅服务路由
# POST /ai/grade AI 辅助批阅 → 结构化成绩
# ============================================
import time as _t
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db
from .dependencies import AuthUser, require_role
from .gateway_client import GatewayError, fetch_completions, route_model
from .instrumentation import (
    EVENT_GRADE_DONE,
    EVENT_GRADE_ERROR,
    EVENT_GRADE_START,
    Instrumentation,
    Timer,
)
from .models import Grade
from .prompt import build_grading_messages, extract_json, parse_grade_result
from .schemas import GradeRequest, GradeResult, ScoreItem

router = APIRouter(prefix="/ai", tags=["AI 批阅"])


@router.post("/grade", response_model=GradeResult, summary="AI 辅助批阅")
def ai_grade(
    payload: GradeRequest,
    request: Request,
    teacher: AuthUser = Depends(require_role("teacher", "admin")),
    db: Session = Depends(get_db),
):
    """对某次作业提交调用 LLM 辅助批阅：按 rubric 逐项评分，写 grades 表，返回结构化结果。"""
    user_token = request.headers.get("authorization", "")
    if not user_token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少访问令牌")

    # ── 校验作业与提交 ──
    assignment = db.execute(
        text("""
            SELECT id, title, description, max_score, rubric, ai_model
            FROM assignments WHERE id = :aid
        """),
        {"aid": str(payload.assignment_id)},
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")

    sub = db.execute(
        text("""
            SELECT id, assignment_id, text_answer, file_urls
            FROM submissions WHERE id = :sid AND assignment_id = :aid
        """),
        {"sid": str(payload.submission_id), "aid": str(payload.assignment_id)},
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="提交不存在或与作业不匹配")

    # ── 评分标准：请求优先，否则取作业 rubric ──
    rubric = [r.model_dump() for r in payload.rubric] if payload.rubric else None
    if not rubric and assignment.rubric:
        rubric = assignment.rubric if isinstance(assignment.rubric, list) else None
    if not rubric:
        raise HTTPException(status_code=400, detail="缺少评分标准（请求 rubric 或作业 rubric）")

    # ── 模型：指定 or 智能路由（task_type=grade）──
    model_name = payload.model_name or request.headers.get("x-model")
    if not model_name:
        try:
            model_name = route_model(user_token, "grade")
        except GatewayError as e:
            raise HTTPException(status_code=400, detail=str(e))

    file_urls = [u for u in (payload.file_urls or []) if isinstance(u, str)]
    answer = sub.text_answer or ""
    messages = build_grading_messages(
        assignment_title=assignment.title,
        assignment_desc=assignment.description or "",
        rubric=rubric,
        answer_text=answer,
        file_urls=file_urls or None,
    )

    Instrumentation(db, request, str(teacher.id)).track(
        EVENT_GRADE_START, properties={
            "assignment_id": str(payload.assignment_id),
            "model": model_name,
            "criteria_count": len(rubric),
        }
    )

    # ── 调网关 → 解析 → 落库 ──
    with Timer() as timer:
        try:
            result = fetch_completions(model_name, messages, user_token,
                                       "grade", payload.max_tokens)
        except GatewayError as e:
            Instrumentation(db, request, str(teacher.id)).track(
                EVENT_GRADE_ERROR, properties={
                    "assignment_id": str(payload.assignment_id), "model": model_name,
                    "error": str(e)[:100],
                }
            )
            raise HTTPException(status_code=502, detail=str(e))

    try:
        parsed = parse_grade_result(extract_json(result["content"]))
    except (ValueError, TypeError, KeyError) as e:
        Instrumentation(db, request, str(teacher.id)).track(
            EVENT_GRADE_ERROR, properties={
                "assignment_id": str(payload.assignment_id), "model": model_name,
                "error": f"结果解析失败: {e}",
            }
        )
        raise HTTPException(status_code=502,
                            detail=f"模型输出无法解析，请重试（{result.get('model') or model_name}）")

    scores = parsed["scores"]
    total = parsed["total"]
    feedback = parsed["feedback"]
    confidence = parsed["confidence"]

    grade = db.query(Grade).filter(Grade.submission_id == payload.submission_id).first()
    if not grade:
        grade = Grade(submission_id=payload.submission_id)
        db.add(grade)
    grade.total_score = total
    grade.feedback = feedback
    grade.rubric_scores = scores
    grade.graded_by = "ai"
    grade.grader_id = teacher.id
    grade.ai_model = model_name
    grade.confidence = confidence
    db.commit()

    prompt_tokens = int(result.get("prompt_tokens") or 0)
    completion_tokens = int(result.get("completion_tokens") or 0)
    Instrumentation(db, request, str(teacher.id)).track(
        EVENT_GRADE_DONE, properties={
            "assignment_id": str(payload.assignment_id),
            "submission_id": str(payload.submission_id),
            "model": model_name,
            "confidence": confidence,
            "total": total,
            "criteria_count": len(scores),
            "tokens": prompt_tokens + completion_tokens,
            "latency_ms": timer.duration_ms,
        }
    )

    return GradeResult(data={
        "scores": [ScoreItem(**s) for s in scores],
        "total": total,
        "feedback": feedback,
        "model": model_name,
        "confidence": confidence,
    })