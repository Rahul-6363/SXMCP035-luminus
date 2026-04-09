from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma4:26b"

    # MySQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "MCP"
    DB_USER: str = "root"
    DB_PASSWORD: str = "Saurav%40007"

    # Mailer
    MAILER_URL: str = "http://localhost:3001"
    CUSTOMER_EMAIL: str = ""   # set in .env — receives BOM-ready notifications

    # IMAP mail reader — polls inbox for vendor shipment replies
    IMAP_HOST: str = "imap.gmail.com"
    IMAP_USER: str = ""   # Gmail address that receives vendor replies
    IMAP_PASS: str = ""   # Gmail app password
    IMAP_POLL_INTERVAL: int = 60  # seconds between polls

    # Discord — channel ID where shipment notifications are posted
    DISCORD_NOTIFY_CHANNEL_ID: int = 0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()