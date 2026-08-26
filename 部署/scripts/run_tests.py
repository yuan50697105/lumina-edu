#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================
# Lumina 墨光 · 统一单元测试运行器（WBS 2.13）
# --------------------------------------------
# 一键运行全部服务的纯单元测试（不碰数据库），并附带契约核对。
#   * 默认跳过 *_api.py 集成测试（它们需要 PostgreSQL）；
#   * --include-api 可一并运行（PG 未就绪时自动 skip，不失败）。
# 用法：
#   python 部署/scripts/run_tests.py
#   python 部署/scripts/run_tests.py --include-api --python 服务/user-service/.venv/Scripts/python.exe
# ============================================
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SVC = ROOT / "服务"
SUMMARY_RE = re.compile(r"(?P<passed>\d+) passed(?:, (?P<failed>\d+) failed)?(?:, (?P<skipped>\d+) skipped)?")


def pick_python(explicit: str | None) -> str:
    if explicit:
        return explicit
    # venv 探测：user-service/.venv
    for s in SVC.iterdir():
        p = s / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        if p.exists():
            return str(p)
    return sys.executable


def run(py: str, file: Path) -> tuple[bool, dict]:
    cmd = [py, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(file)]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    last = [ln for ln in out.splitlines() if len(ln) < 120][-1:] or [""]
    m = SUMMARY_RE.search(out)
    stats = {
        "passed": int(m.group("passed")) if m and m.group("passed") else 0,
        "failed": int(m.group("failed")) if m and m.group("failed") else 0,
        "skipped": int(m.group("skipped")) if m and m.group("skipped") else 0,
    }
    if proc.returncode != 0 and not stats["failed"]:
        stats["failed"] = 1                     # 收集/语法错误等
    return proc.returncode == 0, stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", default=None, help="Python 解释器路径（默认探测 .venv）")
    ap.add_argument("--include-api", action="store_true", help="同时运行 *_api.py 集成测试（缺 DB 自动 skip）")
    ap.add_argument("--exclude", nargs="*", default=[], help="跳过某服务目录（如 user-service）")
    args = ap.parse_args()

    py = pick_python(args.python)
    print(f"🔍 Python: {py}\n")

    files = sorted(p for p in SVC.glob("*/tests/test_*.py"))
    if not args.include_api:
        files = [f for f in files if not f.name.endswith("_api.py")]
    files = [f for f in files if not any(x in str(f) for x in args.exclude)]

    total = {"passed": 0, "failed": 0, "skipped": 0}
    failures = []
    for f in files:
        ok, stats = run(py, f)
        label = f.parent.parent.name + "/" + f.name
        mark = "✅" if ok else "❌"
        print(f"{mark} {label:46} pass={stats['passed']:>3} fail={stats['failed']:>3} skip={stats['skipped']:>3}")
        for k in total:
            total[k] += stats[k]
        if not ok:
            failures.append(label)

    # 附加静态契约核对（不可失败则单列报告）
    has_yaml = shutil.which("python") or True
    print("\n── 静态契约核对 ──")
    check = ROOT / "部署" / "scripts" / "api_contract_check.py"
    proc = subprocess.run([py, str(check)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    print("[契约]", "✅ 通过" if proc.returncode == 0 else "⚠ 有警告（见上面契约输出）")
    if proc.stdout:
        tail = [ln for ln in proc.stdout.splitlines() if "总数" in ln or "一致" in ln or "问题" in ln][-2:]
        for t in tail:
            print(f"       {t}")

    print(f"\n{'=' * 56}\n单元测试  passed={total['passed']}  failed={total['failed']}  skipped={total['skipped']}  (文件数 {len(files)})")
    if failures:
        print("❌ 失败文件：")
        for f in failures:
            print(f"   - {f}")
        return 1
    print("✅ 全部单元测试通过" + ("（含集成 skip 项）" if args.include_api else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())