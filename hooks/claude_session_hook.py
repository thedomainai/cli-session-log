#!/usr/bin/env python3
"""
Claude Code Hook for session management.

This hook is called by Claude Code on specific events:
- Stop: When the session ends

Usage in ~/.claude/settings.json:
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python /path/to/claude_session_hook.py stop"
          }
        ]
      }
    ]
  }
}
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

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

# State file for Claude session ID (not in config as it's hook-specific)
CLAUDE_SESSION_FILE = config.CONFIG_DIR / "claude_session_id.txt"


def ensure_state_dir():
    """Ensure state directory exists."""
    config.ensure_config_dir()


def get_claude_session_id() -> Optional[str]:
    """Get Claude Code session ID from state file."""
    if CLAUDE_SESSION_FILE.exists():
        return CLAUDE_SESSION_FILE.read_text().strip() or None
    return None


def set_claude_session_id(session_id: Optional[str]) -> None:
    """Set Claude Code session ID in state file."""
    ensure_state_dir()
    if session_id:
        CLAUDE_SESSION_FILE.write_text(session_id)
    elif CLAUDE_SESSION_FILE.exists():
        CLAUDE_SESSION_FILE.unlink()


def get_ai_type() -> Optional[str]:
    """Get current AI type (claude/gemini)."""
    if config.AI_TYPE_FILE.exists():
        return config.AI_TYPE_FILE.read_text().strip() or None
    return None


def set_ai_type(ai_type: Optional[str]) -> None:
    """Set current AI type."""
    ensure_state_dir()
    if ai_type:
        config.AI_TYPE_FILE.write_text(ai_type)
    elif config.AI_TYPE_FILE.exists():
        config.AI_TYPE_FILE.unlink()


def get_current_session_id() -> Optional[str]:
    """Get current session ID from state file."""
    if config.STATE_FILE.exists():
        return config.STATE_FILE.read_text().strip() or None
    return None


def set_current_session_id(session_id: Optional[str]) -> None:
    """Set current session ID in state file."""
    ensure_state_dir()
    if session_id:
        config.STATE_FILE.write_text(session_id)
    elif config.STATE_FILE.exists():
        config.STATE_FILE.unlink()


def cmd_start(title: Optional[str] = None, ai_type: Optional[str] = None) -> Optional[str]:
    """Start a new session."""
    manager = SessionManager(config.sessions_dir)

    # Check if there's already an active session
    current_id = get_current_session_id()
    if current_id:
        logger.warning("Session already active: %s", current_id)
        print(f"Session already active: {current_id}", file=sys.stderr)
        return current_id

    # Detect AI type from title if not specified
    if not ai_type and title:
        title_lower = title.lower()
        if "gemini" in title_lower:
            ai_type = "gemini"
        elif "claude" in title_lower:
            ai_type = "claude"

    ai_type = ai_type or "claude"  # Default to claude

    # Create new session
    title = title or f"{ai_type.capitalize()} Session - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    try:
        session_id, session_file = manager.create_session(title)
        set_current_session_id(session_id)
        set_ai_type(ai_type)
        logger.info("Started session: %s (%s)", session_id, ai_type)
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
    ai_name: str
) -> Tuple[int, int]:
    """Import conversation from an AI session history.

    This is a generic import function that works with any extractor.

    Args:
        manager: Session manager instance
        session_id: Target session ID to import into
        extractor: Extractor instance (Claude/Gemini)
        ai_name: Human-readable AI name for messages

    Returns:
        Tuple of (imported_count, skipped_count)
    """
    try:
        session_path = extractor.find_latest_session()
        if not session_path:
            logger.info("No %s session found", ai_name)
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


def import_gemini_conversation(manager: SessionManager, session_id: str) -> int:
    """Import conversation from Gemini history.

    Returns:
        Number of messages imported
    """
    extractor = GeminiExtractor(config.gemini_tmp_dir)
    imported, _ = import_conversation(manager, session_id, extractor, "Gemini")
    return imported


def import_claude_conversation(manager: SessionManager, session_id: str) -> int:
    """Import conversation from Claude Code history.

    Returns:
        Number of messages imported
    """
    extractor = ClaudeExtractor(config.claude_projects_dir)
    imported, _ = import_conversation(manager, session_id, extractor, "Claude Code")
    return imported


def cmd_stop():
    """Stop the current session, import conversation, and extract tasks."""
    manager = SessionManager(config.sessions_dir)

    current_id = get_current_session_id()
    if not current_id:
        logger.warning("No active session to stop")
        print("No active session", file=sys.stderr)
        return

    ai_type = get_ai_type() or "claude"
    logger.info("Stopping session: %s (%s)", current_id, ai_type)

    try:
        # Import conversation based on AI type
        if ai_type == "gemini":
            print("Importing conversation from Gemini...")
            import_gemini_conversation(manager, current_id)
        else:
            print("Importing conversation from Claude Code...")
            import_claude_conversation(manager, current_id)

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
        set_current_session_id(None)
        set_ai_type(None)


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
    """Show current session ID."""
    current_id = get_current_session_id()
    if current_id:
        print(current_id)
    else:
        print("No active session", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: claude_session_hook.py <start|stop|log|current> [args]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    logger.debug("Executing command: %s", cmd)

    if cmd == "start":
        title = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_start(title)
    elif cmd == "stop":
        cmd_stop()
    elif cmd == "log":
        if len(sys.argv) < 4:
            print("Usage: claude_session_hook.py log <User|AI> <message>", file=sys.stderr)
            sys.exit(1)
        cmd_log(sys.argv[2], sys.argv[3])
    elif cmd == "current":
        cmd_current()
    else:
        logger.error("Unknown command: %s", cmd)
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
