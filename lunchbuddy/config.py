"""Configuration management for LunchBuddy bot."""

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Telegram Bot Configuration
    telegram_bot_token: str
    telegram_chat_id: str

    # Database Configuration
    database_url: str = (
        "postgresql://lunchbuddy:lunchbuddy_password@localhost:5432/lunchbuddy"
    )

    # Bot Configuration
    lunch_reminder_time: str = "12:30"
    lunch_days: str = "Tuesday,Wednesday,Thursday"

    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "logs/lunchbuddy.log"

    @field_validator("lunch_days")
    @classmethod
    def parse_reminder_days(cls, v):
        """Parse reminder days string into list."""
        if isinstance(v, str):
            return [day.strip() for day in v.split(",")]
        return v

    @field_validator("lunch_reminder_time")
    @classmethod
    def validate_time_format(cls, v):
        """Validate time format (HH:MM)."""
        try:
            hour, minute = map(int, v.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
            return v
        except (ValueError, AttributeError):
            raise ValueError("Time must be in HH:MM format")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
