#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================
# Lumina 墨光 · 端到端冒烟测试（WBS 2.12）
# --------------------------------------------
# 全链路：登录 → 建课 → 章节 → 选课 → 发布作业 → 学生提交
#       → 教师批阅 → 录入期末成绩 → 成绩单 → 埋点统计 → 日志查询
#
# 前置条件：compose 全部服务在线（POSTGRES 有预置用户）。
# 账号通过环境变量提供（缺省读取 LUMINA_*）：
#   LUMINA_TEACHER_EMAIL/PASSWORD、LUMINA_STUDENT_EMAIL/PASSWORD、LUMINA_ADMIN_EMAIL/PASSWORD
#
# 用法：
#   python 部署/scripts/smoke_test.py                      # 走 Nginx :80
#   python 部署/scripts/smoke_test.py --base http://localhost:8080 --ai
#   python 部署/scripts/smoke_test.py --dry-run            # 不发请求，校验流程/参数
# ============================================
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

BASE_DEFAULT = "http://localhost"
UA = "lumina-smoke-test"

pass_count = fail_count = skip_count = 0
results: list[tuple[str, bool, str]] = []    # (步骤, 通过?, 说明)


def log(name: str, ok: bool, detail: str = ""):
    global pass_count, fail_count, skip_count
    if ok is True:
        pass_count += 1
        mark = "✅ PASS"
    elif ok is False:
        fail_count += 1
        mark = "❌ FAIL"
    else:
        skip_count += 1
        mark = "⏭ SKIP"
    tag = f"{mark:8} {name}"
    print(f"{tag:44} {detail}")
    results.append((name, ok, detail))


class API:
    """极简 HTTP 客户端：JWT 注入 + JSON 序列化"""
    def __init__(self, base: str, dry: bool):
        self.base = base.rstrip("/")
        self.dry = dry
        self.token: str | None = None

    def call(self, method: str, path: str, body=None, ok_status=(200, 201, 202, 204)) -> tuple[int, dict | None]:
        url = self.base + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("User-Agent", UA)
        if data:
            req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        if self.dry:
            print(f"      [dry] {method} {path} body={data.decode() if data else '-'}")
            return 200, {}
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"raw": raw[:200]}


def main() -> int:
    global pass_count, fail_count, skip_count
    ap = argparse.ArgumentParser(description="Lumina 端到端冒烟测试")
    ap.add_argument("--base", default=os.getenv("LUMINA_BASE", BASE_DEFAULT))
    ap.add_argument("--ai", action="store_true", help="额外执行 AI 批阅（需模型已配置）")
    ap.add_argument("--dry-run", action="store_true", help="仅打印请求清单，不发 HTTP")
    args = ap.parse_args()

    dry = args.dry_run
    api = API(args.base, dry)

    teacher = os.getenv("LUMINA_TEACHER_EMAIL"), os.getenv("LUMINA_TEACHER_PASSWORD")
    student = os.getenv("LUMINA_STUDENT_EMAIL"), os.getenv("LUMINA_STUDENT_PASSWORD")
    admin = os.getenv("LUMINA_ADMIN_EMAIL"), os.getenv("LUMINA_ADMIN_PASSWORD")
    if any(x is None for x in teacher + student + admin):
        print("❌ 缺少账号环境变量：LUMINA_TEACHER_EMAIL/PASSWORD、LUMINA_STUDENT_EMAIL/PASSWORD、LUMINA_ADMIN_EMAIL/PASSWORD")
        return 2

    print(f"🌐 目标: {args.base}  {'（dry-run，不发请求）' if dry else ''}\n")

    # ─── S1 健康检查（Nginx 网关）───
    code, body = api.call("GET", "/health")
    log("S1 Nginx/健康检查", code == 200 and (body or {}).get("status") == "ok", f"{code} {body}")

    # ─── S2 各角色登录 ───
    def login(email, password, role):
        if dry:                                # dry-run：伪造 token，仅校验流程
            api.token = "dry-token"
            return True, {"access_token": "dry"}
        code, body = api.call("POST", "/api/v1/auth/login", {"username": email, "password": password, "device": "web"})
        if code == 200 and body and body.get("access_token"):
            api.token = body["access_token"]
            return True, body
        return False, body

    ok, tb = login(*teacher, "teacher")
    log("S2 教师登录", ok, tb.get("access_token", "")[:20] + "…" if ok else str(tb)[:120])
    teacher_token = api.token
    ok, sb = login(*student, "student")
    log("S3 学生登录", ok, sb.get("access_token", "")[:20] + "…" if ok else str(sb)[:120])
    student_token = api.token
    api.token = None
    ok, ab = login(*admin, "admin")
    log("S4 管理员登录", ok, ab.get("access_token", "")[:20] + "…" if ok else str(ab)[:120])
    admin_token = api.token
    if not (teacher_token and student_token and admin_token):
        print("❌ 任一角色登录失败，冒烟终止")
        return 1

    # ─── S5 教师建课 ───
    api.token = teacher_token
    ok, course = api.call("POST", "/api/v1/courses", {
        "code": "SMK201", "title": "冒烟测试课程", "semester": "2026-1",
        "description": "WBS 2.12 端到端验证", "credits": 3,
    })
    course_id = (course or {}).get("id")
    log("S5 教师建课", ok and bool(course_id), f"course_id={str(course_id)[:8]}…")

    # ─── S6 新增章节 ───
    ok, ch = api.call("POST", f"/api/v1/courses/{course_id}/chapters", {"title": "冒烟章节", "content": "内容"})
    chapter_id = (ch or {}).get("id")
    log("S6 新增章节", ok and bool(chapter_id), f"chapter_id={str(chapter_id)[:8]}…")

    # ─── S7 学生选课 ───
    api.token = student_token
    ok, en = api.call("POST", f"/api/v1/courses/{course_id}/enroll")
    log("S7 学生选课", ok, f"{en}")

    # ─── S8 教师发布作业 ───
    api.token = teacher_token
    ok, asg = api.call("POST", f"/api/v1/courses/{course_id}/assignments", {
        "title": "冒烟作业", "description": "端到端提交", "max_score": 100, "ai_grading": False,
    })
    asg_id = (asg or {}).get("id")
    log("S8 教师发布作业", ok and bool(asg_id), f"assignment_id={str(asg_id)[:8]}…")

    # ─── S9 学生提交作业 ───
    api.token = student_token
    ok, sub = api.call("POST", f"/api/v1/assignments/{asg_id}/submit", {"text_answer": "这是我的冒烟答案。"})
    sub_id = (sub or {}).get("id")
    log("S9 学生提交作业", ok and bool(sub_id), f"submission_id={str(sub_id)[:8]}…")

    # ─── S10 教师批阅作业 ───
    api.token = teacher_token
    ok, gr = api.call("POST", f"/api/v1/assignments/{asg_id}/grade", {"total_score": 92, "feedback": "批阅通过"})
    log("S10 教师批阅作业", ok, f"{gr.get('total_score') if isinstance(gr, dict) else gr}")

    # ─── S11 AI 批阅（可选）───
    if args.ai:
        api.token = teacher_token
        acode, ai = api.call("POST", "/api/v1/ai/grade", {"submission_id": str(sub_id), "model": None})
        if acode == 200:
            ok_val = True
            detail = f"{ai}"
        elif acode in (400, 502, 503):          # 模型未配置/无 Key —— 视为 SKIP
            ok_val = None
            detail = f"模型未就绪({acode})，跳过 AI 断言：{str(ai)[:100]}"
        else:
            ok_val = False
            detail = f"AI 批阅异常({acode}): {str(ai)[:100]}"
        log("S11 AI 批阅", ok_val, detail)
    else:
        log("S11 AI 批阅", None, "未启用 --ai，跳过")

    # ─── S12 教师录入期末成绩（需学生 uid → 先查 /users/me）───
    api.token = student_token
    ok, me = api.call("GET", "/api/v1/users/me")
    stu_uid = (me or {}).get("id")
    log("S12a 获取学生 uid(/users/me)", ok and bool(stu_uid), f"uid={str(stu_uid)[:8]}…")

    api.token = teacher_token
    ok, grd = api.call("POST", f"/api/v1/courses/{course_id}/grades", {
        "student_id": str(stu_uid), "semester": "2026-1", "final_score": 88,
    })
    log("S12 教师录入期末成绩", ok, f"{grd.get('final_score') if isinstance(grd, dict) else grd}")

    # ─── S13 学生查成绩单 ───
    api.token = student_token
    ok, sheet = api.call("GET", "/api/v1/grades/me")
    n_courses = len((sheet or {}).get("courses", [])) if sheet else -1
    log("S13 学生查成绩单", ok and n_courses >= 1, f"成绩单课程数={n_courses}")

    # ─── S14 管理员埋点统计 ───
    api.token = admin_token
    ok, stats = api.call("GET", "/api/v1/events/stats")
    log("S14 埋点统计(admin)", ok, f"{stats}")

    # ─── S15 管理员日志查询 ───
    ok, summ = api.call("GET", "/api/v1/logs/summary")
    log("S15 日志汇总(admin)", ok, f"total={summ.get('total') if isinstance(summ, dict) else '?'}")

    # ─── 汇总 ───
    print(f"\n{'=' * 56}\nPASS {pass_count}  |  FAIL {fail_count}  |  SKIP {skip_count}")
    if dry:
        print("ℹ dry-run：仅校验流程/请求构造，FAIL 项为预期假值")
        return 0
    if fail_count:
        print("❌ 存在失败步骤，请查看上表")
        return 1
    if skip_count:
        print("⚠ 含跳过步骤（成功但不完整）")
        return 0
    print("🎉 全链路冒烟通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())