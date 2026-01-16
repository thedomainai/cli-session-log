"""Claude Code conversation extractor."""

import json
from pathlib import Path
from typing import Optional

from ..exceptions import ExtractorError
from ..logging_config import get_logger
from .base import BaseExtractor, Message

logger = get_logger("extractors.claude")


class ClaudeExtractor(BaseExtractor):
    """Extract conversations from Claude Code session files."""

    def find_latest_session(self, cwd: Optional[str] = None) -> Optional[Path]:
        """Find the latest Claude Code session file.

        Args:
            cwd: Optional working directory to filter by

        Returns:
            Path to the latest .jsonl session file
        """
        if not self.base_dir.exists():
            logger.debug("Claude projects dir does not exist: %s", self.base_dir)
            return None

        if cwd:
            # Convert cwd to Claude's directory naming format
            dir_name = cwd.replace("/", "-")
            if dir_name.startswith("-"):
                dir_name = dir_name[1:]
            project_dir = self.base_dir / dir_name
        else:
            # Find most recently modified project directory
            project_dirs = [d for d in self.base_dir.iterdir() if d.is_dir()]
            if not project_dirs:
                logger.debug("No project directories found in %s", self.base_dir)
                return None
            project_dir = max(project_dirs, key=lambda d: d.stat().st_mtime)

        if not project_dir.exists():
            logger.debug("Project directory does not exist: %s", project_dir)
            return None

        # Find most recent .jsonl file
        jsonl_files = list(project_dir.glob("*.jsonl"))
        if not jsonl_files:
            logger.debug("No JSONL files found in %s", project_dir)
            return None

        latest = max(jsonl_files, key=lambda f: f.stat().st_mtime)
        logger.debug("Found latest Claude session: %s", latest)
        return latest

    def extract_messages(self, session_path: Path, limit: int = 50) -> list[Message]:
        """Extract messages from Claude Code JSONL file.

        Args:
            session_path: Path to the .jsonl file
            limit: Maximum number of messages to return

        Returns:
            List of Message objects (last N messages)

        Raises:
            ExtractorError: If file cannot be read or parsed
        """
        messages: list[Message] = []
        errors_count = 0

        try:
            with open(session_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        entry = json.loads(line.strip())
                        message = self._parse_entry(entry)
                        if message:
                            messages.append(message.truncate(1000))
                    except json.JSONDecodeError as e:
                        errors_count += 1
                        if errors_count <= 3:  # Log first few errors
                            logger.debug(
                                "JSON parse error at line %d in %s: %s",
                                line_num, session_path.name, e
                            )
                        continue

        except OSError as e:
            logger.error("Failed to read Claude session file %s: %s", session_path, e)
            raise ExtractorError(f"Failed to read file: {e}", source=str(session_path))

        if errors_count > 0:
            logger.warning(
                "Encountered %d JSON parse errors in %s",
                errors_count, session_path.name
            )

        logger.info(
            "Extracted %d messages from Claude session %s",
            len(messages), session_path.name
        )
        return messages[-limit:]

    def _parse_entry(self, entry: dict) -> Optional[Message]:
        """Parse a single JSONL entry into a Message.

        Args:
            entry: Parsed JSON entry

        Returns:
            Message object or None if not a conversation message
        """
        # User message
        if entry.get("type") == "user" and "message" in entry:
            msg = entry["message"]
            if msg.get("role") == "user" and msg.get("content"):
                content = msg["content"]
                if isinstance(content, str):
                    return Message(
                        role="User",
                        content=content,
                        timestamp=entry.get("timestamp", "")
                    )

        # Assistant message
        elif entry.get("type") == "assistant" or (
            "message" in entry and entry.get("message", {}).get("role") == "assistant"
        ):
            msg = entry.get("message", entry)
            content_parts = msg.get("content", [])
            if isinstance(content_parts, list):
                text_parts = [
                    p.get("text", "")
                    for p in content_parts
                    if p.get("type") == "text"
                ]
                if text_parts:
                    return Message(
                        role="AI",
                        content=" ".join(text_parts),
                        timestamp=entry.get("timestamp", "")
                    )

        return None
