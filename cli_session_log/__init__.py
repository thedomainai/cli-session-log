"""CLI Session Log - Manage CLI sessions with conversation logs and task tracking."""

__version__ = "0.2.0"

from .config import Config, get_config, reset_config
from .exceptions import (
    ConfigError,
    ExtractorError,
    PathTraversalError,
    SessionLogError,
    SessionNotFoundError,
    SessionParseError,
    SessionWriteError,
)
from .extractors import BaseExtractor, ClaudeExtractor, GeminiExtractor, Message
from .logging_config import get_logger, setup_logging
from .session import SessionManager

__all__ = [
    # Config
    "Config",
    "get_config",
    "reset_config",
    # Session
    "SessionManager",
    # Extractors
    "BaseExtractor",
    "ClaudeExtractor",
    "GeminiExtractor",
    "Message",
    # Exceptions
    "SessionLogError",
    "SessionNotFoundError",
    "SessionWriteError",
    "SessionParseError",
    "ConfigError",
    "PathTraversalError",
    "ExtractorError",
    # Logging
    "setup_logging",
    "get_logger",
]
