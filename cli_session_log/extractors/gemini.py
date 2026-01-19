"""Gemini conversation extractor."""

import json
from pathlib import Path
from typing import Optional

from ..constants import DEFAULT_MESSAGE_LIMIT, MESSAGE_TRUNCATE_LENGTH
from ..exceptions import ExtractorError
from ..logging_config import get_logger
from .base import BaseExtractor, Message

logger = get_logger("extractors.gemini")


class GeminiExtractor(BaseExtractor):
    """Extract conversations from Gemini session files."""

    def find_latest_session(self) -> Optional[Path]:
        """Find the latest Gemini session file.

        Returns:
            Path to the latest session JSON file
        """
        if not self.base_dir.exists():
            logger.debug("Gemini tmp dir does not exist: %s", self.base_dir)
            return None

        # Find project directories with chats subdirectory
        project_dirs = [
            d for d in self.base_dir.iterdir()
            if d.is_dir() and (d / "chats").exists()
        ]
        if not project_dirs:
            logger.debug("No project directories with chats found in %s", self.base_dir)
            return None

        # Find the latest session file across all projects
        latest_file: Optional[Path] = None
        latest_mtime = 0.0

        for project_dir in project_dirs:
            chats_dir = project_dir / "chats"
            for session_file in chats_dir.glob("session-*.json"):
                try:
                    mtime = session_file.stat().st_mtime
                    if mtime > latest_mtime:
                        latest_mtime = mtime
                        latest_file = session_file
                except OSError as e:
                    logger.debug("Failed to stat %s: %s", session_file, e)
                    continue

        if latest_file:
            logger.debug("Found latest Gemini session: %s", latest_file)
        return latest_file

    def extract_messages(self, session_path: Path, limit: int = DEFAULT_MESSAGE_LIMIT) -> list[Message]:
        """Extract messages from Gemini session JSON file.

        Args:
            session_path: Path to the session JSON file
            limit: Maximum number of messages to return

        Returns:
            List of Message objects (last N messages)

        Raises:
            ExtractorError: If file cannot be read or parsed
        """
        messages: list[Message] = []

        try:
            with open(session_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Gemini session JSON %s: %s", session_path, e)
            raise ExtractorError(f"Invalid JSON: {e}", source=str(session_path))
        except OSError as e:
            logger.error("Failed to read Gemini session file %s: %s", session_path, e)
            raise ExtractorError(f"Failed to read file: {e}", source=str(session_path))

        raw_messages = data.get("messages", [])
        if not isinstance(raw_messages, list):
            logger.warning("Unexpected messages format in %s", session_path)
            return []

        for msg in raw_messages:
            message = self._parse_message(msg)
            if message:
                messages.append(message.truncate(MESSAGE_TRUNCATE_LENGTH))

        logger.info(
            "Extracted %d messages from Gemini session %s",
            len(messages), session_path.name
        )
        return messages[-limit:]

    def _parse_message(self, msg: dict) -> Optional[Message]:
        """Parse a single message entry.

        Args:
            msg: Message dictionary from session file

        Returns:
            Message object or None if not a conversation message
        """
        msg_type = msg.get("type", "")
        content = msg.get("content", "")

        if not content or not isinstance(content, str):
            return None

        if msg_type == "user":
            return Message(
                role="User",
                content=content,
                timestamp=msg.get("timestamp", "")
            )
        elif msg_type == "model":
            return Message(
                role="AI",
                content=content,
                timestamp=msg.get("timestamp", "")
            )

        return None
