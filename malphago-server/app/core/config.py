from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "MalPhaGo API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://malphago:malphago@localhost:5432/malphago"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["*"]

    # Crawling
    KRA_BASE_URL: str = "https://race.kra.co.kr"
    GUMBIT_BASE_URL: str = "https://www.gumvit.com"

    # FCM (Phase 2)
    FCM_SERVER_KEY: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
