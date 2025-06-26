import logging
from enum import IntEnum, auto

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler

from . import messages
from .config import settings
from .database import db_manager

logger = logging.getLogger(__name__)


class EnrollmentStates(IntEnum):
    NAME = auto()
    EMAIL = auto()
    DIETARY_PREFERENCE = auto()
    DAYS = auto()


class LunchBuddyBot:

    def __init__(self):
        self.application = (
            Application.builder().token(settings.telegram_bot_token).build()
        )
        self.setup_handlers()
        self.setup_schedulers()

    def setup_handlers(self):
        # Command Handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))

        # Conversation Handlers
        self.application.add_handler(ConversationHandler())

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
        user = db_manager.get_user(update.effective_user.id)

        if not user:
            await update.message.reply_text(messages.STATUS_NOT_ENROLLED.strip())
            return

        await update.message.reply_text(
            messages.STATUS_MESSAGE_TEMPLATE.format(
                name=user.full_name,
                email=user.email,
                diet=user.dietary_preference.value.title(),
                days=", ".join(user.preferred_days),
            ).strip()
        )
