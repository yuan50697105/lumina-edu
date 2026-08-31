#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================
# Lumina 墨光 · 阶段三一键验证（准备 + 离线校验）
# --------------------------------------------
# 编排全部质量门禁，不依赖 PostgreSQL / Docker：
#   1. 纯单元测试（run_tests.py，不含集成）
#   2. 静态契约核对（api_contract_check.py）
#   3. 埋点事件目录校验（events_catalog.py --check）
#   4. 冒烟脚本结构自检（smoke_test.py --dry-run）
# --live 时额外执行真实冒烟/集成（需服务在线）
#   5. 冒烟（smoke_test.py）
#   6. 集成测试 run_tests.py --include-api
#   7. 轻量性能压测（load_test.py，20 并发 200 次 /health）
#
#   python 部署/scripts/verify_phase3.py
#   python 部署/scripts/verify_phase3.py --live --base http://localhost:8080
# ============================================
import argparse
import shutil
import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "部署" / "scripts"
PROXY = sys.executable  # 运行 verify 的同一 python


def run(cmd: list[str], label: str, env: dict[str, str] | None = None) -> tuple[bool, str]:
    print(f"\n{'='*60}\n▶ {label}\n{'='*60}")
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env or os.environ)
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    tail = [ln for ln in out.splitlines() if len(ln) < 140][-4:]
    for ln in tail:
        print(f"  {ln}")
    ok = proc.returncode == 0
    print(f"{'✅' if ok else '❌'} {label}  (exit {proc.returncode})")
    return ok, out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="执行真实联调（需服务在线）")
    ap.add_argument("--base", default="http://localhost:8080")
    ap.add_argument("--ai", action="store_true", help="含 AI 批阅验证")
    ap.add_argument("--python", default=None, help="Pytest 解释器（默认用 verify 自身的解释器）")
    args = ap.parse_args()

    if args.python:
        PROXY_CMD = args.python
    else:
        # 优先探测 venv
        PROXY_CMD = PROXY
        for s in (ROOT / "服务").iterdir():
            p = s / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            if p.exists():
                PROXY_CMD = str(p)
                break

    total, passed = 0, 0
    results = []

    def gate(cmd: list[str], label: str, env: dict[str, str] | None = None):
        nonlocal total, passed
        total += 1
        ok, _ = run(cmd, label, env=env)
        if ok:
            passed += 1
        results.append((label, ok))

    # ── 1-2 离线基线 ──
    gate([PROXY_CMD, str(SCRIPTS / "run_tests.py"), "--python", PROXY_CMD], "1. 单元测试")
    gate([PROXY_CMD, str(SCRIPTS / "api_contract_check.py")], "2. 静态契约核对")
    gate([PROXY_CMD, str(SCRIPTS / "events_catalog.py"), "--check"], "3. 埋点事件目录校验")

    smoke_dry = ["--dry-run"]
    dry_envs = {**os.environ,
                "LUMINA_TEACHER_EMAIL": "t@x.com", "LUMINA_TEACHER_PASSWORD": "x",
                "LUMINA_STUDENT_EMAIL": "s@x.com", "LUMINA_STUDENT_PASSWORD": "x",
                "LUMINA_ADMIN_EMAIL": "a@x.com", "LUMINA_ADMIN_PASSWORD": "x"}
    gate([PROXY_CMD, str(SCRIPTS / "smoke_test.py"), *smoke_dry], "4. 冒烟结构自检(dry)", env=dry_envs)

    if args.live:
        # Windows 下 localhost 每次连接 ~2s：冒烟/压测统一用 127.0.0.1
        base_host = args.base.replace("localhost", "127.0.0.1") if "localhost" in args.base else args.base
        if base_host != args.base:
            print(f"ℹ base {args.base} → {base_host}（Windows localhost 解析慢）")
        # live 冒烟需要真实账号：dry-run 的假值不能用于真实登录，
        # 必须由环境变量提供（演示账号见 seed_demo.py：*@lumina.edu / Demo@2026）。
        live_envs = dict(os.environ)
        for k in ("LUMINA_TEACHER_EMAIL", "LUMINA_TEACHER_PASSWORD",
                  "LUMINA_STUDENT_EMAIL", "LUMINA_STUDENT_PASSWORD",
                  "LUMINA_ADMIN_EMAIL", "LUMINA_ADMIN_PASSWORD"):
            if not live_envs.get(k):
                print(f"⚠ 未设置 {k}（冒烟登录可能 401，演示账号默认 Demo@2026）")
        smoke_live = ["--base", base_host]
        if args.ai:
            smoke_live.append("--ai")
        gate([PROXY_CMD, str(SCRIPTS / "smoke_test.py"), *smoke_live], "5. 冒烟(live)", env=live_envs)
        gate([PROXY_CMD, str(SCRIPTS / "run_tests.py"), "--include-api", "--python", PROXY_CMD],
             "6. 集成测试(含 skip)")
        gate([PROXY_CMD, str(SCRIPTS / "load_test.py"), "--base", base_host, "--concurrency", "20", "--total", "200"],
             "7. 性能压测(/health)")

    # ── 汇总 ──
    print(f"\n{'='*60}")
    for label, ok in results:
        print(f"{'✅' if ok else '❌'} {label}")
    print(f"\n通过 {passed}/{total}")
    if passed < total:
        print("❌ 存在失败门禁，请查看上方日志")
        return 1
    print("🎉 阶段三质量门禁全部通过（离线模式）" if not args.live else "🎉 阶段三验证完成（含真实联调）")
    return 0


if __name__ == "__main__":
    sys.exit(main())