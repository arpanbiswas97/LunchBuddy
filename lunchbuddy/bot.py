"""Telegram bot implementation for LunchBuddy."""

import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)

from .models import User, DietaryPreference, WeekDay
from .database import db_manager
from .config import settings

logger = logging.getLogger(__name__)

# Conversation states
(
    WAITING_FOR_NAME,
    WAITING_FOR_EMAIL,
    WAITING_FOR_DIETARY_PREFERENCE,
    WAITING_FOR_DAYS,
    WAITING_FOR_OVERRIDE_CHOICE
) = range(5)

# User data keys
USER_DATA_KEY = "user_data"


class LunchBuddyBot:
    """Main bot class for LunchBuddy."""
    
    def __init__(self):
        self.application = Application.builder().token(settings.telegram_bot_token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup all bot handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Enrollment conversation
        enroll_handler = ConversationHandler(
            entry_points=[CommandHandler("enroll", self.enroll_command)],
            states={
                WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_name)],
                WAITING_FOR_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_email)],
                WAITING_FOR_DIETARY_PREFERENCE: [CallbackQueryHandler(self.get_dietary_preference)],
                WAITING_FOR_DAYS: [CallbackQueryHandler(self.get_preferred_days)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_enrollment)]
        )
        self.application.add_handler(enroll_handler)
        
        # Unenroll command
        self.application.add_handler(CommandHandler("unenroll", self.unenroll_command))
        
        # Override conversation
        override_handler = ConversationHandler(
            entry_points=[CommandHandler("override", self.override_command)],
            states={
                WAITING_FOR_OVERRIDE_CHOICE: [CallbackQueryHandler(self.handle_override_choice)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_override)]
        )
        self.application.add_handler(override_handler)
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_text = """
🍽️ Welcome to LunchBuddy! 🍽️

I'm here to help you manage your lunch enrollments.

Available commands:
/enroll - Enroll for lunch service
/unenroll - Unenroll from lunch service
/status - Check your enrollment status
/override - Override your lunch choice for tomorrow
/help - Show this help message

Let's get started! Use /enroll to begin your enrollment.
        """
        await update.message.reply_text(welcome_text.strip())
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
🍽️ LunchBuddy Help 🍽️

Commands:
• /enroll - Enroll for lunch service (collects your preferences)
• /unenroll - Unenroll from lunch service
• /status - Check your current enrollment status
• /override - Override your lunch choice for tomorrow
• /help - Show this help message

Lunch is available on:
• Tuesday
• Wednesday  
• Thursday

You can choose multiple days and set dietary preferences (Veg/Non-Veg).

Daily reminders are sent at 12:30 PM on Monday, Tuesday, and Wednesday.
        """
        await update.message.reply_text(help_text.strip())
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        user_id = update.effective_user.id
        
        user = db_manager.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ You are not enrolled for lunch service. Use /enroll to get started!")
            return
        
        status_text = f"""
✅ Enrollment Status

Name: {user.full_name}
Email: {user.email}
Dietary Preference: {user.dietary_preference.value.title()}
Preferred Days: {', '.join([day.value.title() for day in user.preferred_days])}
Enrolled: {'Yes' if user.is_enrolled else 'No'}
        """
        await update.message.reply_text(status_text.strip())
    
    async def enroll_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start enrollment conversation."""
        user_id = update.effective_user.id
        
        # Check if already enrolled
        existing_user = db_manager.get_user(user_id)
        if existing_user:
            await update.message.reply_text(
                "❌ You are already enrolled! Use /status to check your details or /unenroll to remove your enrollment."
            )
            return ConversationHandler.END
        
        # Initialize user data
        context.user_data[USER_DATA_KEY] = {
            'telegram_id': user_id
        }
        
        await update.message.reply_text(
            "🍽️ Welcome to LunchBuddy enrollment!\n\n"
            "Please provide your full name:"
        )
        return WAITING_FOR_NAME
    
    async def get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get user's full name."""
        name = update.message.text.strip()
        if len(name) < 2:
            await update.message.reply_text("❌ Please provide a valid full name (at least 2 characters):")
            return WAITING_FOR_NAME
        
        context.user_data[USER_DATA_KEY]['full_name'] = name
        
        await update.message.reply_text(
            f"✅ Name: {name}\n\n"
            "Please provide your work email address:"
        )
        return WAITING_FOR_EMAIL
    
    async def get_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get user's email."""
        email = update.message.text.strip().lower()
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            await update.message.reply_text("❌ Please provide a valid email address:")
            return WAITING_FOR_EMAIL
        
        context.user_data[USER_DATA_KEY]['email'] = email
        
        # Ask for dietary preference
        keyboard = [
            [
                InlineKeyboardButton("🥬 Vegetarian", callback_data="diet_veg"),
                InlineKeyboardButton("🍗 Non-Vegetarian", callback_data="diet_non_veg")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Email: {email}\n\n"
            "Please select your dietary preference:",
            reply_markup=reply_markup
        )
        return WAITING_FOR_DIETARY_PREFERENCE
    
    async def get_dietary_preference(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get user's dietary preference."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "diet_veg":
            preference = DietaryPreference.VEG
        else:
            preference = DietaryPreference.NON_VEG
        
        context.user_data[USER_DATA_KEY]['dietary_preference'] = preference
        
        # Ask for preferred days
        keyboard = [
            [
                InlineKeyboardButton("Tuesday", callback_data="day_tuesday"),
                InlineKeyboardButton("Wednesday", callback_data="day_wednesday"),
                InlineKeyboardButton("Thursday", callback_data="day_thursday")
            ],
            [InlineKeyboardButton("✅ Done", callback_data="days_done")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Dietary Preference: {preference.value.title()}\n\n"
            "Please select your preferred lunch days (you can select multiple):",
            reply_markup=reply_markup
        )
        
        # Initialize selected days
        context.user_data[USER_DATA_KEY]['selected_days'] = []
        return WAITING_FOR_DAYS
    
    async def get_preferred_days(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get user's preferred days."""
        query = update.callback_query
        await query.answer()
        
        user_data = context.user_data[USER_DATA_KEY]
        selected_days = user_data.get('selected_days', [])
        
        if query.data == "days_done":
            if not selected_days:
                await query.edit_message_text(
                    "❌ Please select at least one day for lunch:"
                )
                return WAITING_FOR_DAYS
            
            # Complete enrollment
            user = User(
                telegram_id=user_data['telegram_id'],
                full_name=user_data['full_name'],
                email=user_data['email'],
                dietary_preference=user_data['dietary_preference'],
                preferred_days=selected_days
            )
            
            if db_manager.add_user(user):
                days_text = ', '.join([day.value.title() for day in selected_days])
                await query.edit_message_text(
                    f"🎉 Enrollment successful!\n\n"
                    f"Name: {user.full_name}\n"
                    f"Email: {user.email}\n"
                    f"Dietary Preference: {user.dietary_preference.value.title()}\n"
                    f"Preferred Days: {days_text}\n\n"
                    f"You'll receive daily reminders at 12:30 PM on Monday, Tuesday, and Wednesday."
                )
            else:
                await query.edit_message_text(
                    "❌ Failed to complete enrollment. Please try again later."
                )
            
            # Clear user data
            context.user_data.clear()
            return ConversationHandler.END
        
        # Toggle day selection
        day_name = query.data.replace("day_", "")
        day_enum = WeekDay(day_name)
        
        if day_enum in selected_days:
            selected_days.remove(day_enum)
        else:
            selected_days.append(day_enum)
        
        user_data['selected_days'] = selected_days
        
        # Update keyboard to show selected days
        keyboard = [
            [
                InlineKeyboardButton(
                    f"✅ Tuesday" if WeekDay.TUESDAY in selected_days else "Tuesday",
                    callback_data="day_tuesday"
                ),
                InlineKeyboardButton(
                    f"✅ Wednesday" if WeekDay.WEDNESDAY in selected_days else "Wednesday",
                    callback_data="day_wednesday"
                ),
                InlineKeyboardButton(
                    f"✅ Thursday" if WeekDay.THURSDAY in selected_days else "Thursday",
                    callback_data="day_thursday"
                )
            ],
            [InlineKeyboardButton("✅ Done", callback_data="days_done")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        selected_text = ', '.join([day.value.title() for day in selected_days]) if selected_days else "None"
        await query.edit_message_text(
            f"✅ Dietary Preference: {user_data['dietary_preference'].value.title()}\n\n"
            f"Selected Days: {selected_text}\n\n"
            "Please select your preferred lunch days (you can select multiple):",
            reply_markup=reply_markup
        )
        return WAITING_FOR_DAYS
    
    async def cancel_enrollment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel enrollment process."""
        context.user_data.clear()
        await update.message.reply_text("❌ Enrollment cancelled.")
        return ConversationHandler.END
    
    async def unenroll_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unenroll command."""
        user_id = update.effective_user.id
        
        if db_manager.remove_user(user_id):
            await update.message.reply_text(
                "✅ You have been successfully unenrolled from the lunch service.\n\n"
                "You can re-enroll anytime using /enroll."
            )
        else:
            await update.message.reply_text(
                "❌ You are not currently enrolled for lunch service."
            )
    
    async def override_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start override conversation."""
        user_id = update.effective_user.id
        
        # Check if user is enrolled
        user = db_manager.get_user(user_id)
        if not user:
            await update.message.reply_text(
                "❌ You are not enrolled for lunch service. Use /enroll to get started!"
            )
            return ConversationHandler.END
        
        # Get tomorrow's date
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_day = tomorrow.strftime("%A").lower()
        
        # Check if tomorrow is a lunch day
        if tomorrow_day not in [day.value for day in user.preferred_days]:
            await update.message.reply_text(
                f"❌ Tomorrow ({tomorrow.strftime('%A')}) is not one of your preferred lunch days.\n\n"
                f"Your preferred days: {', '.join([day.value.title() for day in user.preferred_days])}"
            )
            return ConversationHandler.END
        
        # Store tomorrow's date in context
        context.user_data['override_date'] = tomorrow
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, I want lunch", callback_data="override_yes"),
                InlineKeyboardButton("❌ No, skip lunch", callback_data="override_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🍽️ Lunch Override for {tomorrow.strftime('%A, %B %d')}\n\n"
            f"By default, you have lunch scheduled for tomorrow.\n"
            f"Would you like to change this?",
            reply_markup=reply_markup
        )
        return WAITING_FOR_OVERRIDE_CHOICE
    
    async def handle_override_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle override choice."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        override_date = context.user_data['override_date']
        
        if query.data == "override_yes":
            override_choice = True
            choice_text = "✅ Yes, I want lunch"
        else:
            override_choice = False
            choice_text = "❌ No, skip lunch"
        
        if db_manager.add_lunch_override(user_id, override_date, override_choice):
            await query.edit_message_text(
                f"✅ Override set successfully!\n\n"
                f"Date: {override_date.strftime('%A, %B %d')}\n"
                f"Choice: {choice_text}\n\n"
                f"This override only applies to this specific day."
            )
        else:
            await query.edit_message_text(
                "❌ Failed to set override. Please try again later."
            )
        
        context.user_data.clear()
        return ConversationHandler.END
    
    async def cancel_override(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel override process."""
        context.user_data.clear()
        await update.message.reply_text("❌ Override cancelled.")
        return ConversationHandler.END
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error(f"Exception while handling an update: {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later or contact support."
            )
    
    def run(self):
        """Run the bot."""
        logger.info("Starting LunchBuddy bot...")
        self.application.run_polling() 