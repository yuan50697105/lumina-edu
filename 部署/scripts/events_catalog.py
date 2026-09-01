#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================
# Lumina 墨光 · 埋点事件目录生成/校验（阶段三 3.2 准备）
# --------------------------------------------
# 扫描前后端全部埋点事件名，输出统一目录（部署/docs/events-catalog.md），
# 并校验命名规范（namespace.action）与前后端交集。
#   python 部署/scripts/events_catalog.py --check   # 违反规范即 exit 1
#   python 部署/scripts/events_catalog.py            # 只生成目录
# ============================================
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SVC = ROOT / "服务"
OUT = ROOT / "部署" / "docs" / "events-catalog.md"

# 允许的事件类型：后端事件常量 / 前端 track
EVENT_CONST = re.compile(r'EVENT_\w+\s*=\s*"([^"]+)"')
TRACK_LIT = re.compile(r"\btrack\(\s*['\"]([^'\"]+)['\"]")
TRACK_PAGE = re.compile(r"trackPageView\(\s*['\"]([^'\"]+)['\"]")
TRACK_CLICK = re.compile(r"trackClick\(\s*['\"]([^'\"]+)['\"]")

# 事件命名规范：namespace.action（点分，合法命名空间白名单）
ALLOW_NS = {
    "page", "element", "auth", "user", "course", "chapter", "assignment",
    "submission", "grade", "ai", "chat", "announcement", "enrollment",
    "provider", "model", "gateway", "conversation", "session", "system",
    "live", "collab", "notif", "exam",
}


def scan_text(text: str, track_only: bool = True) -> set[str]:
    names = set()
    if track_only:
        names.update(EVENT_CONST.findall(text))
        names.update(TRACK_LIT.findall(text))
    else:
        for pat in (EVENT_CONST, TRACK_LIT, TRACK_PAGE, TRACK_CLICK):
            names.update(pat.findall(text))
    return {n for n in names if n and not n.startswith("{")}


def scan_dir(base: Path, label: str, out: dict[str, set[str]]):
    if not base.exists():
        return
    for ext in ("*.py", "*.ts", "*.tsx"):
        for f in base.rglob(ext):
            try:
                text = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for n in scan_text(text):
                out.setdefault(n, set()).add(f"{label}:{f.relative_to(base).as_posix()}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="校验命名规范并返回退出码")
    args = ap.parse_args()

    events: dict[str, set[str]] = {}
    page_names: set[str] = set()
    # 前端：事件 + 页面视图/元素（页面名不算事件，单独统计）
    for f in list((SVC / "web-frontend" / "src").rglob("*.ts")) + list((SVC / "web-frontend" / "src").rglob("*.tsx")) + \
              list((SVC / "mobile-app" / "src").rglob("*.ts")) + list((SVC / "mobile-app" / "src").rglob("*.tsx")):
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        label = "web" if "web-frontend" in str(f) else "mobile"
        for n in scan_text(text, track_only=True):
            events.setdefault(n, set()).add(f"{label}:{f.relative_to(SVC).as_posix()}")
        page_names.update(TRACK_PAGE.findall(text))

    # 后端全部服务（app 内 track / EVENT_ 常量）
    for s in sorted(SVC.iterdir()):
        app_dir = s / "app"
        if app_dir.exists():
            scan_dir(app_dir, s.name, events)

    # 前端产生的业务事件（排除 SDK 自身调用）
    web_events = {n for n, src in events.items() if any("web" in s or "mobile" in s for s in src)}
    # 后端埋点常量：非前端标记的事件即属后端（单体化后服务为 lumina-app，按 web:/mobile: 前缀反推）
    backend_events = {n for n, src in events.items() if not any(("web:" in s or "mobile:" in s) for s in src)}

    lines = [
        "# Lumina 墨光 · 埋点事件目录",
        "",
        "> 自动生成：`python 部署/scripts/events_catalog.py`（阶段三 3.2 埋点数据验证依据）",
        "",
        "## 事件命名规范",
        "`namespace.action`（点分小写）；允许命名空间：" + ", ".join(sorted(ALLOW_NS)),
        "",
        "## 全量事件清单",
        "",
        "| 事件 | 端 | 出现位置 |",
        "|------|----|---------|",
    ]
    for n in sorted(events):
        src = sorted(events[n])
        ends = "/".join(sorted({("前端" if ("web:" in s or "mobile:" in s) else "后端") for s in src}))
        places = ", ".join(s.split(":", 1)[-1] for s in src[:3])
        lines.append(f"| `{n}` | {ends} | {places} |")

    lines += [
        "",
        "## 前端产生的业务事件（3.2 联调验证清单）",
        "",
    ]
    for n in sorted(web_events):
        lines.append(f"- `{n}`")
    lines += [
        "",
        "## 后端埋点常量（Instrumentation）",
        "",
    ]
    for n in sorted(backend_events):
        lines.append(f"- `{n}`")

    lines += [
        "",
        "## 前端页面视图覆盖（trackPageView 参数）",
        "",
    ]
    for n in sorted(page_names):
        lines.append(f"- `{n}`")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    total = len(events)
    print(f"已生成 {OUT.relative_to(ROOT)}（{total} 个事件，前端 {len(web_events)} / 后端常量 {len(backend_events)}）")

    # ── 命名规范校验 ──
    bad = []
    for n in events:
        parts = n.split(".", 1)
        if len(parts) != 2 or not parts[1] or parts[0] not in ALLOW_NS:
            bad.append(n)
    if bad:
        print(f"\n⚠ 命名不规范（{len(bad)}）：")
        for b in sorted(bad):
            print(f"   - {b}")

    only_front = web_events - backend_events
    only_back = backend_events - web_events
    print(f"前后端交集: {len(web_events & backend_events)}")
    if only_front:
        print(f"仅前端触发（后端无常量引用，允许——后端不强制枚举）: {len(only_front)}")
    if only_back:
        print(f"仅后端常量（前端未直接调用）: {len(only_back)}")

    if args.check and bad:
        print("\n❌ 埋点命名规范违反，exit 1")
        return 1
    if args.check:
        print("\n✅ 埋点命名规范全部合规")
    return (1 if bad else 0) if args.check else 0


if __name__ == "__main__":
    sys.exit(main())