#!/usr/bin/env python3
"""CLI interface for session management."""

import argparse
import sys
from pathlib import Path

from .config import get_config
from .session import SessionManager


def cmd_new(args, manager: SessionManager):
    """Create a new session."""
    session_id, session_file = manager.create_session(args.title)
    print(f"Created session: {session_id}")
    print(f"File: {session_file}")


def cmd_list(args, manager: SessionManager):
    """List sessions."""
    sessions = manager.list_sessions(args.status)

    if not sessions:
        print("No sessions found.")
        return

    print(f"{'ID':<10} {'Status':<12} {'Title':<30} {'Updated':<20}")
    print("-" * 75)

    for s in sessions:
        title = s['title'][:30] if s['title'] else "Untitled"
        updated = s['updated_at'][:19] if s['updated_at'] else ""
        print(f"{s['id']:<10} {s['status']:<12} {title:<30} {updated:<20}")


def cmd_show(args, manager: SessionManager):
    """Show session details."""
    try:
        content = manager.get_session_content(args.id)
        print(content)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


def cmd_log(args, manager: SessionManager):
    """Add a log entry to a session."""
    if args.user:
        role = "User"
        message = args.user
    elif args.ai:
        role = "AI"
        message = args.ai
    else:
        print("Specify -u/--user or -a/--ai with message", file=sys.stderr)
        sys.exit(1)

    try:
        manager.add_log(args.id, message, role)
        fm, _ = manager.get_session(args.id)
        print(f"Added {role} log entry to session {fm['session_id']}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


def cmd_task(args, manager: SessionManager):
    """Manage tasks in a session."""
    try:
        if args.action == "add":
            manager.add_task(args.id, args.text)
            print(f"Added task: {args.text}")

        elif args.action == "done":
            task_num = int(args.text)
            manager.complete_task(args.id, task_num)
            print(f"Completed task {task_num}")

        elif args.action == "list":
            tasks = manager.list_tasks(args.id)
            fm, _ = manager.get_session(args.id)
            print(f"Tasks for session {fm['session_id']}:")
            for task in tasks:
                status = "done" if task['done'] else "pending"
                print(f"  {task['num']}. [{status}] {task['text']}")

    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


def cmd_status(args, manager: SessionManager):
    """Change session status."""
    try:
        old_status = manager.set_status(args.id, args.status)
        fm, _ = manager.get_session(args.id)
        print(f"Session {fm['session_id']}: {old_status} -> {args.status}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


def cmd_close(args, manager: SessionManager):
    """Close a session (set status to completed)."""
    try:
        old_status = manager.set_status(args.id, "completed")
        fm, _ = manager.get_session(args.id)
        print(f"Session {fm['session_id']}: {old_status} -> completed")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="session-log",
        description="Manage CLI sessions with conversation logs and task tracking"
    )
    parser.add_argument(
        "--dir", "-d",
        type=Path,
        help="Sessions directory (default: ./sessions or $SESSION_LOG_DIR)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # new
    p_new = subparsers.add_parser("new", help="Create a new session")
    p_new.add_argument("title", nargs="?", help="Session title")

    # list
    p_list = subparsers.add_parser("list", help="List sessions")
    p_list.add_argument("--status", "-s", help="Filter by status")

    # show
    p_show = subparsers.add_parser("show", help="Show session details")
    p_show.add_argument("id", help="Session ID (partial match)")

    # log
    p_log = subparsers.add_parser("log", help="Add log entry")
    p_log.add_argument("id", help="Session ID")
    p_log.add_argument("-u", "--user", help="User message")
    p_log.add_argument("-a", "--ai", help="AI response")

    # task
    p_task = subparsers.add_parser("task", help="Manage tasks")
    p_task.add_argument("action", choices=["add", "done", "list"], help="Action")
    p_task.add_argument("id", help="Session ID")
    p_task.add_argument("text", nargs="?", help="Task text or number")

    # status
    p_status = subparsers.add_parser("status", help="Change session status")
    p_status.add_argument("id", help="Session ID")
    p_status.add_argument("status", help="New status (active/paused/completed)")

    # close
    p_close = subparsers.add_parser("close", help="Close a session")
    p_close.add_argument("id", help="Session ID")

    args = parser.parse_args()

    # Initialize manager
    config = get_config()
    sessions_dir = args.dir or config.sessions_dir
    manager = SessionManager(sessions_dir)

    # Dispatch commands
    commands = {
        "new": cmd_new,
        "list": cmd_list,
        "show": cmd_show,
        "log": cmd_log,
        "task": cmd_task,
        "status": cmd_status,
        "close": cmd_close,
    }

    commands[args.command](args, manager)


if __name__ == "__main__":
    main()
