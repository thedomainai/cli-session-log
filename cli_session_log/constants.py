"""Application-wide constants.

This module centralizes magic numbers and configuration values
to improve maintainability and provide single source of truth.
"""

# Session Management
SESSION_ID_LENGTH = 8  # Length of hex session ID
SESSION_FILE_VERSION = "1.0"

# Message Processing
MESSAGE_TRUNCATE_LENGTH = 1000  # Max characters for message content
MESSAGE_HASH_LENGTH = 16  # Length of truncated SHA256 hash for deduplication
DEFAULT_MESSAGE_LIMIT = 50  # Default number of messages to extract

# File Locking
LOCK_TIMEOUT_SECONDS = 10  # Timeout for file lock acquisition

# Session Status Values
STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"
STATUS_ARCHIVED = "archived"
VALID_STATUSES = (STATUS_ACTIVE, STATUS_COMPLETED, STATUS_ARCHIVED)

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
