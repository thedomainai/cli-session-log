"""Base class for conversation extractors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..constants import DEFAULT_MESSAGE_LIMIT, MESSAGE_TRUNCATE_LENGTH
from ..logging_config import get_logger

logger = get_logger("extractors.base")


@dataclass
class Message:
    """Represents a conversation message."""

    role: str  # "User" or "AI"
    content: str
    timestamp: str = ""

    def truncate(self, max_length: int = MESSAGE_TRUNCATE_LENGTH) -> "Message":
        """Return a new Message with truncated content."""
        if len(self.content) <= max_length:
            return self
        return Message(
            role=self.role,
            content=self.content[:max_length],
            timestamp=self.timestamp
        )


class BaseExtractor(ABC):
    """Abstract base class for conversation extractors."""

    def __init__(self, base_dir: Path):
        """Initialize extractor with base directory.

        Args:
            base_dir: Base directory where sessions are stored
        """
        self.base_dir = base_dir
        logger.debug("Initialized %s with base_dir: %s", self.__class__.__name__, base_dir)

    @abstractmethod
    def find_latest_session(self, cwd: Optional[str] = None) -> Optional[Path]:
        """Find the most recent session file.

        Args:
            cwd: Optional working directory to filter sessions by

        Returns:
            Path to the latest session file, or None if not found
        """
        pass

    @abstractmethod
    def extract_messages(self, session_path: Path, limit: int = DEFAULT_MESSAGE_LIMIT) -> list[Message]:
        """Extract messages from a session file.

        Args:
            session_path: Path to the session file
            limit: Maximum number of messages to return

        Returns:
            List of Message objects
        """
        pass

    def extract_latest(self, limit: int = DEFAULT_MESSAGE_LIMIT, cwd: Optional[str] = None) -> list[Message]:
        """Extract messages from the latest session.

        Args:
            limit: Maximum number of messages to return
            cwd: Optional working directory to filter sessions by

        Returns:
            List of Message objects, empty if no session found
        """
        session_path = self.find_latest_session(cwd=cwd)
        if session_path is None:
            logger.info("No session found in %s for cwd: %s", self.base_dir, cwd or "(any)")
            return []
        logger.debug("Extracting from latest session: %s", session_path)
        return self.extract_messages(session_path, limit)
