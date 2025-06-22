"""Scheduler for lunch reminders and notifications."""

import logging
import schedule
import time
import asyncio
from datetime import datetime, date, timedelta
from typing import List, Optional

from telegram import Bot
from telegram.error import TelegramError

from .models import User, WeekDay, LunchReminder
from .database import db_manager
from .config import settings

logger = logging.getLogger(__name__)


class LunchScheduler:
    """Handles scheduling and sending lunch reminders."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.setup_schedule()
    
    def setup_schedule(self):
        """Setup the daily reminder schedule."""
        # Schedule reminders for Monday, Tuesday, Wednesday at 12:30 PM
        schedule.every().monday.at(settings.lunch_reminder_time).do(self.send_daily_reminders)
        schedule.every().tuesday.at(settings.lunch_reminder_time).do(self.send_daily_reminders)
        schedule.every().wednesday.at(settings.lunch_reminder_time).do(self.send_daily_reminders)
        
        logger.info(f"Lunch reminders scheduled for {settings.lunch_reminder_time} on Monday, Tuesday, Wednesday")
    
    def send_daily_reminders(self):
        """Send daily lunch reminders to all enrolled users."""
        try:
            # Run the async function in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._send_daily_reminders_async())
            loop.close()
        except Exception as e:
            logger.error(f"Error sending daily reminders: {e}")
    
    async def _send_daily_reminders_async(self):
        """Async implementation of daily reminders."""
        try:
            # Get all enrolled users
            users = db_manager.get_enrolled_users()
            if not users:
                logger.info("No enrolled users found for reminders")
                return
            
            # Get tomorrow's date
            tomorrow = date.today() + timedelta(days=1)
            tomorrow_day = tomorrow.strftime("%A").lower()
            
            logger.info(f"Sending lunch reminders for {tomorrow.strftime('%A, %B %d')}")
            
            # Send reminders to each user
            for user in users:
                await self._send_user_reminder(user, tomorrow, tomorrow_day)
                
        except Exception as e:
            logger.error(f"Error in daily reminders: {e}")
    
    async def _send_user_reminder(self, user: User, tomorrow: date, tomorrow_day: str):
        """Send reminder to a specific user."""
        try:
            # Check if tomorrow is one of user's preferred days
            has_lunch_scheduled = tomorrow_day in [day.value for day in user.preferred_days]
            
            # Check for override
            override = db_manager.get_lunch_override(user.telegram_id, tomorrow)
            
            # Determine final lunch status
            if override is not None:
                final_lunch_status = override
                override_applied = True
            else:
                final_lunch_status = has_lunch_scheduled
                override_applied = False
            
            # Create reminder message
            message = self._create_reminder_message(user, tomorrow, final_lunch_status, override_applied)
            
            # Send message
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"Reminder sent to user {user.telegram_id} ({user.full_name})")
            
        except TelegramError as e:
            logger.error(f"Failed to send reminder to user {user.telegram_id}: {e}")
        except Exception as e:
            logger.error(f"Error sending reminder to user {user.telegram_id}: {e}")
    
    def _create_reminder_message(self, user: User, tomorrow: date, has_lunch: bool, override_applied: bool) -> str:
        """Create the reminder message for a user."""
        tomorrow_str = tomorrow.strftime("%A, %B %d")
        
        if has_lunch:
            status_emoji = "✅"
            status_text = "You have lunch scheduled"
        else:
            status_emoji = "❌"
            status_text = "You do not have lunch scheduled"
        
        message = f"""
🍽️ <b>Lunch Reminder for {tomorrow_str}</b>

{status_emoji} {status_text}

👤 <b>Name:</b> {user.full_name}
🥬 <b>Dietary Preference:</b> {user.dietary_preference.value.title()}
        """
        
        if override_applied:
            message += "\n⚠️ <i>This is an override from your default schedule</i>"
        
        message += f"""

💡 <b>Need to change?</b>
Use /override to modify your lunch choice for tomorrow only.

📅 <b>Your regular schedule:</b>
{', '.join([day.value.title() for day in user.preferred_days])}

For any questions, contact your admin.
        """
        
        return message.strip()
    
    def run_scheduler(self):
        """Run the scheduler loop."""
        logger.info("Starting lunch reminder scheduler...")
        
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
    
    def send_test_reminder(self, user_id: int):
        """Send a test reminder to a specific user (for testing)."""
        try:
            user = db_manager.get_user(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return False
            
            tomorrow = date.today() + timedelta(days=1)
            tomorrow_day = tomorrow.strftime("%A").lower()
            has_lunch = tomorrow_day in [day.value for day in user.preferred_days]
            
            message = self._create_reminder_message(user, tomorrow, has_lunch, False)
            
            # Run in async context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            ))
            loop.close()
            
            logger.info(f"Test reminder sent to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending test reminder: {e}")
            return False 