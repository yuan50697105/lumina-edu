#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================
# Lumina 墨光 · 题库与考试冒烟（V1.1 · D-04）
# 建题（含 422 负例）→ 建卷 → 加题 → 智能组卷 → 发布 → 开始 → 提交自动评分
# → 重复提交 409 / 未选课 403 / 越权 403 → 教师统计 → 主观题人工评分
#   python 部署/scripts/smoke_exam.py [--base http://127.0.0.1:8082]
# 通过则输出 PASS/FAIL 计数，任一失败 exit 1（用于 CI 门禁）
# ============================================
import argparse
import sys
import urllib.error
import urllib.request
import uuid

PASS = 0
FAIL = 0
BASE = ""


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")


def _json(raw):
    import json
    try:
        return json.loads(raw) if raw else None
    except Exception:
        return None


def call(method: str, path: str, token: str = "", body=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    data = None
    if body is not None:
        data = __import__("json").dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, _json(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, _json(e.read())


def login(email, password):
    code, body = call("POST", "/api/v1/auth/login",
                      body={"username": email, "password": password, "device": "web"})
    assert code == 200, f"登录失败 {email}: {body}"
    return body["access_token"]


def main() -> int:
    global PASS, FAIL, BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8082")
    args = ap.parse_args()
    BASE = args.base
    print(f"── D-04 题库与考试冒烟 · {BASE} ──")

    # 0. 登录：教师 / 学生 / 未选课学生
    teacher = login("teacher@lumina.edu", "Demo@2026")
    student = login("student@lumina.edu", "Demo@2026")
    nouser = login("nouser@lumina.edu", "Demo@2026")
    check("服务在线 · 三角色登录", bool(teacher and student and nouser))

    # 1. 定位课程 CS101
    code, body = call("GET", "/api/v1/courses", token=teacher)
    cs101 = next((c for c in (body or {}).get("data", [])
                  if c.get("title") and "程序设计基础" in c.get("title", "")), None)
    check("找到课程 CS101", bool(cs101), f"{body}")
    if not cs101:
        print(f"── 结果：{PASS} PASS / {FAIL} FAIL ──")
        return 1
    cid = cs101["id"]
    tag = uuid.uuid4().hex[:8]

    # 2. 创建客观题（单选）
    qid = None
    code, body = call("POST", f"/api/v1/courses/{cid}/questions", token=teacher, body={
        "qtype": "single", "title": f"冒烟单选题 {tag}",
        "options": [{"key": "A", "text": "选择甲"}, {"key": "B", "text": "选择乙"}],
        "answer": ["A"], "score": 5, "difficulty": "easy", "tags": ["冒烟"]})
    check("创建单选题 201", code == 201, f"code={code} {body}")
    qid = (body or {}).get("id") if code == 201 else None

    code, body = call("POST", f"/api/v1/courses/{cid}/questions", token=teacher, body={
        "qtype": "single", "title": f"冒烟简答题 {tag}", "answer": None})
    check("客观题缺答案 422", code == 422, f"code={code}")

    code, body = call("POST", f"/api/v1/courses/{cid}/questions", token=teacher, body={
        "qtype": "short_answer", "title": f"冒烟简答 {tag}", "score": 10})
    short_id = (body or {}).get("id") if code == 201 else None
    check("创建简答题 201", code == 201, f"code={code} {body}")

    if not qid or not short_id:
        print(f"── 结果：{PASS} PASS / {FAIL} FAIL ──")
        return 1

    # 3. 题目列表（教师视角含答案）
    code, body = call("GET", f"/api/v1/courses/{cid}/questions", token=teacher)
    items = (body or {}).get("data", [])
    mine = next((q for q in items if q.get("id") == qid), None)
    check("题目列表含新建题(含答案)", bool(mine and mine.get("answer") == ["A"]))

    # 4. 创建试卷 + 发布
    code, body = call("POST", f"/api/v1/courses/{cid}/papers", token=teacher, body={
        "title": f"冒烟试卷 {tag}", "description": "冒烟专用", "duration_minutes": 30})
    check("创建试卷 201", code == 201, f"code={code}")
    pid = (body or {}).get("id") if code == 201 else None
    if not pid:
        print(f"── 结果：{PASS} PASS / {FAIL} FAIL ──")
        return 1

    code, body = call("POST", f"/api/v1/papers/{pid}/questions", token=teacher, body={
        "question_id": qid, "score": 5})
    check("试卷加入题目 201", code == 201, f"code={code} {body}")
    code, body = call("POST", f"/api/v1/papers/{pid}/questions", token=teacher, body={
        "question_id": short_id})
    check("试卷加入简答题 201", code == 201, f"code={code} {body}")

    # 5. 智能组卷（easy 抽 2 题追加）
    code, body = call("POST", f"/api/v1/papers/{pid}/generate", token=teacher, body={
        "count": 2, "difficulty": "easy"})
    gen_ok = code == 200
    check("智能组卷 200", gen_ok, f"code={code} {body}")
    if gen_ok:
        n = (body or {}).get("question_count")
        check("组卷后题目数与总分正确", n == 4 and (body or {}).get("total_score") == 25, f"n={n} total={body and body.get('total_score')}")

    # 6. 发布（空卷负例 → 新建空卷再发布应 400）
    code, body = call("POST", f"/api/v1/courses/{cid}/papers", token=teacher, body={"title": f"空卷 {tag}"})
    empty_pid = (body or {}).get("id") if code == 201 else None
    code, _ = call("POST", f"/api/v1/papers/{empty_pid}/publish", token=teacher)
    check("空卷发布被拒 400", code == 400, f"code={code}")

    code, body = call("POST", f"/api/v1/papers/{pid}/publish", token=teacher)
    check("发布试卷 200", code == 200 and (body or {}).get("status") == "published", f"code={code}")

    # 7. 学生开始考试（含未发布卷负例 / 未选课负例）
    code, body = call("POST", f"/api/v1/courses/{cid}/papers", token=teacher, body={"title": f"未发布卷 {tag}"})
    draft_pid = (body or {}).get("id") if code == 201 else None
    code, _ = call("POST", f"/api/v1/papers/{draft_pid}/start", token=student)
    check("未发布卷开始被拒 403", code == 403, f"code={code}")
    code, _ = call("POST", f"/api/v1/papers/{pid}/start", token=nouser)
    check("未选课学生开始被拒 403", code == 403, f"code={code}")

    code, body = call("POST", f"/api/v1/papers/{pid}/start", token=student)
    check("学生开始考试 201", code == 201, f"code={code} {body}")
    attempt_id = (body or {}).get("attempt_id") if code == 201 else None
    questions = (body or {}).get("questions", []) if code == 201 else []
    check("开始返回题目且不含答案", len(questions) == 4 and all(q.get("answer") is None for q in questions),
          f"n={len(questions)}")

    # 8. 幂等：重复 start 返回同一 attempt
    code2, body2 = call("POST", f"/api/v1/papers/{pid}/start", token=student)
    check("重复开始幂等(同 attempt)", code2 == 201 and body2.get("attempt_id") == attempt_id)

    # 9. 提交自动评分（客观题全对 + 简答作答）
    code, body = call("POST", f"/api/v1/papers/{pid}/submit", token=student, body={
        "answers": [
            {"question_id": qid, "answer": ["A"]},
            {"question_id": short_id, "answer": [{"text": "列表可变元组不可变"}]},
        ]})
    check("提交作答 200 自动评分", code == 200 and (body or {}).get("auto_score") == 5, f"code={code} {body}")
    code, _ = call("POST", f"/api/v1/papers/{pid}/submit", token=student, body={"answers": []})
    check("重复提交被拒 409", code == 409, f"code={code}")

    # 10. 越权：他人答卷不可看
    code, _ = call("GET", f"/api/v1/attempts/{attempt_id}", token=nouser)
    check("越权查看他人答卷 403", code == 403, f"code={code}")

    # 11. 教师：提交列表 + 统计
    code, body = call("GET", f"/api/v1/papers/{pid}/attempts", token=teacher)
    check("教师提交列表 200", code == 200 and isinstance(body, list) and len(body) >= 1)
    code, body = call("GET", f"/api/v1/papers/{pid}/stats", token=teacher)
    check("教师统计 200", code == 200 and (body or {}).get("submitted_count") >= 1, f"{body}")
    if code == 200:
        qstats = (body or {}).get("question_stats", [])
        obj = next((s for s in qstats if s.get("question_id") == qid), None)
        check("统计含客观题正确率", bool(obj and obj.get("accuracy") == 1.0), f"{obj}")

    # 12. 主观题人工评分 + 负例
    code, body = call("GET", f"/api/v1/papers/{pid}/attempts", token=teacher)
    real_attempt = body[0]["id"] if isinstance(body, list) and body else None
    code, body = call("POST", f"/api/v1/attempts/{real_attempt}/manual-grade", token=teacher, body={
        "question_id": qid, "score": 5})
    check("客观题人工评分被拒 400", code == 400, f"code={code}")
    code, body = call("POST", f"/api/v1/attempts/{real_attempt}/manual-grade", token=teacher, body={
        "question_id": short_id, "score": 8})
    check("主观题人工评分 200", code == 200 and (body or {}).get("manual_score") == 8, f"code={code} {body}")
    check("评分后总分 = 客观 + 人工",
          code == 200 and (body or {}).get("total_score") == 13, f"{body and body.get('total_score')}")

    # 13. 教师删除题目 → 成功
    code, _ = call("DELETE", f"/api/v1/questions/{qid}", token=teacher)
    check("删除题目 200", code == 200, f"code={code}")

    print(f"── 结果：{PASS} PASS / {FAIL} FAIL ──")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())