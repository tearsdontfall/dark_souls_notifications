from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from notifications.config import CACHE_DIR

LOG_PATH = CACHE_DIR / "app.log"


def setup_logging() -> logging.Logger:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("dark_souls_meetings")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=256_000,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(handler)
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger("dark_souls_meetings")
