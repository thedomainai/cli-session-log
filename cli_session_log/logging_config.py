"""Logging configuration for cli-session-log."""

import logging
import sys
from pathlib import Path
from typing import Optional

# Package logger
logger = logging.getLogger("cli_session_log")


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    debug: bool = False
) -> None:
    """Configure logging for the application.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional file path for logging
        debug: If True, set level to DEBUG
    """
    if debug:
        level = logging.DEBUG

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Configure root logger for package
    logger.setLevel(level)
    logger.handlers.clear()
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.debug("Logging configured: level=%s, file=%s", level, log_file)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"cli_session_log.{name}")
