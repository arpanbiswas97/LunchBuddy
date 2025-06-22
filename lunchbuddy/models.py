"""Data models for LunchBuddy bot."""

from datetime import datetime
from typing import List, Optional
from enum import Enum
from dataclasses import dataclass


class DietaryPreference(Enum):
    """User dietary preferences."""
    VEG = "veg"
    NON_VEG = "non_veg"


class WeekDay(Enum):
    """Week days for lunch."""
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"


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