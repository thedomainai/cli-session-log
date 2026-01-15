"""Claude Code conversation extractor."""

import json
import sys
from pathlib import Path
from typing import Optional

from .base import BaseExtractor, Message


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
                return None
            project_dir = max(project_dirs, key=lambda d: d.stat().st_mtime)

        if not project_dir.exists():
            return None

        # Find most recent .jsonl file
        jsonl_files = list(project_dir.glob("*.jsonl"))
        if not jsonl_files:
            return None

        return max(jsonl_files, key=lambda f: f.stat().st_mtime)

    def extract_messages(self, session_path: Path, limit: int = 50) -> list[Message]:
        """Extract messages from Claude Code JSONL file.

        Args:
            session_path: Path to the .jsonl file
            limit: Maximum number of messages to return

        Returns:
            List of Message objects (last N messages)
        """
        messages: list[Message] = []

        try:
            with open(session_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        message = self._parse_entry(entry)
                        if message:
                            messages.append(message.truncate(1000))
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            print(f"Error reading JSONL: {e}", file=sys.stderr)

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
