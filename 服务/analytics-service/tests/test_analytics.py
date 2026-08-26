# ============================================
# Lumina 墨光 · 埋点收集服务单元测试
# 纯逻辑：身份解析 / 字段提升 / Schema 校验
# 无需 PostgreSQL / 无需鉴权服务
# ============================================
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pydantic import ValidationError

from app.routers import _cell_uuid, _resolve_user, _to_row
from app.schemas import EventBatch, EventIn


class _FakeRequest:
    """最小 Request 替身（只暴露收集逻辑所需字段）"""
    def __init__(self, headers=None, client=None):
        self.headers = headers or {}
        self.client = client

    def get(self):
        return self.client


def _req(bearer=None):
    h = {}
    if bearer:
        h["authorization"] = f"Bearer {bearer}"
    return _FakeRequest(h)


def make_access_token(sub: str) -> str:
    """用共享 JWT 密钥签发 access token（模拟登录用户）"""
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from app.config import settings
    return jwt.encode(
        {"sub": sub, "role": "student", "type": "access",
         "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
    )


class TestCellUuid:
    def test_valid(self):
        u = uuid.uuid4()
        assert _cell_uuid(str(u)) == u

    def test_invalid_returns_none(self):
        assert _cell_uuid("not-a-uuid") is None
        assert _cell_uuid("") is None
        assert _cell_uuid(None) is None
        assert _cell_uuid(123) is None


class TestResolveUser:
    def test_no_token_uses_client_id(self):
        cid = str(uuid.uuid4())
        ev = EventIn(event_name="page.view", user_id=cid)
        u = _resolve_user(_req(), ev)
        assert str(u) == cid

    def test_bogus_client_id_ignored(self):
        ev = EventIn(event_name="page.view", user_id="游客xyz")   # 非 UUID
        assert _resolve_user(_req(), ev) is None

    def test_valid_token_overrides_client_id(self):
        real = uuid.uuid4()
        ev = EventIn(event_name="page.view", user_id=str(uuid.uuid4()))  # 伪造的
        u = _resolve_user(_req(make_access_token(str(real))), ev)
        assert str(u) == str(real)   # JWT 为准

    def test_expired_token_falls_back(self):
        from datetime import datetime, timedelta, timezone
        from jose import jwt
        from app.config import settings
        expired = jwt.encode(
            {"sub": str(uuid.uuid4()), "type": "access",
             "exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
            settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
        )
        cid = str(uuid.uuid4())
        ev = EventIn(event_name="page.view", user_id=cid)
        assert str(_resolve_user(_req(expired), ev)) == cid


class TestToRow:
    def test_course_id_promoted_from_properties(self):
        cid = str(uuid.uuid4())
        ev = EventIn(event_name="course.view", user_id=None,
                     properties={"course_id": cid, "source": "web"})
        row = _to_row(_req(), ev, None)
        assert str(row.course_id) == cid        # 提升为列
        assert row.properties == {"source": "web"}   # 从 properties 移除

    def test_invalid_props_course_not_promoted(self):
        ev = EventIn(event_name="course.view", properties={"course_id": "bad"})
        row = _to_row(_req(), ev, None)
        assert row.course_id is None
        assert row.properties == {"course_id": "bad"}

    def test_collects_meta(self):
        req = _FakeRequest({"user-agent": "Mozilla/5.0", "x-forwarded-for": "1.2.3.4, 5.6.7.8"})
        ev = EventIn(event_name="page.view")
        row = _to_row(req, ev, None)
        assert row.user_agent == "Mozilla/5.0"
        assert row.ip_address == "1.2.3.4"
        assert row.properties is None


class TestSchema:
    def test_event_name_required(self):
        with pytest.raises(ValidationError):
            EventIn(event_name="")

    def test_event_name_too_long(self):
        with pytest.raises(ValidationError):
            EventIn(event_name="x" * 101)

    def test_page_url_capped(self):
        with pytest.raises(ValidationError):
            EventIn(event_name="p", page_url="u" * 501)

    def test_batch_bounds(self):
        with pytest.raises(ValidationError):
            EventBatch(events=[])
        with pytest.raises(ValidationError):
            EventBatch(events=[EventIn(event_name="x")] * 101)

    def test_batch_valid(self):
        b = EventBatch(events=[EventIn(event_name="page.view"),
                               EventIn(event_name="element.click", properties={"label": "登录"})])
        assert len(b.events) == 2