import asyncio
import logging
import re
from datetime import datetime, time, timedelta
from enum import IntEnum, auto

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

from . import messages
from .config import settings
from .database import db_manager
from .models import DietaryPreference, User
from .processor import BrowserAutomator

logger = logging.getLogger(__name__)


class EnrollmentStates(IntEnum):
    NAME = auto()
    EMAIL = auto()
    DIETARY_PREFERENCE = auto()
    DAYS = auto()


# User data keys
USER_DATA_KEY = "user_data"
LUNCH_CONFIRMATION_KEY = "user_confirmation"

PREVIOUS_DAY_MAP = {
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    "monday": 0,
}


class LunchBuddyBot:

    def __init__(self):
        self.application = (
            Application.builder().token(settings.telegram_bot_token).build()
        )
        self.setup_handlers()

    def setup_handlers(self):
        # Command Handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(
            ConversationHandler(
                entry_points=[CommandHandler("enroll", self.enroll_command)],
                states={
                    EnrollmentStates.NAME: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_name)
                    ],
                    EnrollmentStates.EMAIL: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_email)
                    ],
                    EnrollmentStates.DIETARY_PREFERENCE: [
                        CallbackQueryHandler(self.get_dietary_preference)
                    ],
                    EnrollmentStates.DAYS: [
                        CallbackQueryHandler(self.get_preferred_days)
                    ],
                },
                fallbacks=[CommandHandler("cancel", self.cancel_enrollment)],
            )
        )
        self.application.add_handler(CommandHandler("unenroll", self.unenroll_command))

        self.application.add_error_handler(self.error_handler)

        self.application.bot_data[LUNCH_CONFIRMATION_KEY] = {
            "positive_response": set(),
            "negative_response": set(),
            "window_open": False,
        }

        # Schedule the reminder job
        reminder_hour, reminder_minute = map(
            int, settings.lunch_reminder_time.split(":")
        )
        self.application.job_queue.run_daily(
            self.send_lunch_reminders,
            time=time(hour=reminder_hour, minute=reminder_minute),
            days=[PREVIOUS_DAY_MAP[day.strip().lower()] for day in settings.lunch_days],
        )

        self.application.add_handler(
            CallbackQueryHandler(
                self.handle_lunch_response, pattern=r"^lunch_(yes|no)$"
            )
        )

        # Schedule the booking job
        self.application.job_queue.run_daily(
            self.process_lunch_bookings,
            time=(
                datetime.combine(
                    datetime.today().date(),
                    time(hour=reminder_hour, minute=reminder_minute),
                )
                + timedelta(minutes=settings.lunch_reminder_timeout)
            ).time(),
            days=[PREVIOUS_DAY_MAP[day.strip().lower()] for day in settings.lunch_days],
        )

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(messages.WELCOME_MESSAGE.strip())

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            messages.HELP_MESSAGE_TEMPLATE.format(
                days="• ".join(settings.lunch_days),
                reminder_time=settings.lunch_reminder_time,
            ).strip()
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user = db_manager.get_user(user_id)

        if not user:
            await update.message.reply_text(messages.STATUS_NOT_ENROLLED.strip())
            return

        await update.message.reply_text(
            messages.STATUS_MESSAGE_TEMPLATE.format(
                name=user.full_name,
                email=user.email,
                diet=user.dietary_preference.value.title(),
                days=", ".join(user.preferred_days),
                enrolled=user.is_enrolled,
            ).strip()
        )

    async def enroll_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        # Check if already enrolled
        existing_user = db_manager.get_user(user_id)
        if existing_user:
            await update.message.reply_text(messages.ALREADY_ENROLLED.strip())
            return ConversationHandler.END

        # Initalize user data
        context.user_data[USER_DATA_KEY] = {"telegram_id": user_id}

        await update.message.reply_text(messages.ENROLLMENT_WELCOME.strip())

        return EnrollmentStates.NAME

    async def get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        name = update.message.text.strip()
        if len(name) < 2:
            await update.message.reply_text(messages.INVALID_NAME)
            return EnrollmentStates.NAME

        context.user_data[USER_DATA_KEY]["full_name"] = name

        await update.message.reply_text(
            messages.NAME_ACCEPTED_TEMPLATE.format(name=name).strip()
        )

        return EnrollmentStates.EMAIL

    async def get_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        email = update.message.text.strip().lower()

        # Basic email validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            await update.message.reply_text(messages.INVALID_EMAIL.strip())
            return EnrollmentStates.EMAIL

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
            messages.EMAIL_ACCEPTED_TEMPLATE.format(email=email).strip(),
            reply_markup=reply_markup,
        )
        return EnrollmentStates.DIETARY_PREFERENCE

    def _build_days_keyboard(self, selected_days=[]):
        keyboard = []
        row = []
        for day in settings.lunch_days:
            day_lower = day.strip().lower()
            day_title = day.strip().title()
            button_text = f"✅ {day_title}" if day_lower in selected_days else day_title
            row.append(
                InlineKeyboardButton(button_text, callback_data=f"day_{day_lower}")
            )

            # Add 3 days per row for better layout
            if len(row) == 3:
                keyboard.append(row)
                row = []

        # Add any remaining days
        if row:
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("✅ Done", callback_data="days_done")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        return reply_markup

    async def get_dietary_preference(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        query = update.callback_query
        await query.answer()

        if query.data == "diet_veg":
            preference = DietaryPreference.VEG
        else:
            preference = DietaryPreference.NON_VEG

        context.user_data[USER_DATA_KEY]["dietary_preference"] = preference

        reply_markup = self._build_days_keyboard()
        await query.edit_message_text(
            messages.DIET_ACCEPTED_TEMPLATE.format(
                diet=preference.value.title()
            ).strip(),
            reply_markup=reply_markup,
        )

        # Initialize selected days
        context.user_data[USER_DATA_KEY]["selected_days"] = []

        return EnrollmentStates.DAYS

    async def get_preferred_days(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        query = update.callback_query
        await query.answer()

        user_data = context.user_data[USER_DATA_KEY]
        selected_days = user_data.get("selected_days", [])

        if query.data == "days_done":
            if not selected_days:
                reply_markup = self._build_days_keyboard()
                await query.edit_message_text(
                    messages.NO_DAYS_SELECTED.strip(), reply_markup=reply_markup
                )
                return EnrollmentStates.DAYS

            # Complete enrollment
            user = User(
                telegram_id=user_data["telegram_id"],
                full_name=user_data["full_name"],
                email=user_data["email"],
                dietary_preference=user_data["dietary_preference"],
                preferred_days=selected_days,
            )

            if db_manager.add_user(user):
                days_text = ", ".join([day.title() for day in selected_days])
                available_days_text = ", ".join(
                    [day.strip().title() for day in settings.lunch_days]
                )

                await query.edit_message_text(
                    messages.ENROLL_SUCCESS_TEMPLATE.format(
                        name=user.full_name,
                        email=user.email,
                        diet=user.dietary_preference.value.title(),
                        days=days_text,
                        reminder_time=settings.lunch_reminder_time,
                        days_list=available_days_text,
                    ).strip()
                )
            else:
                await query.edit_message_text(messages.ENROLL_FAILED.strip())

            # Clear user data
            context.user_data.clear()
            return ConversationHandler.END

        # Toggle day selection
        day_name = query.data.replace("day_", "")

        if day_name in selected_days:
            selected_days.remove(day_name)
        else:
            selected_days.append(day_name)

        user_data["selected_days"] = selected_days

        # Update keyboard to show selected days
        reply_markup = self._build_days_keyboard(selected_days)

        await query.edit_message_text(
            query.message.text,
            reply_markup=reply_markup,
        )

        return EnrollmentStates.DAYS

    async def cancel_enrollment(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        context.user_data.clear()
        await update.message.reply_text(messages.ENROLLMENT_CANCELLED.strip())
        return ConversationHandler.END

    async def unenroll_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        user_id = update.effective_user.id

        if db_manager.remove_user(user_id):
            await update.message.reply_text(messages.UNENROLL_SUCCESS.strip())
        else:
            await update.message.reply_text(messages.UNENROLL_FAILURE.strip())

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Exception while handling an update: {context.error}")
        if update:
            logger.error(f"Update {update} caused error {context.error}")

    async def send_lunch_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        context.bot_data[LUNCH_CONFIRMATION_KEY]["positive_response"] = set()
        context.bot_data[LUNCH_CONFIRMATION_KEY]["negative_response"] = set()
        context.bot_data[LUNCH_CONFIRMATION_KEY]["window_open"] = True
        users = db_manager.get_enrolled_users()

        async def send_reminder(user):
            try:
                keyboard = [
                    [
                        InlineKeyboardButton("👍 Yes", callback_data="lunch_yes"),
                        InlineKeyboardButton("👎 No", callback_data="lunch_no"),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=messages.LUNCH_CONFIRMATION_TEMPLATE.strip(),
                    reply_markup=reply_markup,
                )
            except Exception as e:
                logger.error(f"Failed to send reminder to {user.telegram_id}")
                logger.exception(e)

        tasks = [send_reminder(user) for user in users]

        await asyncio.gather(*tasks)

    async def handle_lunch_response(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        id = update.effective_user.id
        query = update.callback_query
        await query.answer()
        response = query.data
        if context.bot_data[LUNCH_CONFIRMATION_KEY]["window_open"]:
            if response == "lunch_yes":
                context.bot_data[LUNCH_CONFIRMATION_KEY]["positive_response"].add(id)
                await query.edit_message_text(messages.LUNCH_CONFIRMATION_YES.strip())
            elif response == "lunch_no":
                context.bot_data[LUNCH_CONFIRMATION_KEY]["negative_response"].add(id)
                await query.edit_message_text(messages.LUNCH_CONFIRMATION_NO.strip())
        else:
            await query.edit_message_text(messages.LUNCH_CONFIRMATION_EXPIRED.strip())

    async def process_lunch_bookings(self, context: ContextTypes.DEFAULT_TYPE):
        context.bot_data[LUNCH_CONFIRMATION_KEY]["window_open"] = False
        yes_responders = context.bot_data[LUNCH_CONFIRMATION_KEY]["positive_response"]
        no_responders = context.bot_data[LUNCH_CONFIRMATION_KEY]["negative_response"]
        users = db_manager.get_enrolled_users()
        # Get what day of the week is tomorrow
        tomorrow = (datetime.today() + timedelta(days=1)).strftime("%A").lower()

        tasks = []

        for user in users:

            async def process_user(user=user):
                try:
                    if user.telegram_id in yes_responders:
                        logger.info(
                            f"Booking lunch for user {user.telegram_id} ({user.full_name})"
                        )
                        await self.book_lunch(user.email, user.dietary_preference)
                    elif user.telegram_id in no_responders:
                        logger.info(
                            f"User {user.telegram_id} ({user.full_name}) has not opted for lunch tomorrow"
                        )
                    else:
                        if tomorrow in user.preferred_days:
                            await context.bot.send_message(
                                chat_id=user.telegram_id,
                                text=messages.LUNCH_TIMEOUT_OPT_IN.strip(),
                            )
                            logger.info(
                                f"Booking lunch for user {user.telegram_id} ({user.full_name})"
                            )
                            await self.book_lunch(user.email, user.dietary_preference)
                        else:
                            await context.bot.send_message(
                                chat_id=user.telegram_id,
                                text=messages.LUNCH_TIMEOUT_OPT_OUT.strip(),
                            )
                            logger.info(
                                f"User {user.telegram_id} ({user.full_name}) has not opted for lunch tomorrow"
                            )
                except Exception as e:
                    logger.error(
                        f"Failed to book lunch for user {user.telegram_id} ({user.full_name})"
                    )
                    logger.exception(e)

            tasks.append(process_user())

        await asyncio.gather(*tasks)

    async def book_lunch(self, email: str, dietary_preference: DietaryPreference):
        browser_automator = BrowserAutomator()
        await browser_automator.run_all(settings.form_url, email, dietary_preference)

    def run(self):
        """Run the bot."""
        self.application.run_polling()
