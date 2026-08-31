#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================
# Lumina 墨光 · 协作工具冒烟（V1.1 · D-02）
# 小组/加入/项目/看板(列·卡·移动)/讨论/文件 全流程 + 越权负例
#   python 部署/scripts/smoke_collab.py [--base http://127.0.0.1:8081]
# 通过则输出 PASS/FAIL 计数，任一失败 exit 1（用于 CI 门禁）
# ============================================
import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")


def _json(raw) -> dict | None:
    """安全解析 JSON（下载等非 JSON 响应返回 None）"""
    try:
        return json.loads(raw) if raw else None
    except Exception:
        return None


def call(method: str, path: str, token: str = "", body=None, files=None, ok=(200, 201)):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    data = None
    if files:
        boundary = uuid.uuid4().hex
        pname, (filename, content, ctype) = next(iter(files.items()))
        head = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{pname}"; filename="{filename}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n"
        ).encode()
        data = head + content + f"\r\n--{boundary}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return resp.status, _json(raw)
    except urllib.error.HTTPError as e:
        return e.code, _json(e.read())


def login(email: str, password: str):
    code, body = call("POST", "/api/v1/auth/login", body={"username": email, "password": password, "device": "web"})
    assert code == 200, f"登录失败 {email}: {body}"
    return body["access_token"]


def main() -> int:
    global PASS, FAIL, BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8081")
    args = ap.parse_args()
    BASE = args.base
    print(f"── D-02 协作工具冒烟 · {BASE} ──")

    teacher = login("teacher@lumina.edu", "Demo@2026")
    student = login("student@lumina.edu", "Demo@2026")
    nouser = login("nouser@lumina.edu", "Demo@2026")

    # 1. 获取一门课程
    code, body = call("GET", "/api/v1/courses?limit=10", token=teacher)
    courses = (body or {}).get("data") or []
    course = next((c for c in courses if "冒烟" in (c.get("title") or "")), None) or (courses[0] if courses else None)
    check("获取冒烟课程", bool(course), f"courses={len(courses)}")
    if not course:
        return 1
    cid = course["id"]
    print(f"  课程: {course['title']}")

    # 2. 教师创建小组
    code, g = call("POST", f"/api/v1/courses/{cid}/groups", token=teacher,
                   body={"name": "冒烟第 3 组", "description": "自动化验证"})
    check("教师创建小组", code == 201, f"{code}")
    if code != 201:
        return 1
    gid = g["id"]
    check("组长自动入组", g["member_count"] == 1 and g["is_member"] is True)

    # 3. 越权负例：未选课学生不可见/不可加
    code, _ = call("GET", f"/api/v1/groups/{gid}", token=nouser)
    check("未选课不可看小组 (403)", code == 403, f"{code}")
    code, _ = call("POST", f"/api/v1/groups/{gid}/members", token=nouser)
    check("未选课不可加入小组 (403)", code == 403, f"{code}")

    # 4. 学生加入小组
    code, g2 = call("POST", f"/api/v1/groups/{gid}/members", token=student)
    check("学生加入小组", code == 201 and g2["member_count"] == 2, f"{code}")
    code, _ = call("POST", f"/api/v1/groups/{gid}/members", token=student)
    check("重复加入被拒 (409)", code == 409, f"{code}")

    # 5. 课程小组列表可见（学生）
    code, lst = call("GET", f"/api/v1/courses/{cid}/groups", token=student)
    check("课程小组列表可见", code == 200 and any(x["id"] == gid for x in lst), f"{code}")

    # 6. 项目 + 看板
    code, p = call("POST", f"/api/v1/groups/{gid}/projects", token=student,
                   body={"title": "期中报告", "description": "芯片调研"})
    check("创建项目", code == 201, f"{code}")
    pid = p["id"]

    code, col1 = call("POST", f"/api/v1/projects/{pid}/columns", token=student, body={"title": "待办"})
    code, col2 = call("POST", f"/api/v1/projects/{pid}/columns", token=student, body={"title": "进行中"})
    check("新建两列", code == 201, f"{code}")

    code, card = call("POST", f"/api/v1/columns/{col1['id']}/cards", token=student, body={"title": "资料收集"})
    check("新建卡片", code == 201, f"{code}")
    if code != 201:
        return 1

    code, moved = call("PATCH", f"/api/v1/cards/{card['id']}", token=student, body={"column_id": col2["id"]})
    check("拖拽换列", code == 200 and moved["column_id"] == col2["id"], f"{code}")

    code, board = call("GET", f"/api/v1/projects/{pid}/board", token=student)
    col2cards = next((c for c in board["columns"] if c["id"] == col2["id"]), {})
    check("看板聚合（卡片入列）", code == 200 and len(col2cards.get("cards", [])) == 1, f"{code}")

    # 7. 讨论
    code, t = call("POST", f"/api/v1/groups/{gid}/topics", token=student,
                   body={"title": "分工安排", "content": "周一起跑"})
    check("发表主题", code == 201, f"{code}")
    tid = t["id"]
    code, r = call("POST", f"/api/v1/topics/{tid}/replies", token=teacher, body={"content": "收到"})
    check("回复主题", code == 201, f"{code}")
    code, detail = call("GET", f"/api/v1/topics/{tid}", token=student)
    check("主题详情含回复", code == 200 and detail["reply_count"] == 1, f"{code}")

    # 8. 共享文件
    code, f1 = call("POST", f"/api/v1/groups/{gid}/files", token=student,
                    files={"file": ("课题说明.txt", "协作冒烟内容".encode("utf-8"), "text/plain")})
    check("上传文件", code == 201 and f1["size"] > 0, f"{code}")
    code, fl = call("GET", f"/api/v1/groups/{gid}/files", token=student)
    check("文件列表", code == 200 and len(fl) == 1, f"{code}")
    code, _ = call("GET", f"/api/v1/files/{f1['id']}/download", token=student)
    check("下载文件", code == 200, f"{code}")

    # 9. 清理：教师删除小组（级联）
    code, _ = call("DELETE", f"/api/v1/groups/{gid}", token=teacher)
    check("清理小组（级联删除）", code == 200, f"{code}")
    code, _ = call("GET", f"/api/v1/groups/{gid}", token=teacher)
    check("小组已删除 (404)", code == 404, f"{code}")

    print(f"\n结果：PASS {PASS} · FAIL {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())