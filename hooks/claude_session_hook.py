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

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli_session_log.session import SessionManager

SESSIONS_DIR = Path.home() / "workspace/obsidian_vault/docs/01_resource/sessions"
STATE_FILE = Path.home() / ".config/cli-session-log/current_session.txt"
TASK_EXTRACTOR = Path.home() / "workspace/obsidian_vault/docs/03_project/00_thedomainai/task-picker-agent/task_extractor.py"


def ensure_state_dir():
    """Ensure state directory exists."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def get_current_session_id() -> str | None:
    """Get current session ID from state file."""
    if STATE_FILE.exists():
        return STATE_FILE.read_text().strip() or None
    return None


def set_current_session_id(session_id: str | None):
    """Set current session ID in state file."""
    ensure_state_dir()
    if session_id:
        STATE_FILE.write_text(session_id)
    elif STATE_FILE.exists():
        STATE_FILE.unlink()


def cmd_start(title: str | None = None):
    """Start a new session."""
    manager = SessionManager(SESSIONS_DIR)

    # Check if there's already an active session
    current_id = get_current_session_id()
    if current_id:
        print(f"Session already active: {current_id}", file=sys.stderr)
        return current_id

    # Create new session
    title = title or f"Claude Code Session - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    session_id, session_file = manager.create_session(title)
    set_current_session_id(session_id)

    print(f"Session started: {session_id}")
    return session_id


def extract_tasks_from_session(session_id: str):
    """Extract tasks from session log using task-picker-agent."""
    if not TASK_EXTRACTOR.exists():
        print(f"Task extractor not found: {TASK_EXTRACTOR}", file=sys.stderr)
        return

    try:
        result = subprocess.run(
            ["python3", str(TASK_EXTRACTOR), "--session", session_id],
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
    except Exception as e:
        print(f"Error extracting tasks: {e}", file=sys.stderr)


def cmd_stop():
    """Stop the current session and extract tasks."""
    manager = SessionManager(SESSIONS_DIR)

    current_id = get_current_session_id()
    if not current_id:
        print("No active session", file=sys.stderr)
        return

    try:
        manager.set_status(current_id, "completed")
        print(f"Session completed: {current_id}")

        # Extract tasks from session log
        print("Extracting tasks from session...")
        extract_tasks_from_session(current_id)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
    finally:
        set_current_session_id(None)


def cmd_log(role: str, message: str):
    """Add log entry to current session."""
    manager = SessionManager(SESSIONS_DIR)

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
