"""Session management logic."""

import hashlib
import re
import secrets
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Literal, Optional

from filelock import FileLock, Timeout

try:
    import yaml
except ImportError:
    raise ImportError("Missing dependency: pyyaml. Install with: pip install pyyaml")

from .exceptions import (
    SessionNotFoundError,
    SessionParseError,
    SessionWriteError,
)
from .logging_config import get_logger

logger = get_logger("session")

# Type aliases
SessionStatus = Literal["active", "paused", "completed"]
VALID_STATUSES: tuple[SessionStatus, ...] = ("active", "paused", "completed")


def now_iso() -> str:
    """Return current datetime in ISO format."""
    return datetime.now().replace(microsecond=0).isoformat()


def generate_session_id() -> str:
    """Generate a cryptographically secure session ID (8 characters)."""
    return secrets.token_hex(4)


def compute_message_hash(role: str, content: str) -> str:
    """Compute hash for a message to detect duplicates."""
    data = f"{role}:{content}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:16]


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Markdown content with optional frontmatter

    Returns:
        Tuple of (frontmatter dict, body content)

    Raises:
        SessionParseError: If YAML parsing fails critically
    """
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
    except yaml.YAMLError as e:
        logger.warning("Failed to parse YAML frontmatter: %s", e)
        # Return empty but don't lose the body
        frontmatter = {}

    return frontmatter, body


def serialize_frontmatter(frontmatter: dict[str, Any], body: str) -> str:
    """Serialize frontmatter and body to markdown content."""
    yaml_str = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_str}---\n{body}"


class SessionManager:
    """Manage CLI sessions stored as Markdown files."""

    LOCK_TIMEOUT = 10  # seconds

    def __init__(self, sessions_dir: Optional[Path] = None):
        """Initialize SessionManager.

        Args:
            sessions_dir: Directory to store sessions. Defaults to ./sessions
        """
        if sessions_dir is None:
            sessions_dir = Path.cwd() / "sessions"
        self.sessions_dir = Path(sessions_dir)
        logger.debug("SessionManager initialized: %s", self.sessions_dir)

    @contextmanager
    def _lock_session(self, session_file: Path) -> Iterator[None]:
        """Acquire file lock for session file.

        Args:
            session_file: Path to session file

        Yields:
            None when lock is acquired

        Raises:
            SessionWriteError: If lock cannot be acquired
        """
        lock_file = session_file.with_suffix(".md.lock")
        lock = FileLock(lock_file, timeout=self.LOCK_TIMEOUT)

        try:
            with lock:
                logger.debug("Acquired lock: %s", lock_file)
                yield
        except Timeout:
            logger.error("Failed to acquire lock: %s", lock_file)
            raise SessionWriteError(
                f"Could not acquire lock for session (timeout: {self.LOCK_TIMEOUT}s)",
                path=str(session_file)
            )

    def _get_month_dir(self) -> Path:
        """Get the current month's session directory."""
        month_str = datetime.now().strftime("%Y-%m")
        month_dir = self.sessions_dir / month_str
        month_dir.mkdir(parents=True, exist_ok=True)
        return month_dir

    def find_session(self, session_id: str) -> Optional[Path]:
        """Find a session file by ID (partial match supported).

        Args:
            session_id: Full or partial session ID

        Returns:
            Path to session file or None if not found
        """
        if not self.sessions_dir.exists():
            logger.debug("Sessions directory does not exist: %s", self.sessions_dir)
            return None

        matches: list[Path] = []

        for month_dir in self.sessions_dir.iterdir():
            if not month_dir.is_dir():
                continue
            for session_file in month_dir.glob("session-*.md"):
                if session_id in session_file.stem:
                    matches.append(session_file)

        if not matches:
            return None

        if len(matches) > 1:
            logger.warning(
                "Multiple sessions match ID '%s': %s",
                session_id,
                [m.stem for m in matches]
            )

        # Return most recently modified match
        return max(matches, key=lambda p: p.stat().st_mtime)

    def list_sessions(self, status_filter: Optional[str] = None) -> list[dict[str, Any]]:
        """List all sessions, optionally filtered by status.

        Args:
            status_filter: Filter by status (active/paused/completed)

        Returns:
            List of session metadata dicts
        """
        sessions: list[dict[str, Any]] = []
        if not self.sessions_dir.exists():
            return sessions

        for month_dir in sorted(self.sessions_dir.iterdir(), reverse=True):
            if not month_dir.is_dir():
                continue
            for session_file in sorted(month_dir.glob("session-*.md"), reverse=True):
                try:
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
                except OSError as e:
                    logger.warning("Failed to read session file %s: %s", session_file, e)
                    continue

        return sessions

    def create_session(self, title: Optional[str] = None) -> tuple[str, Path]:
        """Create a new session.

        Args:
            title: Session title

        Returns:
            Tuple of (session_id, file_path)

        Raises:
            SessionWriteError: If file cannot be created
        """
        session_id = generate_session_id()
        title = title or f"Session {session_id}"
        now = now_iso()

        frontmatter: dict[str, Any] = {
            "version": "1.0",
            "session_id": session_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "status": "active",
            "tags": [],
            "imported_hashes": [],  # For duplicate detection
        }

        body = f"""
# Session: {title}

## Tasks

## Conversation Log

"""

        content = serialize_frontmatter(frontmatter, body)

        month_dir = self._get_month_dir()
        session_file = month_dir / f"session-{session_id}.md"

        try:
            session_file.write_text(content, encoding="utf-8")
            logger.info("Created session: %s at %s", session_id, session_file)
        except OSError as e:
            logger.error("Failed to create session file: %s", e)
            raise SessionWriteError(f"Failed to create session: {e}", path=str(session_file))

        return session_id, session_file

    def add_log(
        self,
        session_id: str,
        message: str,
        role: str = "User",
        check_duplicate: bool = False
    ) -> bool:
        """Add a log entry to a session.

        Args:
            session_id: Session ID
            message: Log message
            role: "User" or "AI"
            check_duplicate: If True, skip duplicate messages

        Returns:
            True if message was added, False if skipped (duplicate)

        Raises:
            SessionNotFoundError: If session not found
            SessionWriteError: If file cannot be written
        """
        session_file = self.find_session(session_id)
        if not session_file:
            raise SessionNotFoundError(session_id)

        with self._lock_session(session_file):
            try:
                content = session_file.read_text(encoding="utf-8")
            except OSError as e:
                raise SessionWriteError(f"Failed to read session: {e}", path=str(session_file))

            fm, body = parse_frontmatter(content)

            # Duplicate detection
            if check_duplicate:
                msg_hash = compute_message_hash(role, message)
                imported_hashes = fm.get("imported_hashes", [])
                if msg_hash in imported_hashes:
                    logger.debug("Skipping duplicate message: %s", msg_hash)
                    return False
                imported_hashes.append(msg_hash)
                fm["imported_hashes"] = imported_hashes

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"\n### {timestamp}\n**{role}**: {message}\n"

            body = body.rstrip() + log_entry + "\n"
            fm["updated_at"] = now_iso()

            content = serialize_frontmatter(fm, body)

            try:
                session_file.write_text(content, encoding="utf-8")
                logger.debug("Added %s log to session %s", role, session_id)
            except OSError as e:
                raise SessionWriteError(f"Failed to write session: {e}", path=str(session_file))

        return True

    def add_task(self, session_id: str, task_text: str) -> None:
        """Add a task to a session.

        Args:
            session_id: Session ID
            task_text: Task description

        Raises:
            SessionNotFoundError: If session not found
            SessionWriteError: If file cannot be written
        """
        session_file = self.find_session(session_id)
        if not session_file:
            raise SessionNotFoundError(session_id)

        with self._lock_session(session_file):
            try:
                content = session_file.read_text(encoding="utf-8")
            except OSError as e:
                raise SessionWriteError(f"Failed to read session: {e}", path=str(session_file))

            fm, body = parse_frontmatter(content)

            task_line = f"- [ ] {task_text}\n"

            # Find the Tasks section and append at the end of existing tasks
            tasks_section_match = re.search(r"## Tasks\n((?:- \[[ x]\] [^\n]*\n)*)", body)
            if tasks_section_match:
                # Insert after existing tasks
                insert_pos = tasks_section_match.end()
                body = body[:insert_pos] + task_line + body[insert_pos:]
            else:
                body = "## Tasks\n" + task_line + "\n" + body

            fm["updated_at"] = now_iso()
            content = serialize_frontmatter(fm, body)

            try:
                session_file.write_text(content, encoding="utf-8")
                logger.debug("Added task to session %s: %s", session_id, task_text)
            except OSError as e:
                raise SessionWriteError(f"Failed to write session: {e}", path=str(session_file))

    def complete_task(self, session_id: str, task_num: int) -> None:
        """Mark a task as completed.

        Args:
            session_id: Session ID
            task_num: Task number (1-indexed)

        Raises:
            SessionNotFoundError: If session not found
            ValueError: If task not found
            SessionWriteError: If file cannot be written
        """
        session_file = self.find_session(session_id)
        if not session_file:
            raise SessionNotFoundError(session_id)

        with self._lock_session(session_file):
            try:
                content = session_file.read_text(encoding="utf-8")
            except OSError as e:
                raise SessionWriteError(f"Failed to read session: {e}", path=str(session_file))

            fm, body = parse_frontmatter(content)

            lines = body.split("\n")
            task_count = 0
            found = False

            for i, line in enumerate(lines):
                if re.match(r"^- \[ \] ", line):
                    task_count += 1
                    if task_count == task_num:
                        lines[i] = line.replace("- [ ] ", "- [x] ", 1)
                        found = True
                        break

            if not found:
                raise ValueError(f"Task {task_num} not found")

            body = "\n".join(lines)
            fm["updated_at"] = now_iso()
            content = serialize_frontmatter(fm, body)

            try:
                session_file.write_text(content, encoding="utf-8")
                logger.debug("Completed task %d in session %s", task_num, session_id)
            except OSError as e:
                raise SessionWriteError(f"Failed to write session: {e}", path=str(session_file))

    def list_tasks(self, session_id: str) -> list[dict[str, Any]]:
        """List tasks in a session.

        Args:
            session_id: Session ID

        Returns:
            List of task dicts with num, done, and text keys

        Raises:
            SessionNotFoundError: If session not found
        """
        session_file = self.find_session(session_id)
        if not session_file:
            raise SessionNotFoundError(session_id)

        content = session_file.read_text(encoding="utf-8")
        _, body = parse_frontmatter(content)

        tasks: list[dict[str, Any]] = []
        task_num = 0
        for line in body.split("\n"):
            if re.match(r"^- \[[ x]\] ", line):
                task_num += 1
                done = "[x]" in line
                text = re.sub(r"^- \[[ x]\] ", "", line)
                tasks.append({"num": task_num, "done": done, "text": text})

        return tasks

    def set_status(self, session_id: str, status: SessionStatus) -> str:
        """Change session status.

        Args:
            session_id: Session ID
            status: New status

        Returns:
            Old status

        Raises:
            SessionNotFoundError: If session not found
            ValueError: If invalid status
            SessionWriteError: If file cannot be written
        """
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status. Choose from: {', '.join(VALID_STATUSES)}")

        session_file = self.find_session(session_id)
        if not session_file:
            raise SessionNotFoundError(session_id)

        with self._lock_session(session_file):
            try:
                content = session_file.read_text(encoding="utf-8")
            except OSError as e:
                raise SessionWriteError(f"Failed to read session: {e}", path=str(session_file))

            fm, body = parse_frontmatter(content)

            old_status = fm.get("status", "unknown")
            fm["status"] = status
            fm["updated_at"] = now_iso()

            content = serialize_frontmatter(fm, body)

            try:
                session_file.write_text(content, encoding="utf-8")
                logger.info("Changed session %s status: %s -> %s", session_id, old_status, status)
            except OSError as e:
                raise SessionWriteError(f"Failed to write session: {e}", path=str(session_file))

        return old_status

    def get_session(self, session_id: str) -> tuple[dict[str, Any], str]:
        """Get session frontmatter and body.

        Args:
            session_id: Session ID

        Returns:
            Tuple of (frontmatter dict, body content)

        Raises:
            SessionNotFoundError: If session not found
        """
        session_file = self.find_session(session_id)
        if not session_file:
            raise SessionNotFoundError(session_id)

        content = session_file.read_text(encoding="utf-8")
        return parse_frontmatter(content)

    def get_session_content(self, session_id: str) -> str:
        """Get full session content.

        Args:
            session_id: Session ID

        Returns:
            Full markdown content

        Raises:
            SessionNotFoundError: If session not found
        """
        session_file = self.find_session(session_id)
        if not session_file:
            raise SessionNotFoundError(session_id)

        return session_file.read_text(encoding="utf-8")

    def clear_imported_hashes(self, session_id: str) -> None:
        """Clear imported message hashes for a session.

        Args:
            session_id: Session ID

        Raises:
            SessionNotFoundError: If session not found
        """
        session_file = self.find_session(session_id)
        if not session_file:
            raise SessionNotFoundError(session_id)

        with self._lock_session(session_file):
            content = session_file.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(content)
            fm["imported_hashes"] = []
            fm["updated_at"] = now_iso()
            content = serialize_frontmatter(fm, body)
            session_file.write_text(content, encoding="utf-8")
            logger.info("Cleared imported hashes for session %s", session_id)
