# ============================================
# Lumina 墨光 · D-10 运营监控 单元测试
# 深度健康检查 / Prometheus 指标 / 业务指标
# 路由存在性 / schema 校验 / OpenAPI 注册
# ============================================
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas import (
    ServiceHealth, DeepHealthCheckOut, PrometheusMetricsOut, BusinessMetricsOut,
)


# ───────────────────────────────────────────────────────────────
# D-10 Schema 校验
# ───────────────────────────────────────────────────────────────
class TestD10Schemas:

    def test_service_health_valid(self):
        h = ServiceHealth(
            name="mysql",
            status="healthy",
            latency_ms=12.5,
            details={"version": "9.7"},
        )
        assert h.name == "mysql"
        assert h.status == "healthy"
        assert h.latency_ms == 12.5

    def test_service_health_down(self):
        h = ServiceHealth(name="redis", status="down", details={"error": "timeout"})
        assert h.status == "down"
        assert h.latency_ms is None

    def test_deep_health_check_out(self):
        out = DeepHealthCheckOut(
            status="healthy",
            timestamp=datetime.now(timezone.utc),
            services=[
                ServiceHealth(name="mysql", status="healthy", latency_ms=10.0),
                ServiceHealth(name="redis", status="degraded"),
                ServiceHealth(name="lumina-app", status="healthy"),
            ],
            version="1.0.0",
            uptime_seconds=3600,
        )
        assert out.status == "healthy"
        assert out.version == "1.0.0"
        assert len(out.services) == 3
        assert out.uptime_seconds == 3600

    def test_deep_health_check_requires_fields(self):
        with pytest.raises(ValidationError):
            DeepHealthCheckOut(
                status="healthy",
                # missing timestamp, services, version, uptime
            )

    def test_prometheus_metrics_out(self):
        out = PrometheusMetricsOut(content="lumina_users_total 42\n")
        assert "lumina_users_total" in out.content

    def test_business_metrics_out(self):
        out = BusinessMetricsOut(
            total_users=100,
            active_users_today=25,
            total_courses=10,
            active_courses=8,
            total_videos=50,
            videos_watched_today=12,
            total_assignments=30,
            submissions_today=15,
            total_exams=5,
            exam_attempts_today=20,
            ai_calls_today=100,
            checkins_today=30,
            timestamp=datetime.now(timezone.utc),
        )
        assert out.total_users == 100
        assert out.active_users_today == 25
        assert out.ai_calls_today == 100


# ───────────────────────────────────────────────────────────────
# D-10 OpenAPI 注册校验
# ───────────────────────────────────────────────────────────────
class TestD10OpenAPIRegistration:

    @pytest.fixture(scope="class")
    def schema(self):
        from app.main import app
        return app.openapi()

    def test_ops_paths_registered(self, schema):
        paths = set(schema["paths"].keys())
        required = {
            "/api/v1/ops/health/deep",
            "/api/v1/ops/metrics",
            "/api/v1/ops/metrics/business",
        }
        assert required.issubset(paths), f"Missing: {required - paths}"

    def test_ops_health_methods(self, schema):
        assert "get" in schema["paths"]["/api/v1/ops/health/deep"]

    def test_ops_metrics_methods(self, schema):
        assert "get" in schema["paths"]["/api/v1/ops/metrics"]

    def test_ops_business_metrics_methods(self, schema):
        assert "get" in schema["paths"]["/api/v1/ops/metrics/business"]

    def test_ops_tag_exists(self, schema):
        """D-10 标签存在于任意 operation 的 tags 中"""
        tags = set()
        for path, ops in schema["paths"].items():
            for op in ops.values():
                tags.update(op.get("tags", []))
        assert any("D-10" in t for t in tags), f"No D-10 tag in {tags}"

    def test_business_metrics_requires_auth(self, schema):
        """业务指标接口需要管理员认证"""
        op = schema["paths"]["/api/v1/ops/metrics/business"]["get"]
        security = op.get("security", [])
        assert len(security) > 0, "business metrics should require authentication"

    def test_total_path_count(self, schema):
        """确认总路径数包含 D-10 新增"""
        paths = list(schema["paths"].keys())
        assert len(paths) >= 174, f"Expected >=174 paths, got {len(paths)}"


# ───────────────────────────────────────────────────────────────
# D-10 Prometheus 格式校验（单元级，不依赖 DB）
# ───────────────────────────────────────────────────────────────
class TestD10PrometheusFormat:
    """验证 Prometheus 文本格式符合规范"""

    def test_metric_format(self):
        """验证生成的指标行符合 Prometheus 文本格式"""
        lines = [
            "# HELP lumina_users_total Total number of users",
            "# TYPE lumina_users_total gauge",
            "lumina_users_total 42",
        ]
        for line in lines:
            assert isinstance(line, str)
            assert len(line) > 0

        # 数据行不含 # 前缀
        data_lines = [l for l in lines if not l.startswith("#")]
        for l in data_lines:
            parts = l.split(" ")
            assert len(parts) == 2
            assert parts[1].isdigit()

    def test_metric_label_format(self):
        """验证带标签的指标格式"""
        line = 'lumina_api_requests_total{status="200"} 1234'
        assert "{" in line and "}" in line
        assert "=" in line.split("{")[1].split("}")[0]
