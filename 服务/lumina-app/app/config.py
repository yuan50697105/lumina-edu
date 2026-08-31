# ============================================
# Lumina 墨光 · 应用配置
# ============================================
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """应用配置，从环境变量读取"""

    # 应用
    APP_NAME: str = "lumina-user-service"
    APP_ENV: str = "development"  # development / testing / production
    APP_DEBUG: bool = False  # True 时 SQLAlchemy echo 全量 SQL 日志，拖慢高并发

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

    # 直播流媒体地址前缀（HLS 适配层，如 http://127.0.0.1:8888/live）
    # 输出布局 {base}/{stream_key}/index.m3u8（与 mediamtx / Nginx-HLS 一致）
    # 留空时 /live/rooms/{id} 返回 mock:// 占位流地址，不阻塞课堂协作逻辑
    LIVE_STREAM_BASE: str = ""

    # 直播同源反代（开发/演示）：true 时 stream_url 返回 /media/... 相对代理地址，
    # 由 lumina-app 转发到 LIVE_STREAM_BASE，规避跨域 CORS 与媒体服务器 cookie 校验
    LIVE_STREAM_PROXY: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()