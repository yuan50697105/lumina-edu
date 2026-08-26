# ============================================
# Lumina 墨光 · 基础日志服务配置
# ============================================
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，从环境变量读取"""

    APP_NAME: str = "lumina-logs"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    DATABASE_URL: str = "postgresql://lumina:lumina_secure_password@localhost:5432/lumina"

    JWT_SECRET_KEY: str = "change_me_jwt_secret_key"
    JWT_ALGORITHM: str = "HS256"

    CORS_ORIGINS: str = (
        "http://localhost:3000,http://localhost:8080,http://localhost:5173"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()