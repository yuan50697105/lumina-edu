# ============================================
# Lumina 墨光 · AI 批阅服务 提示词引擎 + 结果解析
# 纯函数：可独立单元测试
# ============================================
import json
import re
from typing import Optional

# 阅卷助手 System Prompt（结构化 JSON 输出）
GRADING_SYSTEM_PROMPT = (
    "你是 Lumina 墨光学习平台的 AI 阅卷助手。\n"
    "请严格依据评分标准对学生作业逐项评分，并给出整体反馈。\n"
    "评分要求：\n"
    "1. 客观、一致性优先，同类错误给分一致；\n"
    "2. 每个评分维度的分数不得超过其满分（max）；\n"
    "3. 每个维度给出简短评语（comment），指出得分与失分点；\n"
    "4. 整体 feedback 用简体中文，语气专业温和，先肯定再指正；\n"
    "5. confidence 为本次批阅的置信度（0~1 小数）。\n"
    "只输出 JSON，不要输出任何其他文字、注释或 markdown 代码块：\n"
    '{"scores": [{"criteria": "维度名", "score": 分数, "max": 满分, "comment": "评语"}], '
    '"total": 总分, "feedback": "整体反馈", "confidence": 0.9}'
)


def build_rubric_text(rubric: list[dict]) -> str:
    """rubric 列表 → 评分标准文本（权重 + 满分）"""
    if not rubric:
        return "（未提供评分标准）"
    lines = []
    for i, r in enumerate(rubric, 1):
        criteria = r.get("criteria", f"维度{i}")
        weight = r.get("weight", 0)
        max_score = r.get("max_score", 100)
        lines.append(f"{i}. {criteria}（权重 {weight}，满分 {max_score}）")
    return "\n".join(lines)


def build_grading_messages(
    *,
    assignment_title: str,
    assignment_desc: str,
    rubric: list[dict],
    answer_text: str,
    file_urls: Optional[list[str]] = None,
) -> list[dict]:
    """构造发给 AI 网关的批阅 messages（含作业要求 / 评分标准 / 学生答案）"""
    rubric_text = build_rubric_text(rubric)
    attachments = ""
    if file_urls:
        attachments = "\n附件文件：" + "、".join(file_urls)
    if not answer_text.strip() and file_urls:
        answer_text = "（学生以附件形式提交作业，附件见上；请基于可读取内容评分）"

    user_prompt = (
        f"【作业题目】{assignment_title}\n"
        f"【作业要求】{assignment_desc or '（无）'}\n"
        f"【评分标准】\n{rubric_text}\n"
        f"{attachments}\n"
        f"【学生答案】\n{answer_text}\n\n"
        f"请按评分标准逐项评分，并返回 JSON。"
    )
    return [
        {"role": "system", "content": GRADING_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


# ─── 模型输出 JSON 解析（容错）───
def extract_json(text: str) -> dict:
    """从模型输出中提取 JSON 对象（兼容 ```json 围栏/前导文字/尾注）"""
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        raise ValueError("响应中未找到 JSON 对象")
    return json.loads(t[i:j + 1])


def parse_grade_result(obj: dict, default_max: int = 100) -> dict:
    """防御性解析模型批阅结果：缺字段取默认、分数 clamp 到 [0, max]、confidence clamp 到 [0,1]"""
    scores = []
    total = 0
    for s in obj.get("scores") or []:
        if not isinstance(s, dict):
            continue
        mx = int(s.get("max") or default_max)
        score = int(s.get("score") or 0)
        score = max(0, min(score, mx))
        total += score
        scores.append({
            "criteria": str(s.get("criteria") or "维度"),
            "score": score,
            "max": mx,
            "comment": str(s.get("comment") or ""),
        })
    feedback = str(obj.get("feedback") or "")
    try:
        confidence = float(obj.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(confidence, 1.0))
    return {
        "scores": scores,
        "total": total,
        "feedback": feedback,
        "confidence": confidence,
    }