# ============================================
# Lumina 墨光 · 题库与考试 · 纯函数逻辑（D-04）
# 自动评分 / 题型判定 / 智能组卷筛选
# 无 DB 依赖，便于单元测试
# ============================================
import random
from typing import Any, Optional


OBJECTIVE_TYPES = ("single", "multiple", "true_false")

# 题型 → 是否需要选项/答案
def is_objective(qtype: str) -> bool:
    """客观题（可按选项集合自动判分）"""
    return qtype in OBJECTIVE_TYPES


def judge_answer(qtype: str, correct: Optional[list], stu: Optional[list]) -> Optional[bool]:
    """判定单题正误。

    - 客观题：学生选项集合 == 正确答案集合 → True；未答 → False；容错字符串化比较。
    - 主观题（short_answer）：返回 None（交由教师人工评分）。
    """
    if not is_objective(qtype):
        return None
    correct_set = {str(x) for x in (correct or [])}
    stu_set = {str(x) for x in (stu or [])}
    return bool(correct_set) and correct_set == stu_set


def select_questions(
    questions: list[Any],
    *,
    count: int,
    difficulty: Optional[str] = None,
    qtype_filter: Optional[str] = None,
    tag: Optional[str] = None,
    exclude_ids: Optional[set] = None,
    seed: Optional[int] = None,
) -> list[Any]:
    """智能组卷：按条件筛选 + 随机抽取 count 题。

    questions: 题库候选（SQLAlchemy Model 或含 .difficulty/.qtype/.tags/.id 的对象）
    exclude_ids: 已在试卷中的题目 id（避免重复组卷）
    返回抽取结果（数量 ≤ count；候选不足时返回全部命中）。
    """
    exclude = exclude_ids or set()
    pool = []
    for q in questions:
        if str(q.id) in {str(x) for x in exclude}:
            continue
        if difficulty and q.difficulty != difficulty:
            continue
        if qtype_filter and q.qtype != qtype_filter:
            continue
        if tag:
            tags = [str(t).lower() for t in (q.tags or [])]
            if tag.lower() not in tags:
                continue
        pool.append(q)
    if not pool:
        return []
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()
    if len(pool) <= count:
        return pool
    return rng.sample(pool, count)