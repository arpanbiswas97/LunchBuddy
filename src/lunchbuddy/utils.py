import logging

from .config import settings


def setup_logging():
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
    )
