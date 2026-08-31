# ============================================
# Lumina 墨光 · OpenAPI 生成单元测试
# 回归：app.openapi() 抛 TypeAdapter not fully defined 的修复验证
# 说明：openapi 仅靠 schema 生成，不连数据库
# ============================================
from app.main import app


def test_openapi_generates():
    """openapi() 生成成功且包含全部业务端点"""
    spec = app.openapi()
    assert len(spec["paths"]) >= 44
    # 认证登录端点必须存在
    assert "/api/v1/auth/login" in spec["paths"]