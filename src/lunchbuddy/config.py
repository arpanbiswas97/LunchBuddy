from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "logs/lunchbuddy.log"
    log_rotation_when: str = "midnight"     # log rotation schedule
    log_backup_count: int = 7               # number of log backups to keep

    # Telegram Configuration
    telegram_bot_token: str                 # bot token from BotFather
    telegram_chat_id: str                   # target chat ID for sending messages

    # Database Configuration
    database_url: str = (
        "postgresql://lunchbuddy:lunchbuddy_password@localhost:5432/lunchbuddy"
    )

    # Lunch Reminder Configuration
    lunch_reminder_time: str = "12:30"      # 24h time format
    lunch_days: List[str] = [               # days when lunch is available
        "tuesday",
        "wednesday",
        "thursday",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
