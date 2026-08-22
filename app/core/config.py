from functools import lru_cache
import os


class Settings:
    database_url: str
    secret_key: str
    access_token_expire_minutes: int
    public_base_url: str
    smtp_host: str | None
    smtp_port: int | None
    smtp_user: str | None
    smtp_password: str | None
    smtp_from: str | None

    def __init__(self) -> None:
        # SQLite makes local first-run and the test suite self-contained. Production uses DATABASE_URL.
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./dayflow.db")
        self.secret_key = os.getenv("SECRET_KEY", "development-only-change-me")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        self.public_base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT")) if os.getenv("SMTP_PORT") else None
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_from = os.getenv("SMTP_FROM")



@lru_cache
def get_settings() -> Settings:
    return Settings()

