# ============================================
# Lumina 墨光 · HLS 媒体反代（开发/演示同源代理）
# 解决本地媒体服务器（mediamtx）直连时的跨域 CORS 与 cookieCheck 校验问题：
# 前端播放 /media/... 同源地址，本模块转发到 LIVE_STREAM_BASE 目标并附加
# cookieCheck=1 参数直接放行（mediamtx 防 CDN 缓存合并的机制，见部署/stream）。
# 生产形态建议由 CDN / 网关把 /media → 媒体服务器 反代，语义一致。
#
# ⚠ 仅用于开发/演示：路径直接拼入上游 URL，未做白名单校验（已排除 ../ 越界）。
# ============================================
import logging

import httpx
from fastapi import APIRouter, Request, Response

from app.config import settings

logger = logging.getLogger("lumina.app")

router = APIRouter(prefix="/media", tags=["媒体流"])

# mediamtx 防缓存合并 cookie 校验：附带 cookieCheck=1 即放行（等价于已通过 302 挑战）
_COOKIE_CHECK = {"cookieCheck": "1"}


@router.get("/{path:path}", summary="HLS 媒体流反代（开发演示同源代理）")
async def media_proxy(path: str, request: Request):
    if not settings.LIVE_STREAM_BASE:
        return Response(status_code=503, content="LIVE_STREAM_BASE 未配置")
    if ".." in path:
        return Response(status_code=400, content="非法路径")

    target = f"{settings.LIVE_STREAM_BASE.rstrip('/')}/{path}"

    forward_headers = {}
    for header_name in ("range", "if-range", "origin"):
        value = request.headers.get(header_name)
        if value:
            forward_headers[header_name] = value

    # 保留原 query（如 LL-HLS session 参数），并附加 cookieCheck 放行
    params = dict(request.query_params)
    params.update(_COOKIE_CHECK)

    # HLS 资源（m3u8 / ts / mp4 分片）均为小程序，本地演示直接用同步缓冲转发，
    # 避免 httpx 流式响应在生成器迭代前 client 已关闭导致的 0 字节问题。
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            resp = await client.get(target, params=params, headers=forward_headers)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "application/octet-stream")
            out_headers = {
                "content-type": content_type,
                "cache-control": "no-cache",
                "accept-ranges": "bytes",
            }
            if resp.headers.get("content-length"):
                out_headers["content-length"] = resp.headers["content-length"]
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=out_headers,
                media_type=content_type,
            )
    except httpx.HTTPStatusError as exc:
        return Response(status_code=exc.response.status_code, content=exc.response.text[:500])
    except httpx.HTTPError as exc:
        logger.warning("HLS 反代失败 %s: %s", target, exc)
        return Response(status_code=502, content="媒体服务器不可达")