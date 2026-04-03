from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "MalPhaGo API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database (sqlite+aiosqlite for local dev, postgresql+asyncpg for production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./malphago_dev.db"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["*"]

    # Crawling
    KRA_BASE_URL: str = "https://race.kra.co.kr"
    GUMBIT_BASE_URL: str = "https://www.gumvit.com"

    # data.go.kr 공공데이터 API
    DATA_GO_KR_SERVICE_KEY: str = ""  # data.go.kr 인증키 (URL 인코딩된 키)

    # FCM (Phase 2)
    FCM_SERVER_KEY: str = ""

    # SMS (알리고 API)
    SMS_API_KEY: str = ""
    SMS_USER_ID: str = ""
    SMS_SENDER: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
