from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma2:27b"

    # Local MySQL database
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "items_db"
    db_user: str = "root"
    db_password: str = ""

    # Schema file
    schema_path: str = "items_schema.sql"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
