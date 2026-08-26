# ============================================
# Lumina 墨光 · 用户服务 监控埋点模块单测
# 纯逻辑测试：Instrumentation（track/log_api）/ Timer
# 用 FakeDB / FakeRequest，不触数据库
# ============================================
import os
import sys
import uuid
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app import instrumentation as instr
from app.instrumentation import Instrumentation, Timer


class FakeDB:
    """记录 add 对象 + commit/rollback 次数的假会话"""

    def __init__(self, fail_commit: bool = False):
        self.added = []
        self.commit_calls = 0
        self.rollback_calls = 0
        self.fail_commit = fail_commit

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commit_calls += 1
        if self.fail_commit:
            raise RuntimeError("db down")

    def rollback(self):
        self.rollback_calls += 1


def make_request(**headers):
    return SimpleNamespace(
        client=None,
        headers=headers,
        url="http://lumina.test/api/v1/courses",
    )


# ─── Instrumentation ───
class TestInstrumentationInit:
    def test_request_id_generated_with_request(self):
        req = make_request()
        ins = Instrumentation(FakeDB(), req, "u-1")
        assert ins.request_id is not None
        # 每次请求独立 request_id
        ins2 = Instrumentation(FakeDB(), req, "u-1")
        assert ins2.request_id != ins.request_id

    def test_no_request_means_no_request_id(self):
        ins = Instrumentation(FakeDB())
        assert ins.request_id is None

    def test_user_id_passed_through(self):
        ins = Instrumentation(FakeDB(), user_id="u-42")
        assert ins.user_id == "u-42"


class TestTrack:
    def test_basic_event_attributes(self):
        db = FakeDB()
        req = make_request(**{"user-agent": "smoke", "session_id": "sess-9"})
        ins = Instrumentation(db, req, "u-1")
        ins.track("user.view", course_id="c-1", uri="/me")
        assert len(db.added) == 1
        ev = db.added[0]
        assert ev.event_name == "user.view"
        assert ev.user_id == "u-1"
        assert ev.session_id == "sess-9"
        assert ev.course_id == "c-1"
        assert ev.properties == {"uri": "/me"}
        assert ev.page_url == "http://lumina.test/api/v1/courses"
        assert ev.user_agent == "smoke"
        assert ev.ip_address is None
        assert db.commit_calls == 1

    def test_properties_override_user_id_and_session(self):
        db = FakeDB()
        ins = Instrumentation(db, make_request(), "u-ins")
        ins.track("user.login", user_id="u-ext", session_id="s-ext")
        ev = db.added[0]
        assert ev.user_id == "u-ext"
        assert ev.session_id == "s-ext"
        assert ev.properties is None          # 全部被提升字段消费 → 无冗余

    def test_no_request_defaults_to_none(self):
        db = FakeDB()
        ins = Instrumentation(db)
        ins.track("user.login")
        ev = db.added[0]
        assert ev.user_id is None
        assert ev.session_id is None
        assert ev.page_url is None
        assert ev.user_agent is None

    def test_commit_failure_rolls_back(self):
        db = FakeDB(fail_commit=True)
        ins = Instrumentation(db)
        ins.track("user.login")               # 不应抛异常
        assert db.rollback_calls == 1
        assert db.commit_calls == 1

    def test_event_names_use_namespace_convention(self):
        assert instr.EVENT_LOGIN == "user.login"
        assert instr.EVENT_LOGIN_FAIL == "user.login_fail"
        assert instr.EVENT_PROFILE_UPDATE == "user.profile_update"
        assert instr.EVENT_USER_VIEW == "user.view"
        for name in (
            instr.EVENT_LOGIN, instr.EVENT_REGISTER, instr.EVENT_LOGOUT,
            instr.EVENT_TOKEN_REFRESH, instr.EVENT_PASSWORD_CHANGE,
        ):
            assert name.startswith("user.") and " " not in name


class TestLogApi:
    def test_log_api_writes_shared_fields(self):
        db = FakeDB()
        req = make_request()
        ins = Instrumentation(db, req, "u-7")
        ins.request_id = "REQ-abc"
        ins.log_api("POST", "/api/v1/courses", 201, 123, error_message=None)
        assert len(db.added) == 1
        log = db.added[0]
        assert log.method == "POST"
        assert log.path == "/api/v1/courses"
        assert log.status_code == 201
        assert log.duration_ms == 123
        assert log.user_id == "u-7"
        assert log.request_id == "REQ-abc"
        assert log.error_message is None

    def test_log_api_error_message_kept(self):
        db = FakeDB()
        ins = Instrumentation(db, user_id="u-7")
        ins.log_api("GET", "/x", 500, 9000, error_message="boom")
        assert db.added[0].error_message == "boom"

    def test_log_api_failure_rolls_back(self):
        db = FakeDB(fail_commit=True)
        ins = Instrumentation(db)
        ins.log_api("GET", "/x", 200, 5)      # 不应抛异常
        assert db.rollback_calls == 1


# ─── Timer ───
class FakeClock:
    def __init__(self):
        self.t = 1.0

    def __call__(self):
        return self.t


class TestTimer:
    def test_duration_ms_computed_on_exit(self, monkeypatch):
        clock = FakeClock()
        monkeypatch.setattr(instr.time, "perf_counter", clock)
        with Timer() as tm:
            clock.t = 2.5                     # 经过 1.5s
        assert tm.duration_ms == 1500

    def test_instant_exit_zero(self, monkeypatch):
        clock = FakeClock()
        monkeypatch.setattr(instr.time, "perf_counter", clock)
        with Timer() as tm:
            pass                              # 未耗时
        assert tm.duration_ms == 0

    def test_exception_still_measures(self, monkeypatch):
        clock = FakeClock()
        monkeypatch.setattr(instr.time, "perf_counter", clock)
        with pytest.raises(ValueError):
            with Timer() as tm:
                clock.t = 1.25
                raise ValueError("boom")
        assert tm.duration_ms == 250