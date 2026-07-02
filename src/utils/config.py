"""
MeetSmart AI — Config loader using pydantic-settings.
Reads from .env file (falls back to defaults).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "MeetSmart AI"
    APP_HOST: str = "localhost"
    API_PORT: int = 8000
    FRONTEND_PORT: int = 5173

    # Database
    DATABASE_URL: str = "sqlite:///./meetsmart.db"

    # Gemini
    GEMINI_API_KEY: str = ""

    # Email
    SMTP_MODE: str = "mock"          # "mock" | "gmail"
    GMAIL_ADDRESS: str = ""
    GMAIL_APP_PASSWORD: str = ""

    # Outputs
    OUTPUTS_DIR: str = "./outputs"

    @property
    def outputs_path(self) -> Path:
        p = Path(self.OUTPUTS_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.GEMINI_API_KEY)


settings = Settings()
