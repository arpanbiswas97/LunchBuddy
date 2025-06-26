import logging
import re
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

logger = logging.getLogger(__name__)


class EnrollmentStates(IntEnum):
    NAME = auto()
    EMAIL = auto()
    DIETARY_PREFERENCE = auto()
    DAYS = auto()


# User data keys
USER_DATA_KEY = "user_data"


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
                enrolled=user.is_enrolled
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

    def run(self):
        """Run the bot."""
        self.application.run_polling()
