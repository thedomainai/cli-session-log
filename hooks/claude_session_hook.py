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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli_session_log.config import get_config
from cli_session_log.extractors import ClaudeExtractor, GeminiExtractor
from cli_session_log.session import SessionManager

# Get configuration
config = get_config()

# State file for Claude session ID (not in config as it's hook-specific)
CLAUDE_SESSION_FILE = config.CONFIG_DIR / "claude_session_id.txt"


def ensure_state_dir():
    """Ensure state directory exists."""
    config.ensure_config_dir()


def get_claude_session_id() -> str | None:
    """Get Claude Code session ID from state file."""
    if CLAUDE_SESSION_FILE.exists():
        return CLAUDE_SESSION_FILE.read_text().strip() or None
    return None


def set_claude_session_id(session_id: str | None):
    """Set Claude Code session ID in state file."""
    ensure_state_dir()
    if session_id:
        CLAUDE_SESSION_FILE.write_text(session_id)
    elif CLAUDE_SESSION_FILE.exists():
        CLAUDE_SESSION_FILE.unlink()


def get_ai_type() -> str | None:
    """Get current AI type (claude/gemini)."""
    if config.AI_TYPE_FILE.exists():
        return config.AI_TYPE_FILE.read_text().strip() or None
    return None


def set_ai_type(ai_type: str | None):
    """Set current AI type."""
    ensure_state_dir()
    if ai_type:
        config.AI_TYPE_FILE.write_text(ai_type)
    elif config.AI_TYPE_FILE.exists():
        config.AI_TYPE_FILE.unlink()


def get_current_session_id() -> str | None:
    """Get current session ID from state file."""
    if config.STATE_FILE.exists():
        return config.STATE_FILE.read_text().strip() or None
    return None


def set_current_session_id(session_id: str | None):
    """Set current session ID in state file."""
    ensure_state_dir()
    if session_id:
        config.STATE_FILE.write_text(session_id)
    elif config.STATE_FILE.exists():
        config.STATE_FILE.unlink()


def cmd_start(title: str | None = None, ai_type: str | None = None):
    """Start a new session."""
    manager = SessionManager(config.sessions_dir)

    # Check if there's already an active session
    current_id = get_current_session_id()
    if current_id:
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
    session_id, session_file = manager.create_session(title)
    set_current_session_id(session_id)
    set_ai_type(ai_type)

    print(f"Session started: {session_id} ({ai_type})")
    return session_id


def extract_tasks_from_session(session_id: str):
    """Extract tasks from session log using task-picker-agent."""
    if not config.task_extractor.exists():
        print(f"Task extractor not found: {config.task_extractor}", file=sys.stderr)
        return

    try:
        result = subprocess.run(
            ["python3", str(config.task_extractor), "--session", session_id],
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
    except Exception as e:
        print(f"Error extracting tasks: {e}", file=sys.stderr)


def import_gemini_conversation(manager: SessionManager, session_id: str):
    """Import conversation from Gemini history."""
    extractor = GeminiExtractor(config.gemini_tmp_dir)
    session_path = extractor.find_latest_session()

    if not session_path:
        print("No Gemini session found", file=sys.stderr)
        return

    print(f"Importing conversation from: {session_path.name}")
    messages = extractor.extract_messages(session_path)

    if not messages:
        print("No messages found in session")
        return

    for msg in messages:
        try:
            manager.add_log(session_id, msg.content, msg.role)
        except Exception as e:
            print(f"Error adding log: {e}", file=sys.stderr)

    print(f"Imported {len(messages)} messages")


def import_claude_conversation(manager: SessionManager, session_id: str):
    """Import conversation from Claude Code history."""
    extractor = ClaudeExtractor(config.claude_projects_dir)
    session_path = extractor.find_latest_session()

    if not session_path:
        print("No Claude Code session found", file=sys.stderr)
        return

    print(f"Importing conversation from: {session_path.name}")
    messages = extractor.extract_messages(session_path)

    if not messages:
        print("No messages found in session")
        return

    for msg in messages:
        try:
            manager.add_log(session_id, msg.content, msg.role)
        except Exception as e:
            print(f"Error adding log: {e}", file=sys.stderr)

    print(f"Imported {len(messages)} messages")


def cmd_stop():
    """Stop the current session, import conversation, and extract tasks."""
    manager = SessionManager(config.sessions_dir)

    current_id = get_current_session_id()
    if not current_id:
        print("No active session", file=sys.stderr)
        return

    ai_type = get_ai_type() or "claude"

    try:
        # Import conversation based on AI type
        if ai_type == "gemini":
            print("Importing conversation from Gemini...")
            import_gemini_conversation(manager, current_id)
        else:
            print("Importing conversation from Claude Code...")
            import_claude_conversation(manager, current_id)

        manager.set_status(current_id, "completed")
        print(f"Session completed: {current_id} ({ai_type})")

        # Extract tasks from session log
        print("Extracting tasks from session...")
        extract_tasks_from_session(current_id)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
    finally:
        set_current_session_id(None)
        set_ai_type(None)


def cmd_log(role: str, message: str):
    """Add log entry to current session."""
    manager = SessionManager(config.sessions_dir)

    current_id = get_current_session_id()
    if not current_id:
        print("No active session", file=sys.stderr)
        return

    try:
        manager.add_log(current_id, message, role)
        print(f"Added {role} log")
    except ValueError as e:
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
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
