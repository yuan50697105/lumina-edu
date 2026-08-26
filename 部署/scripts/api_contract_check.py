#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================
# Lumina 墨光 · API 契约核对工具（WBS 2.12）
# --------------------------------------------
# 静态核对三层契约一致性，**不需要启动任何服务**：
#   前端调用 URL  ⊂  后端服务端点  ⊂  Nginx 路由(端口/服务)
# 用法：
#   python 部署/scripts/api_contract_check.py
# 输出：联调矩阵 + 未闭合项清单（exit 1 表示存在可修复的缺口）
# ============================================
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # edu/
SVC = ROOT / "服务"
NGINX_CONF = ROOT / "部署" / "config" / "nginx" / "conf.d" / "lumina.conf"
COMPOSE = ROOT / "部署" / "docker-compose.yml"
WEB_SRC = SVC / "web-frontend" / "src"

problems: list[str] = []
warnings: list[str] = []


# ─── 1. 提取后端端点 ───
ROUTER_DEF = re.compile(r'([a-zA-Z_]\w*)\s*=\s*APIRouter\(([^)]*)\)')
ENDPOINT = re.compile(
    r'@([a-zA-Z_]\w*)\.(get|post|patch|delete|put)\("([^"]*)"'
)
INCLUDE = re.compile(r'include_router\(([A-Za-z_][\w.]*),\s*prefix="([^"]+)"')


def _router_prefix(sig: str) -> str:
    m = re.search(r'prefix="([^"]*)"', sig)
    return m.group(1) if m else ""


def collect_backend_endpoints() -> dict[str, set[str]]:
    """返回 {服务名: {完整端点路径}}。尽力而为：解析 decorator 到 include 拼路径。"""
    result: dict[str, set[str]] = {}

    def _find_router_file(sdir: Path, parts: list[str]) -> Path | None:
        """定位 include 引用变量所在的 .py：优先 父名同名文件，回退 routers.py"""
        if len(parts) == 2:                       # grades.course_router
            cand = sdir / "app" / "routers" / f"{parts[0]}.py"
            if cand.exists():
                return cand
            cand = sdir / "app" / f"{parts[0]}.py"
            if cand.exists():
                return cand
        cand = sdir / "app" / "routers.py"        # 单文件别名（router as chat_router）
        return cand if cand.exists() else None

    def _module_routes(file: Path) -> dict[str, dict]:
        """file 内所有 router 变量 → {'prefix':.., 'endpoints':[{method,path}]}"""
        text = file.read_text(encoding="utf-8")
        mods: dict[str, dict] = {}
        for var, sig in ROUTER_DEF.findall(text):
            mods.setdefault(var, {"prefix": _router_prefix(sig), "endpoints": []})
        for var, method, path in ENDPOINT.findall(text):
            mods.setdefault(var, {"prefix": "", "endpoints": []})
            mods[var]["endpoints"].append((method.upper(), path))
        return mods

    for sdir in sorted(SVC.iterdir()):
        main = sdir / "app" / "main.py"
        if not main.exists():
            continue
        main_text = main.read_text(encoding="utf-8")
        for inc_path, inc_prefix in INCLUDE.findall(main_text):
            parts = inc_path.split(".")
            var = parts[-1]
            rfile = _find_router_file(sdir, parts)
            if rfile is None:
                warnings.append(f"{sdir.name} 找不到 {inc_path} 的路由文件")
                continue
            mods = _module_routes(rfile)
            mod = mods.get(var)
            if mod is None and len(parts) == 1:
                # 单段别名（from .routers import router as chat_router）→ 取 router 或唯一定义
                mod = mods.get("router") or (next(iter(mods.values()), None))
            if mod is None:
                warnings.append(f"{sdir.name}/{rfile.name} 未定义 router 变量 {var}")
                continue
            for method, path in mod["endpoints"]:
                full = f"{inc_prefix}{mod['prefix']}{path}" or "/"
                result.setdefault(sdir.name, set()).add(f"{method} {full}")
    return result


# ─── 2. 提取 Nginx 路由 → 端口/服务 ───
def collect_nginx_routes():
    text = NGINX_CONF.read_text(encoding="utf-8")
    regex_locs, prefix_locs = [], []
    for block in re.finditer(
        r"location\s+(?:(~+)\s+)?(\S+)\s*\{(.*?)\}", text, re.S
    ):
        tilde = block.group(1)
        patt = block.group(2)
        body = block.group(3)
        m = re.search(r"proxy_pass\s+http://([\w.-]+)", body)
        if not m:
            continue
        upstream = m.group(1)
        if tilde:                                    # 正则 location（~ 或 ~*）
            regex_locs.append((patt[1:-1] if patt.startswith('"') else patt, upstream))
        else:                                        # 前缀 location
            prefix_locs.append((patt, upstream))
    return regex_locs, prefix_locs


def nginx_upstream(path: str, regex_locs, prefix_locs) -> str | None:
    """模拟 Nginx：正则先于前缀；前缀取最长匹配"""
    for patt, upstream in regex_locs:                  # 按定义顺序
        if re.match(patt, path):
            return upstream
    best = None
    for patt, upstream in prefix_locs:
        if path.startswith(patt) and (best is None or len(patt) > len(best[0])):
            best = (patt, upstream)
    return best[1] if best else None


def _norm(path: str) -> str:
    """路径变量归一：/{course_id} 与 {} 与 /{id} 视为同形"""
    return re.sub(r"\{[^}]*\}", "{}", path)


# ─── 3. 提取前端调用 URL（泛型参数可选，如 get<Course> 与 patch( 均覆盖）───
CALL = re.compile(
    r"\b(get|post|patch|del)\b\s*(?:<[^>]*>)?\(\s*[`'\"]([^`'\"]+)[`'\"]"
)
FETCH = re.compile(r"fetch\(\s*[`'\"]([^`'\"]+)[`'\"]")


def collect_frontend_urls() -> set[str]:
    urls = set()
    for py in list(WEB_SRC.rglob("*.ts")) + list(WEB_SRC.rglob("*.tsx")):
        if "client.ts" in str(py) or "tracker.ts" in str(py):
            continue
        text = py.read_text(encoding="utf-8")
        for _, u in CALL.findall(text):
            urls.add(u)
        for u in FETCH.findall(text):
            if u.startswith("/api/"):
                urls.add(u)
    norm = set()
    for u in urls:
        u = re.sub(r"\$\{[^}]+\}|\{[^}]*\}", "{}", u)     # 变量归一
        if not u.startswith("/api/"):
            u = "/api/v1" + u
        norm.add(u.split("?")[0])
    return norm


def compose_service_names() -> set[str] | None:
    try:
        import yaml
        data = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
        return set(data.get("services", {})) if data else None
    except Exception:
        return None


# ─── 主流程 ───
def main() -> int:
    backend = collect_backend_endpoints()
    all_endpoints = set()
    for svc, eps in backend.items():
        for ep in eps:
            all_endpoints.add(ep.split(" ", 1)[1])
    regex_locs, prefix_locs = collect_nginx_routes()
    frontend = collect_frontend_urls()
    comp_services = compose_service_names()

    # 3.1 前端 URL 必须能路由到后端端点
    for url in sorted(frontend):
        upstream = nginx_upstream(url, regex_locs, prefix_locs)
        svc_eps = backend.get(f"{upstream}-service") or backend.get(upstream, set())
        reachable = any(_norm(p) == _norm(url) for _, p in (e.split(" ", 1) for e in svc_eps))
        status = "✓" if reachable else "✗ 端点缺失" if upstream else "✗ 无 Nginx 路由"
        print(f"{status:12} 前端 {url:48} → {upstream or '?'}")
        if upstream is None:
            problems.append(f"前端 {url} 无 Nginx 路由")
        elif not reachable:
            problems.append(f"前端 {url} 未命中后端端点（Nginx → {upstream}）")

    # 3.2 后端每个端点必须有 Nginx 路由（公共端点除外）
    print("\n── 后端端点 → Nginx 覆盖 ──")
    for svc, eps in sorted(backend.items()):
        for ep in sorted(eps):
            method, path = ep.split(" ", 1)
            upstream = nginx_upstream(path, regex_locs, prefix_locs)
            msg = f"{svc:20} {ep:52} → {upstream}"
            ok = upstream is not None and upstream.endswith(svc)
            print(f"{'✓' if ok else '⚠' if upstream else '✗'}  {msg}")
            if upstream is None:
                problems.append(f"后端 {svc} {ep} 无 Nginx 路由")

    # 3.3 Nginx upstream 须存在于 compose
    if comp_services:
        bad_ups = []
        seen = set()
        for _, up in regex_locs + prefix_locs:
            if up in seen:
                continue
            seen.add(up)
            if up not in comp_services:
                bad_ups.append(up)
        if bad_ups:
            problems.append(f"Nginx upstream 不在 compose 中: {bad_ups}")

    print(f"\n前端调用总数: {len(frontend)} | 后端端点总数: {len(all_endpoints)}")
    for w in warnings:
        print(f"[警告] {w}")
    if problems:
        print(f"\n❌ 发现 {len(problems)} 个契约问题：")
        for p in problems:
            print(f"   - {p}")
        return 1
    print("\n✅ 三层契约一致，无未闭合项")
    return 0


if __name__ == "__main__":
    sys.exit(main())