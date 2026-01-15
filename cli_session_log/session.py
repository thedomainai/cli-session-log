"""Session management logic."""

import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    raise ImportError("Missing dependency: pyyaml. Install with: pip install pyyaml")


def now_iso() -> str:
    """Return current datetime in ISO format."""
    return datetime.now().replace(microsecond=0).isoformat()


def generate_session_id() -> str:
    """Generate a short session ID (8 characters)."""
    return uuid.uuid4().hex[:8]


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---\n"):
        return {}, content

    end_match = re.search(r"\n---\n", content[4:])
    if not end_match:
        return {}, content

    yaml_end = end_match.start() + 4
    yaml_str = content[4:yaml_end]
    body = content[yaml_end + 5:]

    try:
        frontmatter = yaml.safe_load(yaml_str) or {}
    except yaml.YAMLError:
        frontmatter = {}

    return frontmatter, body


def serialize_frontmatter(frontmatter: dict, body: str) -> str:
    """Serialize frontmatter and body to markdown content."""
    yaml_str = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_str}---\n{body}"


class SessionManager:
    """Manage CLI sessions stored as Markdown files."""

    def __init__(self, sessions_dir: Optional[Path] = None):
        """Initialize SessionManager.

        Args:
            sessions_dir: Directory to store sessions. Defaults to ./sessions
        """
        if sessions_dir is None:
            sessions_dir = Path.cwd() / "sessions"
        self.sessions_dir = Path(sessions_dir)

    def _get_month_dir(self) -> Path:
        """Get the current month's session directory."""
        month_str = datetime.now().strftime("%Y-%m")
        month_dir = self.sessions_dir / month_str
        month_dir.mkdir(parents=True, exist_ok=True)
        return month_dir

    def find_session(self, session_id: str) -> Optional[Path]:
        """Find a session file by ID (partial match supported)."""
        if not self.sessions_dir.exists():
            return None

        for month_dir in self.sessions_dir.iterdir():
            if not month_dir.is_dir():
                continue
            for session_file in month_dir.glob("session-*.md"):
                if session_id in session_file.stem:
                    return session_file
        return None

    def list_sessions(self, status_filter: Optional[str] = None) -> list[dict]:
        """List all sessions, optionally filtered by status."""
        sessions = []
        if not self.sessions_dir.exists():
            return sessions

        for month_dir in sorted(self.sessions_dir.iterdir(), reverse=True):
            if not month_dir.is_dir():
                continue
            for session_file in sorted(month_dir.glob("session-*.md"), reverse=True):
                content = session_file.read_text(encoding="utf-8")
                fm, _ = parse_frontmatter(content)

                if status_filter and fm.get("status") != status_filter:
                    continue

                sessions.append({
                    "id": fm.get("session_id", "unknown"),
                    "title": fm.get("title", "Untitled"),
                    "status": fm.get("status", "unknown"),
                    "created_at": fm.get("created_at", ""),
                    "updated_at": fm.get("updated_at", ""),
                    "path": session_file,
                })

        return sessions

    def create_session(self, title: Optional[str] = None) -> tuple[str, Path]:
        """Create a new session.

        Returns:
            Tuple of (session_id, file_path)
        """
        session_id = generate_session_id()
        title = title or f"Session {session_id}"
        now = now_iso()

        frontmatter = {
            "session_id": session_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "status": "active",
            "tags": [],
        }

        body = f"""
# Session: {title}

## Tasks

## Conversation Log

"""

        content = serialize_frontmatter(frontmatter, body)

        month_dir = self._get_month_dir()
        session_file = month_dir / f"session-{session_id}.md"
        session_file.write_text(content, encoding="utf-8")

        return session_id, session_file

    def add_log(self, session_id: str, message: str, role: str = "User") -> None:
        """Add a log entry to a session.

        Args:
            session_id: Session ID
            message: Log message
            role: "User" or "AI"
        """
        session_file = self.find_session(session_id)
        if not session_file:
            raise ValueError(f"Session not found: {session_id}")

        content = session_file.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"\n### {timestamp}\n**{role}**: {message}\n"

        body = body.rstrip() + log_entry + "\n"
        fm["updated_at"] = now_iso()

        content = serialize_frontmatter(fm, body)
        session_file.write_text(content, encoding="utf-8")

    def add_task(self, session_id: str, task_text: str) -> None:
        """Add a task to a session."""
        session_file = self.find_session(session_id)
        if not session_file:
            raise ValueError(f"Session not found: {session_id}")

        content = session_file.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)

        task_line = f"- [ ] {task_text}\n"

        tasks_match = re.search(r"(## Tasks\n)", body)
        if tasks_match:
            insert_pos = tasks_match.end()
            body = body[:insert_pos] + task_line + body[insert_pos:]
        else:
            body = "## Tasks\n" + task_line + "\n" + body

        fm["updated_at"] = now_iso()
        content = serialize_frontmatter(fm, body)
        session_file.write_text(content, encoding="utf-8")

    def complete_task(self, session_id: str, task_num: int) -> None:
        """Mark a task as completed."""
        session_file = self.find_session(session_id)
        if not session_file:
            raise ValueError(f"Session not found: {session_id}")

        content = session_file.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)

        lines = body.split("\n")
        task_count = 0

        for i, line in enumerate(lines):
            if re.match(r"^- \[ \] ", line):
                task_count += 1
                if task_count == task_num:
                    lines[i] = line.replace("- [ ] ", "- [x] ", 1)
                    break
        else:
            raise ValueError(f"Task {task_num} not found")

        body = "\n".join(lines)
        fm["updated_at"] = now_iso()
        content = serialize_frontmatter(fm, body)
        session_file.write_text(content, encoding="utf-8")

    def list_tasks(self, session_id: str) -> list[dict]:
        """List tasks in a session."""
        session_file = self.find_session(session_id)
        if not session_file:
            raise ValueError(f"Session not found: {session_id}")

        content = session_file.read_text(encoding="utf-8")
        _, body = parse_frontmatter(content)

        tasks = []
        task_num = 0
        for line in body.split("\n"):
            if re.match(r"^- \[[ x]\] ", line):
                task_num += 1
                done = "[x]" in line
                text = re.sub(r"^- \[[ x]\] ", "", line)
                tasks.append({"num": task_num, "done": done, "text": text})

        return tasks

    def set_status(self, session_id: str, status: str) -> str:
        """Change session status.

        Returns:
            Old status
        """
        valid_statuses = ["active", "paused", "completed"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Choose from: {', '.join(valid_statuses)}")

        session_file = self.find_session(session_id)
        if not session_file:
            raise ValueError(f"Session not found: {session_id}")

        content = session_file.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)

        old_status = fm.get("status", "unknown")
        fm["status"] = status
        fm["updated_at"] = now_iso()

        content = serialize_frontmatter(fm, body)
        session_file.write_text(content, encoding="utf-8")

        return old_status

    def get_session(self, session_id: str) -> tuple[dict, str]:
        """Get session frontmatter and body."""
        session_file = self.find_session(session_id)
        if not session_file:
            raise ValueError(f"Session not found: {session_id}")

        content = session_file.read_text(encoding="utf-8")
        return parse_frontmatter(content)

    def get_session_content(self, session_id: str) -> str:
        """Get full session content."""
        session_file = self.find_session(session_id)
        if not session_file:
            raise ValueError(f"Session not found: {session_id}")

        return session_file.read_text(encoding="utf-8")
