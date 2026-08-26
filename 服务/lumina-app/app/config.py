# ============================================
# Lumina 墨光 · 应用配置（单体统一）
# ============================================
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，从环境变量读取"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # 应用
    APP_NAME: str = "lumina-app"
    APP_ENV: str = "development"  # development / testing / production
    APP_DEBUG: bool = True

    # 数据库
    DATABASE_URL: str = "postgresql://lumina:lumina_secure_password@localhost:5432/lumina"

    # JWT
    JWT_SECRET_KEY: str = "change_me_jwt_secret_key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://localhost:8080,http://localhost:5173"
    )

    # 日志
    LOG_LEVEL: str = "INFO"

    # AI 网关地址（单体内指向自身）
    AI_GATEWAY_URL: str = "http://localhost:8080"

    # AI 供应商 API Key（不入库，由环境变量注入）
    QWEN_API_KEY: str = ""
    GLM_API_KEY: str = ""
    SPARK_API_KEY: str = ""
    DOUBAO_API_KEY: str = ""
    BCE_API_KEY: str = ""
    MOONSHOT_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""


settings = Settings()