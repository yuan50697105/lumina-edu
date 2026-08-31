# ============================================
# Lumina 墨光 · HLS 反代与流地址单元测试
# 覆盖：
#   app.modules.live.routers._stream_url 三种模式（mock / HLS 直连 / 同源反代）
#   app.media_proxy 反代转发（附加 cookieCheck、透传资源、URL 正确拼接）
# 纯内存断言，不连数据库、不发起真实网络请求
# ============================================
import asyncio
import uuid

import httpx
from fastapi import Request

from app import media_proxy as mp
from app.config import settings
from app.models import LiveRoom
from app.modules.live.routers import _stream_url


class TestStreamUrl:
    """stream_url 模式：无媒体服务器 → mock 占位；有 base → HLS；proxy → 同源相对"""

    def _room(self, status="live", stream_key="roomdemo"):
        return LiveRoom(id=uuid.uuid4(), stream_key=stream_key, status=status)

    def test_no_base_mock_placeholder(self, monkeypatch):
        """未配置媒体服务器：返回 mock:// 占位（保持原契约）"""
        monkeypatch.setattr(settings, "LIVE_STREAM_BASE", "")
        assert _stream_url(self._room()) == "mock://live/roomdemo"

    def test_no_base_fallback_to_room_id(self, monkeypatch):
        """无 stream_key 时回退房间 id"""
        monkeypatch.setattr(settings, "LIVE_STREAM_BASE", "")
        rid = uuid.uuid4()
        assert _stream_url(LiveRoom(id=rid, status="live")) == f"mock://live/{rid}"

    def test_base_generates_hls_layout(self, monkeypatch):
        """配置媒体服务器根：输出 {base}/{key}/index.m3u8（mediamtx / Nginx-HLS 布局）"""
        monkeypatch.setattr(settings, "LIVE_STREAM_BASE", "http://127.0.0.1:8888/live")
        monkeypatch.setattr(settings, "LIVE_STREAM_PROXY", False)
        assert _stream_url(self._room()) == "http://127.0.0.1:8888/live/roomdemo/index.m3u8"

    def test_proxy_returns_relative_media_url(self, monkeypatch):
        """开发演示反代：返回同源 /media/ 相对地址"""
        monkeypatch.setattr(settings, "LIVE_STREAM_BASE", "http://127.0.0.1:8888/live")
        monkeypatch.setattr(settings, "LIVE_STREAM_PROXY", True)
        assert _stream_url(self._room()) == "/media/roomdemo/index.m3u8"

    def test_not_live_returns_none(self, monkeypatch):
        """未开播不返回播放地址"""
        monkeypatch.setattr(settings, "LIVE_STREAM_BASE", "http://127.0.0.1:8888/live")
        assert _stream_url(self._room(status="scheduled")) is None


# ─── media_proxy 反代 ───

class _FakeResponse:
    status_code = 200
    headers = {"content-type": "application/vnd.apple.mpegurl", "content-length": "100"}
    content = b"#EXTM3U\n#EXT-X-VERSION:3\n"

    def raise_for_status(self):
        pass


def _make_request(query: bytes = b""):
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/media/roomdemo/index.m3u8",
        "raw_path": b"/media/roomdemo/index.m3u8",
        "query_string": query,
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "scheme": "http",
        "root_path": "",
        "state": {},
    }
    return Request(scope)


class TestMediaProxy:
    def test_forwards_to_base_with_cookie_check(self, monkeypatch):
        """目标 URL 拼接正确，且附加 mediamtx cookieCheck 放行参数"""
        captured = {}

        class _FakeClient:
            def __init__(self, *a, **kw):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

            async def get(self, url, **kw):
                captured["url"] = url
                captured["params"] = kw.get("params")
                return _FakeResponse()

        monkeypatch.setattr(settings, "LIVE_STREAM_BASE", "http://127.0.0.1:8888/live")
        monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)

        resp = asyncio.run(mp.media_proxy("roomdemo/index.m3u8", _make_request()))

        assert resp.status_code == 200
        assert resp.body == _FakeResponse.content
        assert captured["url"] == "http://127.0.0.1:8888/live/roomdemo/index.m3u8"
        assert captured["params"]["cookieCheck"] == "1"

    def test_preserves_query_and_forwards_range(self, monkeypatch):
        """保留原 query（LL-HLS session 等）并透传 Range 请求头"""
        captured = {}

        class _FakeClient:
            def __init__(self, *a, **kw):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

            async def get(self, url, **kw):
                captured["url"] = url
                captured["params"] = kw.get("params")
                captured["headers"] = kw.get("headers")
                return _FakeResponse()

        monkeypatch.setattr(settings, "LIVE_STREAM_BASE", "http://127.0.0.1:8888/live")
        monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)

        scope = {
            "type": "http", "method": "GET",
            "path": "/media/roomdemo/main_stream.m3u8",
            "raw_path": b"/media/roomdemo/main_stream.m3u8",
            "query_string": b"session=abc",
            "headers": [(b"range", b"bytes=0-100")],
            "client": ("127.0.0.1", 12345), "server": ("test", 80),
            "scheme": "http", "root_path": "", "state": {},
        }
        resp = asyncio.run(mp.media_proxy("roomdemo/main_stream.m3u8", Request(scope)))

        assert resp.status_code == 200
        assert captured["params"].get("session") == "abc"
        assert captured["params"]["cookieCheck"] == "1"
        assert captured["headers"].get("range") == "bytes=0-100"

    def test_rejects_path_traversal(self, monkeypatch):
        """拒绝 ../ 越界路径"""
        monkeypatch.setattr(settings, "LIVE_STREAM_BASE", "http://127.0.0.1:8888/live")
        resp = asyncio.run(mp.media_proxy("../../etc/passwd", _make_request()))
        assert resp.status_code == 400

    def test_503_when_no_base(self, monkeypatch):
        """未配置媒体服务器时返回 503"""
        monkeypatch.setattr(settings, "LIVE_STREAM_BASE", "")
        resp = asyncio.run(mp.media_proxy("roomdemo/index.m3u8", _make_request()))
        assert resp.status_code == 503