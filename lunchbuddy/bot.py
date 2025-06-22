"""Telegram bot implementation for LunchBuddy."""

import asyncio
import logging
import re
from datetime import date, datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .config import settings
from .database import db_manager
from .models import DietaryPreference, PendingLunchConfirmation, User, WeekDay
from .scheduler import LunchRegistrationEvent, register_user_for_lunch, pending_confirmations

logger = logging.getLogger(__name__)

# Conversation states
(
    WAITING_FOR_NAME,
    WAITING_FOR_EMAIL,
    WAITING_FOR_DIETARY_PREFERENCE,
    WAITING_FOR_DAYS,
    WAITING_FOR_OVERRIDE_CHOICE,
) = range(5)

# User data keys
USER_DATA_KEY = "user_data"


class LunchBuddyBot:
    """Main bot class for LunchBuddy."""

    def __init__(self):
        self.application = (
            Application.builder().token(settings.telegram_bot_token).build()
        )
        self.event_loop = None  # Will be set when bot starts
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
                WAITING_FOR_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_name)
                ],
                WAITING_FOR_EMAIL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_email)
                ],
                WAITING_FOR_DIETARY_PREFERENCE: [
                    CallbackQueryHandler(self.get_dietary_preference)
                ],
                WAITING_FOR_DAYS: [CallbackQueryHandler(self.get_preferred_days)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_enrollment)],
        )
        self.application.add_handler(enroll_handler)

        # Unenroll command
        self.application.add_handler(CommandHandler("unenroll", self.unenroll_command))

        # Lunch confirmation response handler
        self.application.add_handler(CallbackQueryHandler(self.handle_lunch_response))

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
/help - Show this help message

Let's get started! Use /enroll to begin your enrollment.
        """
        await update.message.reply_text(welcome_text.strip())

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        # Get available days from configuration
        available_days = [day.strip().title() for day in settings.lunch_days]
        days_text = ", ".join(available_days)
        
        help_text = f"""
🍽️ LunchBuddy Help 🍽️

Commands:
• /enroll - Enroll for lunch service (collects your preferences)
• /unenroll - Unenroll from lunch service
• /status - Check your current enrollment status
• /override - Override your lunch choice for tomorrow
• /help - Show this help message

Lunch is available on:
• {days_text}

You can choose multiple days and set dietary preferences (Veg/Non-Veg).

Daily registration requests are sent at {settings.lunch_reminder_time} on the day before each lunch day.
        """
        await update.message.reply_text(help_text.strip())

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        user_id = update.effective_user.id

        user = db_manager.get_user(user_id)
        if not user:
            await update.message.reply_text(
                "❌ You are not enrolled for lunch service. Use /enroll to get started!"
            )
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
        context.user_data[USER_DATA_KEY] = {"telegram_id": user_id}

        await update.message.reply_text(
            "🍽️ Welcome to LunchBuddy enrollment!\n\n" "Please provide your full name:"
        )
        return WAITING_FOR_NAME

    async def get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get user's full name."""
        name = update.message.text.strip()
        if len(name) < 2:
            await update.message.reply_text(
                "❌ Please provide a valid full name (at least 2 characters):"
            )
            return WAITING_FOR_NAME

        context.user_data[USER_DATA_KEY]["full_name"] = name

        await update.message.reply_text(
            f"✅ Name: {name}\n\n" "Please provide your work email address:"
        )
        return WAITING_FOR_EMAIL

    async def get_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get user's email."""
        email = update.message.text.strip().lower()

        # Basic email validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            await update.message.reply_text("❌ Please provide a valid email address:")
            return WAITING_FOR_EMAIL

        context.user_data[USER_DATA_KEY]["email"] = email

        # Ask for dietary preference
        keyboard = [
            [
                InlineKeyboardButton("🥬 Vegetarian", callback_data="diet_veg"),
                InlineKeyboardButton("🍗 Non-Vegetarian", callback_data="diet_non_veg"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Email: {email}\n\n" "Please select your dietary preference:",
            reply_markup=reply_markup,
        )
        return WAITING_FOR_DIETARY_PREFERENCE

    async def get_dietary_preference(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Get user's dietary preference."""
        query = update.callback_query
        await query.answer()

        if query.data == "diet_veg":
            preference = DietaryPreference.VEG
        else:
            preference = DietaryPreference.NON_VEG

        context.user_data[USER_DATA_KEY]["dietary_preference"] = preference

        # Create keyboard with available days from configuration
        keyboard = []
        row = []
        for day in settings.lunch_days:
            day_lower = day.strip().lower()
            day_title = day.strip().title()
            row.append(InlineKeyboardButton(day_title, callback_data=f"day_{day_lower}"))
            
            # Add 3 days per row for better layout
            if len(row) == 3:
                keyboard.append(row)
                row = []
        
        # Add any remaining days
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("✅ Done", callback_data="days_done")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"✅ Dietary Preference: {preference.value.title()}\n\n"
            "Please select your preferred lunch days (you can select multiple):",
            reply_markup=reply_markup,
        )

        # Initialize selected days
        context.user_data[USER_DATA_KEY]["selected_days"] = []
        return WAITING_FOR_DAYS

    async def get_preferred_days(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Get user's preferred days."""
        query = update.callback_query
        await query.answer()

        user_data = context.user_data[USER_DATA_KEY]
        selected_days = user_data.get("selected_days", [])

        if query.data == "days_done":
            if not selected_days:
                await query.edit_message_text(
                    "❌ Please select at least one day for lunch:"
                )
                return WAITING_FOR_DAYS

            # Complete enrollment
            user = User(
                telegram_id=user_data["telegram_id"],
                full_name=user_data["full_name"],
                email=user_data["email"],
                dietary_preference=user_data["dietary_preference"],
                preferred_days=selected_days,
            )

            if db_manager.add_user(user):
                days_text = ", ".join([day.value.title() for day in selected_days])
                available_days = [day.strip().title() for day in settings.lunch_days]
                days_list = ", ".join(available_days)
                
                await query.edit_message_text(
                    f"🎉 Enrollment successful!\n\n"
                    f"Name: {user.full_name}\n"
                    f"Email: {user.email}\n"
                    f"Dietary Preference: {user.dietary_preference.value.title()}\n"
                    f"Preferred Days: {days_text}\n\n"
                    f"You'll receive registration requests at {settings.lunch_reminder_time} on the day before each lunch day ({days_list})."
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

        user_data["selected_days"] = selected_days

        # Update keyboard to show selected days
        keyboard = []
        row = []
        for day in settings.lunch_days:
            day_lower = day.strip().lower()
            day_title = day.strip().title()
            
            # Find the corresponding WeekDay enum
            day_enum = None
            for enum_day in WeekDay:
                if enum_day.value == day_lower:
                    day_enum = enum_day
                    break
            
            if day_enum:
                button_text = f"✅ {day_title}" if day_enum in selected_days else day_title
                row.append(InlineKeyboardButton(button_text, callback_data=f"day_{day_lower}"))
                
                # Add 3 days per row for better layout
                if len(row) == 3:
                    keyboard.append(row)
                    row = []
        
        # Add any remaining days
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("✅ Done", callback_data="days_done")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        selected_text = (
            ", ".join([day.value.title() for day in selected_days])
            if selected_days
            else "None"
        )
        await query.edit_message_text(
            f"✅ Dietary Preference: {user_data['dietary_preference'].value.title()}\n\n"
            f"Selected Days: {selected_text}\n\n"
            "Please select your preferred lunch days (you can select multiple):",
            reply_markup=reply_markup,
        )
        return WAITING_FOR_DAYS

    async def cancel_enrollment(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Cancel enrollment process."""
        context.user_data.clear()
        await update.message.reply_text("❌ Enrollment cancelled.")
        return ConversationHandler.END

    async def unenroll_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
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

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors in the bot."""
        logger.error(f"Exception while handling an update: {context.error}")
        if update:
            logger.error(f"Update {update} caused error {context.error}")

    async def process_lunch_registration(self, event: LunchRegistrationEvent):
        """Process lunch registration for a user."""
        try:
            keyboard = [
                [
                    InlineKeyboardButton(
                        "✅ Yes", callback_data=f"lunch_yes_{event.target_date}"
                    ),
                    InlineKeyboardButton(
                        "❌ No", callback_data=f"lunch_no_{event.target_date}"
                    ),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            msg = await self.application.bot.send_message(
                chat_id=event.user_id,
                text=f"🍽️ Do you want lunch for {event.target_date.strftime('%A, %B %d')}?\n\n"
                     f"Please respond within 30 minutes. If no response is received, "
                     f"you will be automatically registered for lunch.",
                reply_markup=reply_markup,
            )
            
            # Store the pending confirmation
            pending_confirmations[(event.user_id, event.target_date)] = (
                PendingLunchConfirmation(
                    user_id=event.user_id,
                    target_date=event.target_date,
                    message_id=msg.message_id,
                    chat_id=event.user_id,
                    created_at=datetime.now(),
                )
            )
            
            logger.info(
                f"Lunch registration request sent to user {event.user_id} for {event.target_date}"
            )
            
        except Exception as e:
            logger.error(f"Failed to process lunch registration for user {event.user_id}: {e}")

    async def send_timeout_notification(
        self, user_id: int, target_date: date, take_lunch: bool
    ):
        """Send timeout notification to user."""
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=f"⏰ No response received within 30 minutes for lunch on {target_date.strftime('%A, %B %d')}.\n\n"
                     f"{'✅' if take_lunch else '❌'} You have been {'automatically registered' if take_lunch else 'automatically cancelled'} for lunch.",
            )
            logger.info(
                f"Timeout notification sent to user {user_id} for {target_date}"
            )
        except Exception as e:
            logger.error(
                f"Failed to send timeout notification to user {user_id}: {e}"
            )

    def handle_registration_event(self, event: LunchRegistrationEvent):
        """Handle registration events by posting to the bot's event loop."""
        try:
            if self.event_loop is None:
                logger.error("Bot event loop not available for registration event")
                return
                
            # Post the coroutine to the bot's event loop
            self.event_loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.process_lunch_registration(event))
            )
            logger.info(f"Registration event queued for user {event.user_id}")
            
        except Exception as e:
            logger.error(f"Error handling registration event: {e}")

    def handle_timeout_event(
        self, user_id: int, target_date: date, take_lunch: bool
    ):
        """Handle timeout events by posting to the bot's event loop."""
        try:
            if self.event_loop is None:
                logger.error("Bot event loop not available for timeout event")
                return
                
            # Post the coroutine to the bot's event loop
            self.event_loop.call_soon_threadsafe(
                lambda: asyncio.create_task(
                    self.send_timeout_notification(user_id, target_date, take_lunch)
                )
            )
            logger.info(f"Timeout event queued for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling timeout event: {e}")

    async def handle_lunch_response(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle lunch response from user."""
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data
        
        if data.startswith("lunch_yes_") or data.startswith("lunch_no_"):
            date_str = data.split("_", 2)[2]
            target_date = date.fromisoformat(date_str)
            key = (user_id, target_date)
            confirmation = pending_confirmations.get(key)
            
            if confirmation and not confirmation.response_received:
                confirmation.response_received = True
                confirmation.user_choice = data.startswith("lunch_yes_")
                
                # Process the registration based on user choice
                if confirmation.user_choice:
                    user = db_manager.get_user(user_id)
                    if user:
                        register_user_for_lunch(
                            user.full_name, user.email, user.dietary_preference.value
                        )
                        logger.info(f"User {user_id} confirmed lunch for {target_date}")
                
                await query.edit_message_text(
                    f"{'✅' if confirmation.user_choice else '❌'} Your lunch registration for {target_date.strftime('%A, %B %d')} has been {'confirmed' if confirmation.user_choice else 'cancelled'}."
                )
                
                # Clean up the pending confirmation
                del pending_confirmations[key]
                
            else:
                await query.answer(
                    "This confirmation is no longer active or already recorded.",
                    show_alert=True,
                )

    def run(self):
        """Run the bot."""
        logger.info("Starting LunchBuddy bot...")
        # Store the event loop reference
        self.event_loop = asyncio.get_event_loop()
        self.application.run_polling()
