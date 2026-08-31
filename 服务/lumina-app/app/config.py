# ============================================
# Lumina 墨光 · 应用配置
# ============================================
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """应用配置，从环境变量读取"""

    # 应用
    APP_NAME: str = "lumina-user-service"
    APP_ENV: str = "development"  # development / testing / production
    APP_DEBUG: bool = True

    # 数据库
    DATABASE_URL: str = "mysql+pymysql://lumina:lumina_secure_password@localhost:3306/lumina"

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

    # AI 网关地址（单体内指向自身，微服务时指向 ai-gateway 服务）
    AI_GATEWAY_URL: str = "http://localhost:8080"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()