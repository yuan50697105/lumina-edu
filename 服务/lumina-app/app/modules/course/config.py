# ============================================
# Lumina 墨光 · 课程服务配置
# ============================================
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，从环境变量读取"""

    # 应用
    APP_NAME: str = "lumina-course-service"
    APP_ENV: str = "development"  # development / testing / production
    APP_DEBUG: bool = True

    # 数据库（与 user-service 共享同一 MySQL）
    DATABASE_URL: str = "mysql+pymysql://lumina:lumina_secure_password@localhost:3306/lumina"

    # JWT（与 user-service 共享密钥，用于跨服务鉴权）
    JWT_SECRET_KEY: str = "change_me_jwt_secret_key"
    JWT_ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://localhost:8080,http://localhost:5173"
    )

    # 用户服务地址（第 2.12 联调阶段启用远端同步）
    USER_SERVICE_URL: str = "http://user-service:8080"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()