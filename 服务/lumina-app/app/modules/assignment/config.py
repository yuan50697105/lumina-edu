# ============================================
# Lumina 墨光 · 作业服务配置
# ============================================
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，从环境变量读取"""

    # 应用
    APP_NAME: str = "lumina-assignment-service"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    # 数据库（共享库）
    DATABASE_URL: str = "mysql+pymysql://lumina:lumina_secure_password@localhost:3306/lumina"

    # JWT（跨服务共享密钥）
    JWT_SECRET_KEY: str = "change_me_jwt_secret_key"
    JWT_ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://localhost:8080,http://localhost:5173"
    )

    # 上传存储
    UPLOAD_DIR: str = "uploads"          # 临时本地存储（正式环境接 MinIO）
    MAX_UPLOAD_MB: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()