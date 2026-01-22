#!/usr/bin/env python3
"""
Claude Code Hook for session management.

This hook is called by Claude Code on specific events:
- Stop: When the session ends

Supports parallel multi-session management:
- Multiple Claude Code sessions in different directories
- Simultaneous Claude and Gemini sessions

Usage in ~/.claude/settings.json:
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/claude_session_hook.py stop"
          }
        ]
      }
    ]
  }
}
"""

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

from filelock import FileLock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli_session_log.config import get_config
from cli_session_log.constants import AI_TYPE_CLAUDE, AI_TYPE_GEMINI, DATETIME_FORMAT
from cli_session_log.exceptions import ExtractorError, SessionNotFoundError, SessionWriteError
from cli_session_log.extractors import ClaudeExtractor, GeminiExtractor
from cli_session_log.extractors.base import BaseExtractor
from cli_session_log.logging_config import get_logger, setup_logging
from cli_session_log.session import SessionManager

# Setup logging for hook
setup_logging()
logger = get_logger("hook")

# Get configuration
config = get_config()


@dataclass
class SessionState:
    """State for an active session."""
    session_id: str
    ai_type: str
    cwd: str
    start_timestamp: str
    title: Optional[str] = None
    terminal_id: Optional[str] = None  # Cursor terminal ID for multi-terminal support

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, data: str) -> "SessionState":
        parsed = json.loads(data)
        # Handle legacy state files without terminal_id
        if "terminal_id" not in parsed:
            parsed["terminal_id"] = None
        return cls(**parsed)


def ensure_state_dir():
    """Ensure state directory exists."""
    config.ensure_config_dir()
    config.ensure_state_dir()


def get_current_cwd() -> str:
    """Get current working directory."""
    return os.getcwd()


def get_terminal_id() -> Optional[str]:
    """Get terminal ID from environment variable.

    Returns:
        Terminal ID if available (set by Cursor terminal-id extension), None otherwise
    """
    return os.environ.get("CURSOR_TERMINAL_ID")


def get_session_state(ai_type: str, cwd: str, terminal_id: Optional[str] = None) -> Optional[SessionState]:
    """Get session state for a specific AI type and terminal/cwd.

    Priority:
    1. terminal_id parameter (if provided)
    2. CURSOR_TERMINAL_ID environment variable
    3. Fallback to cwd-based lookup

    Args:
        ai_type: AI type (claude/gemini)
        cwd: Working directory (used as fallback)
        terminal_id: Optional terminal ID override

    Returns:
        SessionState if exists, None otherwise
    """
    # Use provided terminal_id or get from environment
    tid = terminal_id or get_terminal_id()

    state_file = config.get_session_state_file(ai_type, cwd, tid)
    if state_file.exists():
        try:
            return SessionState.from_json(state_file.read_text())
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Failed to parse session state: %s", e)
    return None


def set_session_state(state: SessionState) -> None:
    """Save session state atomically.

    Uses temp file + rename pattern to ensure atomic writes.

    Args:
        state: SessionState to save
    """
    ensure_state_dir()
    state_file = config.get_session_state_file(state.ai_type, state.cwd)

    # Atomic write: temp file + rename
    fd, tmp_path = tempfile.mkstemp(dir=state_file.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(state.to_json())
        os.replace(tmp_path, state_file)  # Atomic on POSIX
        logger.debug("Saved session state to %s", state_file)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def clear_session_state(ai_type: str, cwd: str, terminal_id: Optional[str] = None) -> None:
    """Clear session state for a specific AI type and terminal/cwd.

    Args:
        ai_type: AI type (claude/gemini)
        cwd: Working directory
        terminal_id: Optional terminal ID
    """
    # Use provided terminal_id or get from environment
    tid = terminal_id or get_terminal_id()

    state_file = config.get_session_state_file(ai_type, cwd, tid)
    if state_file.exists():
        state_file.unlink()
        logger.debug("Cleared session state: %s", state_file)


def find_session_by_cwd(cwd: str) -> Optional[SessionState]:
    """Find active session by working directory (any AI type).

    Args:
        cwd: Working directory

    Returns:
        SessionState if found, None otherwise
    """
    for ai_type in config.AI_TYPES:
        state = get_session_state(ai_type, cwd)
        if state:
            return state
    return None


def find_session(cwd: Optional[str] = None, terminal_id: Optional[str] = None) -> Optional[SessionState]:
    """Find active session by terminal ID or cwd.

    Priority:
    1. terminal_id parameter
    2. CURSOR_TERMINAL_ID environment variable
    3. cwd-based lookup (fallback)

    Args:
        cwd: Working directory (optional, defaults to current cwd)
        terminal_id: Terminal ID (optional, defaults to CURSOR_TERMINAL_ID env var)

    Returns:
        SessionState if found, None otherwise
    """
    cwd = cwd or get_current_cwd()
    tid = terminal_id or get_terminal_id()

    # Try to find by terminal ID first (if available)
    if tid:
        for ai_type in config.AI_TYPES:
            state = get_session_state(ai_type, cwd, tid)
            if state:
                logger.debug("Found session by terminal_id: %s", tid)
                return state

    # Fallback to cwd-based lookup (for non-Cursor environments or legacy)
    for ai_type in config.AI_TYPES:
        state = get_session_state(ai_type, cwd, terminal_id=None)
        if state:
            logger.debug("Found session by cwd: %s", cwd)
            return state

    return None


def list_all_active_sessions() -> list[SessionState]:
    """List all active sessions across all AI types.

    Returns:
        List of active SessionState objects
    """
    sessions = []
    for state_file in config.list_active_sessions():
        try:
            state = SessionState.from_json(state_file.read_text())
            sessions.append(state)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Failed to parse state file %s: %s", state_file, e)
    return sessions


def cleanup_stale_sessions(max_age_hours: int = 24) -> int:
    """Remove state files older than max_age_hours.

    This helps clean up orphaned sessions from crashes or abnormal exits.

    Args:
        max_age_hours: Maximum age in hours before a session is considered stale

    Returns:
        Number of stale sessions removed
    """
    removed = 0
    for state_file in config.list_active_sessions():
        try:
            state = SessionState.from_json(state_file.read_text())
            start_time = datetime.fromisoformat(state.start_timestamp)
            if datetime.now() - start_time > timedelta(hours=max_age_hours):
                logger.warning("Removing stale session: %s (started %s)", state.session_id, state.start_timestamp)
                state_file.unlink()
                removed += 1
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            # Corrupt state file - remove it
            logger.warning("Removing corrupt state file %s: %s", state_file, e)
            try:
                state_file.unlink()
                removed += 1
            except OSError:
                pass
    return removed


# Legacy compatibility functions
def get_current_session_id() -> Optional[str]:
    """Get current session ID from legacy state file or by cwd."""
    # First try to find by current cwd
    cwd = get_current_cwd()
    state = find_session_by_cwd(cwd)
    if state:
        return state.session_id

    # Fall back to legacy state file
    if config.STATE_FILE.exists():
        return config.STATE_FILE.read_text().strip() or None
    return None


def set_current_session_id(session_id: Optional[str]) -> None:
    """Set current session ID in legacy state file."""
    ensure_state_dir()
    if session_id:
        config.STATE_FILE.write_text(session_id)
    elif config.STATE_FILE.exists():
        config.STATE_FILE.unlink()


def get_ai_type() -> Optional[str]:
    """Get AI type for current cwd or from legacy state file."""
    cwd = get_current_cwd()
    state = find_session_by_cwd(cwd)
    if state:
        return state.ai_type

    # Fall back to legacy state file
    if config.AI_TYPE_FILE.exists():
        return config.AI_TYPE_FILE.read_text().strip() or None
    return None


def set_ai_type(ai_type: Optional[str]) -> None:
    """Set current AI type in legacy state file."""
    ensure_state_dir()
    if ai_type:
        config.AI_TYPE_FILE.write_text(ai_type)
    elif config.AI_TYPE_FILE.exists():
        config.AI_TYPE_FILE.unlink()


def cmd_start(title: Optional[str] = None, ai_type: Optional[str] = None) -> Optional[str]:
    """Start a new session.

    Supports parallel sessions:
    - Different AI types (Claude/Gemini) can run simultaneously
    - Same AI type in different directories can run simultaneously
    - Same AI type in same terminal will reuse existing session
    - Multiple terminals in the same directory are correctly distinguished

    Uses file locking to prevent race conditions when multiple processes
    try to start sessions simultaneously.
    """
    manager = SessionManager(config.sessions_dir)
    cwd = get_current_cwd()
    terminal_id = get_terminal_id()

    # Detect AI type from title if not specified
    if not ai_type and title:
        title_lower = title.lower()
        if "gemini" in title_lower:
            ai_type = AI_TYPE_GEMINI
        elif "claude" in title_lower:
            ai_type = AI_TYPE_CLAUDE

    ai_type = ai_type or AI_TYPE_CLAUDE  # Default to claude

    # Clean up stale sessions before checking (prevents zombie sessions)
    cleanup_stale_sessions()

    # Use file lock to prevent race condition (TOCTOU)
    ensure_state_dir()
    state_file = config.get_session_state_file(ai_type, cwd, terminal_id)
    lock_file = state_file.with_suffix('.lock')
    lock = FileLock(lock_file, timeout=5)

    try:
        with lock:
            # Check if there's already an active session for this AI type and terminal/cwd
            existing_state = get_session_state(ai_type, cwd, terminal_id)
            if existing_state:
                logger.info("Session already active for %s (terminal=%s, cwd=%s): %s",
                           ai_type, terminal_id, cwd, existing_state.session_id)
                print(f"Session already active: {existing_state.session_id} ({ai_type})")
                return existing_state.session_id

            # Create new session
            title = title or f"{ai_type.capitalize()} Session - {datetime.now().strftime(DATETIME_FORMAT)}"

            session_id, session_file = manager.create_session(title)

            # Save session state with terminal_id and cwd
            state = SessionState(
                session_id=session_id,
                ai_type=ai_type,
                cwd=cwd,
                start_timestamp=datetime.now().isoformat(),
                title=title,
                terminal_id=terminal_id
            )
            set_session_state(state)

            if terminal_id:
                logger.info("Started session: %s (%s) terminal=%s cwd=%s", session_id, ai_type, terminal_id, cwd)
            else:
                logger.info("Started session: %s (%s) in %s (no terminal_id)", session_id, ai_type, cwd)
            print(f"Session started: {session_id} ({ai_type})")
            return session_id
    except SessionWriteError as e:
        logger.error("Failed to create session: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return None


def extract_tasks_from_session(session_id: str):
    """Extract tasks from session log using task-picker-agent (optional)."""
    task_extractor = config.task_extractor
    if task_extractor is None:
        # Task extraction is optional - skip silently if not configured
        logger.debug("Task extractor not configured, skipping")
        return

    if not task_extractor.exists():
        logger.warning("Task extractor not found: %s", task_extractor)
        print(f"Task extractor not found: {task_extractor}", file=sys.stderr)
        return

    try:
        result = subprocess.run(
            ["python3", str(task_extractor), "--session", session_id],
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
    except Exception as e:
        logger.error("Error extracting tasks: %s", e)
        print(f"Error extracting tasks: {e}", file=sys.stderr)


def import_conversation(
    manager: SessionManager,
    session_id: str,
    extractor: BaseExtractor,
    ai_name: str,
    cwd: Optional[str] = None
) -> Tuple[int, int]:
    """Import conversation from an AI session history.

    This is a generic import function that works with any extractor.

    Args:
        manager: Session manager instance
        session_id: Target session ID to import into
        extractor: Extractor instance (Claude/Gemini)
        ai_name: Human-readable AI name for messages
        cwd: Optional working directory to filter sessions

    Returns:
        Tuple of (imported_count, skipped_count)
    """
    try:
        session_path = extractor.find_latest_session(cwd=cwd)
        if not session_path:
            logger.info("No %s session found for cwd: %s", ai_name, cwd)
            print(f"No {ai_name} session found", file=sys.stderr)
            return 0, 0

        print(f"Importing conversation from: {session_path.name}")
        messages = extractor.extract_messages(session_path)

    except ExtractorError as e:
        logger.error("Failed to extract %s conversation: %s", ai_name, e)
        print(f"Error extracting conversation: {e}", file=sys.stderr)
        return 0, 0

    if not messages:
        print("No messages found in session")
        return 0, 0

    imported = 0
    skipped = 0

    for msg in messages:
        try:
            if manager.add_log(session_id, msg.content, msg.role, check_duplicate=True):
                imported += 1
            else:
                skipped += 1
        except (SessionNotFoundError, SessionWriteError) as e:
            logger.error("Error adding log: %s", e)
            print(f"Error adding log: {e}", file=sys.stderr)

    logger.info("Imported %d messages, skipped %d duplicates", imported, skipped)
    if skipped:
        print(f"Imported {imported} messages, skipped {skipped} duplicates")
    else:
        print(f"Imported {imported} messages")

    return imported, skipped


def import_gemini_conversation(manager: SessionManager, session_id: str, cwd: Optional[str] = None) -> int:
    """Import conversation from Gemini history.

    Args:
        manager: SessionManager instance
        session_id: Target session ID
        cwd: Working directory to filter sessions (optional)

    Returns:
        Number of messages imported
    """
    extractor = GeminiExtractor(config.gemini_tmp_dir)
    imported, _ = import_conversation(manager, session_id, extractor, "Gemini", cwd)
    return imported


def import_claude_conversation(manager: SessionManager, session_id: str, cwd: Optional[str] = None) -> int:
    """Import conversation from Claude Code history.

    Args:
        manager: SessionManager instance
        session_id: Target session ID
        cwd: Working directory to filter sessions (optional)

    Returns:
        Number of messages imported
    """
    extractor = ClaudeExtractor(config.claude_projects_dir)
    imported, _ = import_conversation(manager, session_id, extractor, "Claude Code", cwd)
    return imported


def cmd_stop(ai_type_arg: Optional[str] = None):
    """Stop the current session, import conversation, and extract tasks.

    Uses terminal_id (if available) or cwd to identify the correct session to stop.

    Args:
        ai_type_arg: Optional AI type override
    """
    manager = SessionManager(config.sessions_dir)
    cwd = get_current_cwd()
    terminal_id = get_terminal_id()

    # Find session by terminal_id or cwd
    state = find_session(cwd, terminal_id)

    if not state:
        # Legacy fallback
        current_id = None
        if config.STATE_FILE.exists():
            current_id = config.STATE_FILE.read_text().strip() or None

        if not current_id:
            logger.warning("No active session to stop (terminal=%s, cwd=%s)", terminal_id, cwd)
            print(f"No active session in {cwd}", file=sys.stderr)
            return

        ai_type = ai_type_arg or (config.AI_TYPE_FILE.read_text().strip() if config.AI_TYPE_FILE.exists() else AI_TYPE_CLAUDE)
        logger.info("Using legacy session state: %s (%s)", current_id, ai_type)
    else:
        current_id = state.session_id
        ai_type = ai_type_arg or state.ai_type
        cwd = state.cwd  # Use stored cwd
        terminal_id = state.terminal_id  # Use stored terminal_id

    logger.info("Stopping session: %s (%s) terminal=%s cwd=%s", current_id, ai_type, terminal_id, cwd)

    try:
        # Import conversation based on AI type, using cwd
        if ai_type == AI_TYPE_GEMINI:
            print("Importing conversation from Gemini...")
            import_gemini_conversation(manager, current_id, cwd)
        else:
            print("Importing conversation from Claude Code...")
            import_claude_conversation(manager, current_id, cwd)

        manager.set_status(current_id, "completed")
        logger.info("Session completed: %s", current_id)
        print(f"Session completed: {current_id} ({ai_type})")

        # Extract tasks from session log
        print("Extracting tasks from session...")
        extract_tasks_from_session(current_id)

    except (SessionNotFoundError, SessionWriteError) as e:
        logger.error("Error stopping session: %s", e)
        print(f"Error: {e}", file=sys.stderr)
    finally:
        # Clear session state
        if state:
            clear_session_state(state.ai_type, state.cwd, state.terminal_id)
        else:
            # Legacy cleanup
            if config.STATE_FILE.exists():
                config.STATE_FILE.unlink()
            if config.AI_TYPE_FILE.exists():
                config.AI_TYPE_FILE.unlink()


def cmd_log(role: str, message: str):
    """Add log entry to current session."""
    manager = SessionManager(config.sessions_dir)

    current_id = get_current_session_id()
    if not current_id:
        logger.warning("No active session for log")
        print("No active session", file=sys.stderr)
        return

    try:
        manager.add_log(current_id, message, role)
        logger.debug("Added %s log to session %s", role, current_id)
        print(f"Added {role} log")
    except (SessionNotFoundError, SessionWriteError) as e:
        logger.error("Error adding log: %s", e)
        print(f"Error: {e}", file=sys.stderr)


def cmd_current():
    """Show current session for this terminal/working directory."""
    cwd = get_current_cwd()
    terminal_id = get_terminal_id()
    state = find_session(cwd, terminal_id)

    if state:
        if state.terminal_id:
            print(f"{state.session_id} ({state.ai_type}) [terminal={state.terminal_id[:8]}]")
        else:
            print(f"{state.session_id} ({state.ai_type})")
    else:
        # Legacy fallback
        current_id = get_current_session_id()
        if current_id:
            ai_type = get_ai_type() or "unknown"
            print(f"{current_id} ({ai_type}) [legacy]")
        else:
            print(f"No active session (terminal={terminal_id}, cwd={cwd})", file=sys.stderr)
            sys.exit(1)


def cmd_list():
    """List all active sessions."""
    sessions = list_all_active_sessions()

    if not sessions:
        print("No active sessions")
        return

    print(f"Active sessions ({len(sessions)}):")
    for s in sessions:
        terminal_info = f" [terminal={s.terminal_id[:8]}]" if s.terminal_id else ""
        print(f"  {s.session_id} ({s.ai_type}){terminal_info} - {s.cwd}")
        if s.title:
            print(f"    Title: {s.title}")
        print(f"    Started: {s.start_timestamp}")


def cmd_cleanup(max_age_hours: int = 24):
    """Clean up stale session state files."""
    removed = cleanup_stale_sessions(max_age_hours)
    if removed:
        print(f"Removed {removed} stale session(s)")
    else:
        print("No stale sessions found")


def main():
    if len(sys.argv) < 2:
        print("Usage: claude_session_hook.py <start|stop|log|current|list|cleanup> [args]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    logger.debug("Executing command: %s", cmd)

    if cmd == "start":
        title = sys.argv[2] if len(sys.argv) > 2 else None
        ai_type = sys.argv[3] if len(sys.argv) > 3 else None
        cmd_start(title, ai_type)
    elif cmd == "stop":
        ai_type = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_stop(ai_type)
    elif cmd == "log":
        if len(sys.argv) < 4:
            print("Usage: claude_session_hook.py log <User|AI> <message>", file=sys.stderr)
            sys.exit(1)
        cmd_log(sys.argv[2], sys.argv[3])
    elif cmd == "current":
        cmd_current()
    elif cmd == "list":
        cmd_list()
    elif cmd == "cleanup":
        max_age = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        cmd_cleanup(max_age)
    else:
        logger.error("Unknown command: %s", cmd)
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
