from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Gemini
    gemini_api_key: str = ""

    # JWT
    secret_key: str = "change-this-secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # Database
    database_url: str = "sqlite:////app/data/andreja.db"

    # Storage
    upload_dir: str = "/app/data/uploads"
    images_dir: str = "/app/data/images"

    # Ingestion performance (safe defaults)
    ingestion_concurrency: int = 2

    # Admin default
    admin_email: str = "admin@andreja.com"
    admin_password: str = "admin123"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
