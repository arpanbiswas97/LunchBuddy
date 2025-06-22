"""Data models for LunchBuddy bot."""

from datetime import datetime, date
from typing import List, Optional, Dict
from enum import Enum
from dataclasses import dataclass

from .config import settings


class DietaryPreference(Enum):
    """User dietary preferences."""
    VEG = "veg"
    NON_VEG = "non_veg"


def create_weekday_enum():
    """Create WeekDay enum dynamically from configuration."""
    # Create enum values from configured lunch days
    enum_values = {}
    for day in settings.lunch_days:
        day_lower = day.strip().lower()
        day_upper = day.strip().upper()
        enum_values[day_upper] = day_lower
    
    return Enum('WeekDay', enum_values)


# Create WeekDay enum dynamically
WeekDay = create_weekday_enum()


@dataclass
class User:
    """User enrollment data."""
    telegram_id: int
    full_name: str
    email: str
    dietary_preference: DietaryPreference
    preferred_days: List[WeekDay]
    is_enrolled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class PendingLunchConfirmation:
    """Pending lunch confirmation for a user."""
    user_id: int
    target_date: date
    message_id: int
    chat_id: int
    created_at: datetime
    response_received: bool = False
    user_choice: Optional[bool] = None


@dataclass
class LunchOverride:
    """Temporary lunch override for a specific day."""
    user_id: int
    date: datetime
    override_choice: bool  # True for lunch, False for no lunch
    created_at: Optional[datetime] = None


@dataclass
class LunchReminder:
    """Lunch reminder data."""
    user: User
    next_day: datetime
    has_lunch_scheduled: bool
    override_available: bool 