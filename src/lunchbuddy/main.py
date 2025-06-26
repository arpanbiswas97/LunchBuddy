import logging
import sys

from .bot import LunchBuddyBot
from .database import db_manager
from .utils import setup_logging


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        logger.info("🚀 LunchBuddy server starting...")

        # Initialize database
        logger.info("Initializing database...")
        db_manager.init_database()
        logger.info("Database initialized successfully")

        # Create bot instance
        logger.info("Creating bot instance...")
        bot_instance = LunchBuddyBot()

        # Run the bot
        logger.info("Starting bot...")
        bot_instance.run()

    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error("Application error")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
