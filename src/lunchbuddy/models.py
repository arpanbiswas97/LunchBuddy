from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class DietaryPreference(Enum):
    """User dietary preferences."""

    VEG = "Veg"
    NON_VEG = "Non Veg"


class User(BaseModel):
    """User enrollment data."""

    telegram_id: int
    full_name: str
    email: str
    dietary_preference: DietaryPreference
    preferred_days: List[str]
    is_enrolled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
