"""
logging_config.py
-----------------
Configures structured logging for the trading bot.

Logs are written to BOTH:
  - The terminal (INFO level, human-readable)
  - logs/trading_bot.log (DEBUG level, full detail for auditing)

Usage:
    from bot.logging_config import get_logger
    logger = get_logger(__name__)
"""

import logging
import logging.handlers
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

CONSOLE_FORMAT = "%(levelname)-8s | %(message)s"
FILE_FORMAT    = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT    = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(log_level: str = "INFO") -> None:
    """
    Call once at startup to configure root logger.

    Parameters
    ----------
    log_level : str
        Console verbosity (DEBUG / INFO / WARNING / ERROR).
    """
    global _configured
    if _configured:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)   # capture everything; handlers filter

    # ── Console handler (brief) ─────────────────────────────────────────────
    console = logging.StreamHandler()
    console.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    console.setFormatter(logging.Formatter(CONSOLE_FORMAT))

    # ── Rotating file handler (full detail, 5 MB max, 3 backups) ───────────
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(FILE_FORMAT, datefmt=DATE_FORMAT))

    root.addHandler(console)
    root.addHandler(fh)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger (call setup_logging first)."""
    return logging.getLogger(name)
