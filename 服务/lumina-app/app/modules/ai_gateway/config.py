# ============================================
# Lumina 墨光 · AI 网关服务配置
# ============================================
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，从环境变量读取"""

    APP_NAME: str = "lumina-ai-gateway"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    DATABASE_URL: str = "mysql+pymysql://lumina:lumina_secure_password@localhost:3306/lumina"

    JWT_SECRET_KEY: str = "change_me_jwt_secret_key"
    JWT_ALGORITHM: str = "HS256"

    CORS_ORIGINS: str = (
        "http://localhost:3000,http://localhost:8080,http://localhost:5173"
    )

    # 模型供应商 API Key（不入库，对话/批阅服务消费）
    QWEN_API_KEY: str = ""
    GLM_API_KEY: str = ""
    SPARK_API_KEY: str = ""
    DOUBAO_API_KEY: str = ""
    BCE_API_KEY: str = ""
    MOONSHOT_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()