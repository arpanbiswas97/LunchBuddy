"""Main entry point for LunchBuddy bot."""

import logging
import os
import sys
import threading
from pathlib import Path

from telegram import Bot

from .bot import LunchBuddyBot
from .scheduler import LunchScheduler
from .database import db_manager
from .config import settings

# Setup logging
def setup_logging():
    """Setup logging configuration."""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(settings.log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main application entry point."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting LunchBuddy application...")
        
        # Initialize database
        logger.info("Initializing database...")
        db_manager.init_database()
        logger.info("Database initialized successfully")
        
        # Create bot instance
        logger.info("Creating bot instance...")
        bot_instance = LunchBuddyBot()
        
        # Create scheduler
        logger.info("Creating scheduler...")
        telegram_bot = Bot(token=settings.telegram_bot_token)
        scheduler = LunchScheduler(telegram_bot)
        
        # Start scheduler in a separate thread
        logger.info("Starting scheduler thread...")
        scheduler_thread = threading.Thread(target=scheduler.run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Run the bot
        logger.info("Starting bot...")
        bot_instance.run()
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 