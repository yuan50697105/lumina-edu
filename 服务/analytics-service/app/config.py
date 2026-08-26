# ============================================
# Lumina 墨光 · 埋点收集服务配置
# ============================================
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，从环境变量读取"""

    APP_NAME: str = "lumina-analytics"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    DATABASE_URL: str = "postgresql://lumina:lumina_secure_password@localhost:5432/lumina"

    JWT_SECRET_KEY: str = "change_me_jwt_secret_key"
    JWT_ALGORITHM: str = "HS256"

    # 收集端点允许的跨域来源（comma 分隔；beacon/fetch 同源场景可留空）
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()