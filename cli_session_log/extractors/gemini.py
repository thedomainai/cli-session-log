"""Gemini conversation extractor."""

import json
import sys
from pathlib import Path
from typing import Optional

from .base import BaseExtractor, Message


class GeminiExtractor(BaseExtractor):
    """Extract conversations from Gemini session files."""

    def find_latest_session(self) -> Optional[Path]:
        """Find the latest Gemini session file.

        Returns:
            Path to the latest session JSON file
        """
        if not self.base_dir.exists():
            return None

        # Find project directories with chats subdirectory
        project_dirs = [
            d for d in self.base_dir.iterdir()
            if d.is_dir() and (d / "chats").exists()
        ]
        if not project_dirs:
            return None

        # Find the latest session file across all projects
        latest_file: Optional[Path] = None
        latest_mtime = 0.0

        for project_dir in project_dirs:
            chats_dir = project_dir / "chats"
            for session_file in chats_dir.glob("session-*.json"):
                mtime = session_file.stat().st_mtime
                if mtime > latest_mtime:
                    latest_mtime = mtime
                    latest_file = session_file

        return latest_file

    def extract_messages(self, session_path: Path, limit: int = 50) -> list[Message]:
        """Extract messages from Gemini session JSON file.

        Args:
            session_path: Path to the session JSON file
            limit: Maximum number of messages to return

        Returns:
            List of Message objects (last N messages)
        """
        messages: list[Message] = []

        try:
            with open(session_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for msg in data.get("messages", []):
                message = self._parse_message(msg)
                if message:
                    messages.append(message.truncate(1000))

        except json.JSONDecodeError as e:
            print(f"Error parsing Gemini session JSON: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error reading Gemini session: {e}", file=sys.stderr)

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
