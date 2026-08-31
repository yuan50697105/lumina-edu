#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================
# Lumina 墨光 · 轻量性能压测（阶段三 3.3 准备）
# --------------------------------------------
# 无第三方依赖：线程并发请求，统计吞吐/RPS/P99。
#   python 部署/scripts/load_test.py --base http://localhost --concurrency 20 --total 200 --endpoint /health
#   python 部署/scripts/load_test.py --sorted           # 打印延迟分布
# 基线建议：API 观测接口 < 200ms，突发 < 500ms。
# ============================================
import argparse
import statistics
import sys
import threading
import time
import urllib.request
from urllib.parse import urlparse, urlunparse

_lock = threading.Lock()
_lat: list[float] = []
_errors: list[str] = []


def worker(base: str, endpoint: str, total_per: int, token: str | None = None):
    for _ in range(total_per):
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(base + endpoint)
            req.add_header("User-Agent", "lumina-load-test")
            if token:
                req.add_header("Authorization", f"Bearer {token}")
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
            dur = (time.perf_counter() - t0) * 1000
            with _lock:
                _lat.append(dur)
            if status >= 500:
                with _lock:
                    _errors.append(f"{status}")
        except Exception as e:
            with _lock:
                _errors.append(str(e)[:60])


def pct(sorted_lat: list[float], p: float) -> float:
    if not sorted_lat:
        return 0.0
    idx = min(len(sorted_lat) - 1, int(len(sorted_lat) * p))
    return round(sorted_lat[idx], 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost", help="目标基础地址")
    ap.add_argument("--endpoint", default="/health", help="压测端点")
    ap.add_argument("--concurrency", type=int, default=20)
    ap.add_argument("--total", type=int, default=200, help="总请求数")
    ap.add_argument("--token", default=None, help="Bearer token（压登录后接口）")
    ap.add_argument("--sorted", action="store_true", help="打印延迟排序分布")
    args = ap.parse_args()

    # Windows 下 localhost 常走 IPv6/系统代理导致每次连接 ~2s：规范化为本机地址
    _u = urlparse(args.base)
    if _u.hostname in ("localhost", ""):
        _netloc = "127.0.0.1" + (f":{_u.port}" if _u.port else "")
        args.base = urlunparse((_u.scheme, _netloc, _u.path or "/", "", "", ""))
        print(f"ℹ localhost → {args.base}（Windows localhost 解析慢）")

    per = max(1, args.total // args.concurrency)
    threads = [threading.Thread(target=worker, args=(args.base, args.endpoint, per, args.token)) for _ in range(args.concurrency)]

    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.perf_counter() - t0

    lat = sorted(_lat)
    total = len(lat)
    errors = len(_errors)
    rps = total / wall if wall else 0.0

    print(f"\n压测 {args.base}{args.endpoint} · 并发 {args.concurrency} · 请求 {total}")
    print(f"总耗时 {wall:.2f}s · 吞吐 {rps:.0f} req/s · 错误 {errors}")
    print(f"p50 {pct(lat, .5)}ms · p90 {pct(lat, .9)}ms · p95 {pct(lat, .95)}ms · p99 {pct(lat, .99)}ms")
    if lat:
        print(f"min {lat[0]:.1f}ms · max {lat[-1]:.1f}ms · avg {statistics.mean(lat):.1f}ms")
    if errors:
        print(f"⚠ 错误样本（前 5）: {_errors[:5]}")
    if args.sorted:
        print("\n延迟排序：")
        print(" ".join(f"{v:.0f}" for v in lat))

    return 0 if errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())