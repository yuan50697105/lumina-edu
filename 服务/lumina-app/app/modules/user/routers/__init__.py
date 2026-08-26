# routers 子目录（user-service 使用 auth.py + users.py）
from ..routers_auth import router as auth_router
from ..routers_users import router as users_router

__all__ = ["auth_router", "users_router"]
