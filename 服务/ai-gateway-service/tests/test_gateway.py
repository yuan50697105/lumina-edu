# ============================================
# Lumina 墨光 · AI 网关 单元测试
# Schema 校验 / 配额判断（无需数据库）
# ============================================
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.routers.ai_gateway import _quota_ok
from app.schemas import ModelCreate, ProviderCreate, RouteRequest


class FakeProvider:
    def __init__(self, quota=Decimal("0"), used=Decimal("0")):
        self.monthly_quota = quota
        self.used_quota = used


class TestSchema:
    def test_provider_name_pattern(self):
        ProviderCreate(name="qwen", display_name="通义千问")
        ProviderCreate(name="glm-4x", display_name="智谱")
        with pytest.raises(Exception):
            ProviderCreate(name="Bad Name!", display_name="非法")

    def test_model_create(self):
        m = ModelCreate(
            provider_name="qwen", model_name="qwen-max",
            display_name="通义千问 Max", task_types=["chat", "generate"],
            priority=10, cost_per_1k_tokens=Decimal("0.02"),
        )
        assert m.max_tokens == 4096
        assert m.openai_compatible is True

    def test_model_task_types_required(self):
        with pytest.raises(Exception):
            ModelCreate(provider_name="qwen", model_name="x", display_name="x", task_types=None)

    def test_route_task_type_valid(self):
        for t in ["chat", "grade", "generate", "vl", "speech"]:
            RouteRequest(task_type=t)
        with pytest.raises(Exception):
            RouteRequest(task_type="image_gen")


class TestQuota:
    def test_unlimited_ok(self):
        assert _quota_ok(FakeProvider(Decimal("0"), Decimal("0"))) is True

    def test_under_quota_ok(self):
        assert _quota_ok(FakeProvider(Decimal("100"), Decimal("50"))) is True

    def test_at_quota_blocked(self):
        assert _quota_ok(FakeProvider(Decimal("100"), Decimal("100"))) is False

    def test_over_quota_blocked(self):
        assert _quota_ok(FakeProvider(Decimal("100"), Decimal("150"))) is False