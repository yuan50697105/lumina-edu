# ============================================
# Lumina 墨光 · AI 对话服务 苏格拉底导师提示词引擎
# 纯函数：可独立单元测试
# ============================================

# 苏格拉底导师 System Prompt（教育引导型）
SOCRATIC_SYSTEM_PROMPT = (
    "你是「苏格拉底导师」，Lumina 墨光学习平台的 AI 助教。\n"
    "行为准则：\n"
    "1. 用提问引导思考，而不是直接给答案——先启发，再逐步收敛；\n"
    "2. 结合学生当前学习的课程/章节内容作答；\n"
    "3. 全程使用简体中文，语气亲切耐心；\n"
    "4. 学生思路有误时，先肯定其思考，再温和地引导修正；\n"
    "5. 涉及公式/定理时使用 LaTeX 数学记法（$...$ / $$...$$）。"
)

# 生成首条消息标题的截断长度
TITLE_PREFIX_LEN = 20

# 单次请求携带的历史消息条数上限（防 context 超长）
MAX_HISTORY_MESSAGES = 20


def context_paragraph(context: dict | None) -> str:
    """把课程/章节上下文转成自然语言段落（无则返回空串）"""
    if not context:
        return ""
    parts = []
    if context.get("course_id"):
        parts.append(f"课程ID {context['course_id']}")
    if context.get("chapter_id"):
        parts.append(f"章节ID {context['chapter_id']}")
    return ("学生当前正在学习：" + "、".join(parts) + "。\n\n") if parts else ""


def build_messages(
    history: list[dict],
    new_message: str,
    context: dict | None = None,
    max_history: int = MAX_HISTORY_MESSAGES,
) -> list[dict]:
    """构造发送给 AI 网关的 messages 列表。

    history: 会话历史 [{role, content}]（user/assistant）
    returns: [system(苏格拉底+上下文), *history(近 max_history 条), user(新消息)]
    """
    system = SOCRATIC_SYSTEM_PROMPT
    ctx = context_paragraph(context)
    if ctx:
        system = ctx + system

    messages: list[dict] = [{"role": "system", "content": system}]
    messages.extend(history[-max_history:])
    messages.append({"role": "user", "content": new_message})
    return messages


def auto_title(message: str) -> str:
    """由首条消息生成会话标题（前 20 字符）"""
    title = message.strip().replace("\n", " ")
    return title[:TITLE_PREFIX_LEN] + ("…" if len(title) > TITLE_PREFIX_LEN else "")