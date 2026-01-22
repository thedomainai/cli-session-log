"""Application-wide constants.

This module centralizes magic numbers and configuration values
to improve maintainability and provide single source of truth.
"""

from enum import Enum


class SessionStatus(str, Enum):
    """Valid session statuses.

    Inherits from str to ensure backward compatibility with string comparisons.
    """

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"

    def __str__(self) -> str:
        return self.value


# Session Management
SESSION_ID_LENGTH = 8  # Length of hex session ID
SESSION_FILE_VERSION = "1.0"
SESSION_ID_PATTERN = r"^[a-f0-9]{8}$"  # Valid session ID format (8 hex chars)

# Security Limits
MAX_SESSION_FILE_SIZE = 50 * 1024 * 1024  # 50MB max session file size
MAX_TITLE_LENGTH = 200  # Maximum session title length
MAX_TASK_TEXT_LENGTH = 1000  # Maximum task text length
MAX_MESSAGE_LENGTH = 100000  # Maximum log message length

# Message Processing
MESSAGE_TRUNCATE_LENGTH = 1000  # Max characters for message content
MESSAGE_HASH_LENGTH = 16  # Length of truncated SHA256 hash for deduplication
DEFAULT_MESSAGE_LIMIT = 50  # Default number of messages to extract

# File Locking
LOCK_TIMEOUT_SECONDS = 10  # Timeout for file lock acquisition

# Session Status Values (legacy constants for backward compatibility)
STATUS_ACTIVE = SessionStatus.ACTIVE.value
STATUS_PAUSED = SessionStatus.PAUSED.value
STATUS_COMPLETED = SessionStatus.COMPLETED.value
STATUS_ARCHIVED = SessionStatus.ARCHIVED.value
VALID_STATUSES = tuple(s.value for s in SessionStatus)

# AI Types
AI_TYPE_CLAUDE = "claude"
AI_TYPE_GEMINI = "gemini"
SUPPORTED_AI_TYPES = (AI_TYPE_CLAUDE, AI_TYPE_GEMINI)

# CLI Output Formatting
CLI_TABLE_ID_WIDTH = 10
CLI_TABLE_STATUS_WIDTH = 12
CLI_TABLE_TITLE_WIDTH = 30
CLI_TABLE_DATE_WIDTH = 20

# Date/Time Formats
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
MONTH_DIR_FORMAT = "%Y-%m"

# Task Regex Patterns
TASK_SECTION_PATTERN = r"## Tasks\n((?:- \[[ x]\] [^\n]*\n)*)"
TASK_PATTERN_INCOMPLETE = r"^- \[ \] "
TASK_PATTERN_ALL = r"^- \[[ x]\] "
