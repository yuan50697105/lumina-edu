#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================
# Lumina 墨光 · 消息通知冒烟（V1.1 · D-03）
# 自助注册 → 欢迎通知 → 未读数 → 列表 → 单条已读 → 全部已读
# 负例：重复邮箱 409 / admin 角色 422 / 短密码 422
#   python 部署/scripts/smoke_notif.py [--base http://127.0.0.1:8081]
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
    try:
        return json.loads(raw) if raw else None
    except Exception:
        return None


def call(method: str, path: str, token: str = "", body=None, ok=(200, 201)):
    """ok 参数沿袭既有脚本（用于可读性）；实际调用方自行判断返回值"""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, _json(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, _json(e.read())


def login(email: str, password: str):
    code, body = call("POST", "/api/v1/auth/login", body={"username": email, "password": password, "device": "web"})
    assert code == 200, f"登录失败 {email}: {body}"
    return body["access_token"]


def register(payload: dict):
    return call("POST", "/api/v1/auth/register", body=payload)


def main() -> int:
    global PASS, FAIL, BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8081")
    args = ap.parse_args()
    BASE = args.base
    print(f"── D-03 消息通知冒烟 · {BASE} ──")

    # 0. 连接性：教师登录（验证服务在线 + 种子账号）
    teacher = login("teacher@lumina.edu", "Demo@2026")
    check("服务在线 · 教师登录", bool(teacher))

    # 1. 自助注册（学生）→ 201 + token + 欢迎通知
    tag = uuid.uuid4().hex[:8]
    email = f"smoke{tag}@lumina.edu"
    sid = f"20{tag[:6]}"
    code, body = register({
        "name": "冒烟新同学", "email": email, "password": "Smoke@2026",
        "student_id": sid, "role": "student", "device": "web",
    })
    check("注册学生 201", code == 201, f"code={code} {body}")
    if code != 201:
        return 1
    new_token = body["access_token"]
    new_uid = body["user"]["id"]
    check("注册即自动登录(user.id)", bool(new_uid))

    # 2. 欢迎通知未读数为 1
    code, body = call("GET", "/api/v1/notifications/my/unread-count", token=new_token)
    check("欢迎通知未读数 = 1", (body or {}).get("unread_count") == 1, f"{body}")

    # 3. 我的通知列表含 welcome
    code, body = call("GET", "/api/v1/notifications/my", token=new_token)
    items = body or []
    welcome = next((n for n in items if n.get("type") == "welcome"), None)
    check("我的通知列表含欢迎", bool(welcome), f"n={len(items)}")
    nid = welcome["id"] if welcome else None

    # 4. 单条已读 → 未读 0
    if nid:
        code, _ = call("POST", f"/api/v1/notifications/my/{nid}/read", token=new_token)
        check("标记单条已读 200", code == 200)
        code, body = call("GET", "/api/v1/notifications/my/unread-count", token=new_token)
        check("已读后未读 = 0", (body or {}).get("unread_count") == 0, f"{body}")

    # 5. 再写入一条（注册第二个用户把欢迎通知删掉的场景不存在；这里用 system 类型模拟不可行——只验证 read-all 幂等）
    code, _ = call("POST", "/api/v1/notifications/my/read-all", token=new_token)
    check("全部已读幂等 200", code == 200)

    # 6. 越权：他人通知不可读写（404）
    code, _ = call("POST", f"/api/v1/notifications/my/{nid}/read", token=teacher)
    check("越权读他人通知 404", code == 404, f"code={code}")

    # 7. 负例：重复邮箱 / admin 角色 / 短密码
    code, body = register({"name": "重复", "email": email, "password": "Smoke@2026"})
    check("重复邮箱 409", code == 409, f"code={code}")
    code, body = register({"name": "管理员", "email": f"admin{tag}@lumina.edu", "password": "Smoke@2026", "role": "admin"})
    check("admin 角色被拒 422", code == 422, f"code={code}")
    code, body = register({"name": "短密码", "email": f"short{tag}@lumina.edu", "password": "a"})
    check("短密码被拒 422", code == 422, f"code={code}")

    print(f"── 结果：{PASS} PASS / {FAIL} FAIL ──")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())