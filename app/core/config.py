from functools import lru_cache
import os


class Settings:
    database_url: str
    secret_key: str
    access_token_expire_minutes: int

    def __init__(self) -> None:
        # SQLite makes local first-run and the test suite self-contained. Production uses DATABASE_URL.
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./dayflow.db")
        self.secret_key = os.getenv("SECRET_KEY", "development-only-change-me")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


@lru_cache
def get_settings() -> Settings:
    return Settings()

