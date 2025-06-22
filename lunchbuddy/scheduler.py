"""Scheduler for lunch registration processing."""

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable, Dict, List, Optional

import schedule

from .config import settings
from .database import db_manager
from .models import PendingLunchConfirmation

logger = logging.getLogger(__name__)

# In-memory store for pending confirmations: (user_id, date) -> PendingLunchConfirmation
pending_confirmations: Dict[tuple, PendingLunchConfirmation] = {}


@dataclass
class LunchRegistrationEvent:
    """Event data for lunch registration processing."""

    user_id: int
    target_date: date
    user_name: str
    user_email: str
    dietary_preference: str
    preferred_days: List[str]


def register_user_for_lunch(name: str, email: str, dietary_preference: str):
    """
    #TODO: Implement actual lunch registration logic here.
    This function is called when user confirms they want lunch.
    """
    logger.info(f"Registering {name} ({email}, {dietary_preference}) for lunch.")
    pass


class LunchScheduler:
    """Handles scheduling and processing lunch registrations."""

    def __init__(
        self,
        registration_callback: Callable[[LunchRegistrationEvent], None],
        timeout_callback: Optional[Callable[[int, date, bool], None]] = None,
    ):
        """
        Initialize scheduler with callback functions that will be called
        when registration processing should be triggered.

        Args:
            registration_callback: Function to call when registration processing should be triggered.
                                  This function will be called from the scheduler thread
                                  and should handle posting to the bot's event loop.
            timeout_callback: Function to call when confirmation times out (30 minutes).
                             This function will be called from the scheduler thread
                             and should handle posting to the bot's event loop.
        """
        self.registration_callback = registration_callback
        self.timeout_callback = timeout_callback
        self.setup_schedule()

    def setup_schedule(self):
        """Setup schedule based on lunch_days configuration."""
        # Get the configured lunch days
        lunch_days = settings.lunch_days
        
        # Schedule registration processing one day before each lunch day at 12:30 PM
        for day in lunch_days:
            day_lower = day.strip().lower()
            
            # Map day names to schedule methods
            day_mapping = {
                "monday": schedule.every().monday,
                "tuesday": schedule.every().tuesday,
                "wednesday": schedule.every().wednesday,
                "thursday": schedule.every().thursday,
                "friday": schedule.every().friday,
                "saturday": schedule.every().saturday,
                "sunday": schedule.every().sunday,
            }
            
            # Map lunch days to the day before when we should schedule the process
            day_before_mapping = {
                "monday": "sunday",      # Process on Sunday for Monday lunch
                "tuesday": "monday",     # Process on Monday for Tuesday lunch
                "wednesday": "tuesday",  # Process on Tuesday for Wednesday lunch
                "thursday": "wednesday", # Process on Wednesday for Thursday lunch
                "friday": "thursday",    # Process on Thursday for Friday lunch
                "saturday": "friday",    # Process on Friday for Saturday lunch
                "sunday": "saturday",    # Process on Saturday for Sunday lunch
            }
            
            if day_lower in day_mapping:
                # Get the day before when we should schedule the process
                day_before = day_before_mapping.get(day_lower)
                if day_before and day_before in day_mapping:
                    # Schedule registration processing on the day before at the configured time
                    day_mapping[day_before].at(settings.lunch_reminder_time).do(
                        self.process_lunch_registration
                    )
                    logger.info(
                        f"Scheduled lunch registration processing for {day} (process on {day_before} at {settings.lunch_reminder_time})"
                    )
                else:
                    logger.warning(f"Could not determine day before for {day}")
            else:
                logger.warning(f"Invalid day '{day}' in lunch_days configuration")

    def process_lunch_registration(self):
        """Process lunch registration for the next day."""
        try:
            logger.info("Processing lunch registration for the next day.")
            users = db_manager.get_enrolled_users()
            if not users:
                logger.info("No enrolled users for lunch registration.")
                return
                
            tomorrow = date.today() + timedelta(days=1)
            tomorrow_day = tomorrow.strftime("%A").lower()
            
            for user in users:
                # Check if tomorrow is in user's preferred days
                if tomorrow_day in [d.value for d in user.preferred_days]:
                    # Create event data
                    event = LunchRegistrationEvent(
                        user_id=user.telegram_id,
                        target_date=tomorrow,
                        user_name=user.full_name,
                        user_email=user.email,
                        dietary_preference=user.dietary_preference.value,
                        preferred_days=[d.value for d in user.preferred_days],
                    )
                    
                    # Trigger the callback to process registration
                    self.registration_callback(event)
                    
                    # Schedule timeout check for this user
                    self.schedule_timeout_check(user.telegram_id, tomorrow)
                    
        except Exception as e:
            logger.error(f"Error processing lunch registration: {e}")

    def schedule_timeout_check(self, user_id: int, target_date: date):
        """Schedule a timeout check for 30 minutes from now."""
        def timeout_handler():
            self.handle_registration_timeout(user_id, target_date)
        
        # Schedule timeout check for 30 minutes from now
        schedule.every(30).minutes.do(timeout_handler).tag(
            f"timeout_{user_id}_{target_date}"
        )
        logger.info(f"Scheduled timeout check for user {user_id} on {target_date}")

    def handle_registration_timeout(self, user_id: int, target_date: date):
        """Handle registration timeout - assume default preference."""
        try:
            key = (user_id, target_date)
            confirmation = pending_confirmations.get(key)
            
            if confirmation and not confirmation.response_received:
                # Check if the target date is in user's preferred days
                user = db_manager.get_user(user_id)
                if user:
                    target_day = target_date.strftime("%A").lower()
                    take_lunch = target_day in [d.value for d in user.preferred_days]
                    
                    # Register for lunch only if it's a preferred day
                    if take_lunch:
                        register_user_for_lunch(
                            user.full_name, user.email, user.dietary_preference.value
                        )
                    
                    # Notify user about timeout and default action
                    if self.timeout_callback:
                        self.timeout_callback(user_id, target_date, take_lunch)
                    
                    # Clean up
                    del pending_confirmations[key]
                    
                    # Remove the timeout schedule
                    schedule.clear(f"timeout_{user_id}_{target_date}")
                    
                    logger.info(
                        f"Registration timeout for user {user_id} on {target_date}, defaulted to {'lunch' if take_lunch else 'no lunch'}"
                    )
                
        except Exception as e:
            logger.error(f"Error handling registration timeout: {e}")

    def run_scheduler(self):
        """Run the scheduler loop."""
        logger.info("Starting lunch registration scheduler...")

        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)  # Wait before retrying
