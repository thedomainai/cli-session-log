"""Tests for CLI commands."""

import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from cli_session_log.cli import (
    cmd_close,
    cmd_list,
    cmd_log,
    cmd_new,
    cmd_show,
    cmd_status,
    cmd_task,
    main,
)
from cli_session_log.session import SessionManager


class MockArgs:
    """Mock argparse namespace for testing."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestCmdNew:
    """Tests for new command."""

    @pytest.fixture
    def manager(self):
        """Create a SessionManager with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SessionManager(Path(tmpdir))

    def test_cmd_new_creates_session(self, manager, capsys):
        """Test creating a new session."""
        args = MockArgs(title="Test Session")
        cmd_new(args, manager)

        captured = capsys.readouterr()
        assert "Created session:" in captured.out
        assert "File:" in captured.out

    def test_cmd_new_without_title(self, manager, capsys):
        """Test creating a session without title."""
        args = MockArgs(title=None)
        cmd_new(args, manager)

        captured = capsys.readouterr()
        assert "Created session:" in captured.out


class TestCmdList:
    """Tests for list command."""

    @pytest.fixture
    def manager(self):
        """Create a SessionManager with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SessionManager(Path(tmpdir))

    def test_cmd_list_empty(self, manager, capsys):
        """Test listing when no sessions exist."""
        args = MockArgs(status=None)
        cmd_list(args, manager)

        captured = capsys.readouterr()
        assert "No sessions found" in captured.out

    def test_cmd_list_with_sessions(self, manager, capsys):
        """Test listing sessions."""
        manager.create_session("Test 1")
        manager.create_session("Test 2")

        args = MockArgs(status=None)
        cmd_list(args, manager)

        captured = capsys.readouterr()
        assert "ID" in captured.out
        assert "Status" in captured.out
        assert "Test 1" in captured.out or "Test 2" in captured.out

    def test_cmd_list_with_status_filter(self, manager, capsys):
        """Test listing sessions with status filter."""
        session_id, _ = manager.create_session("Test Active")
        manager.set_status(session_id, "completed")
        manager.create_session("Test Active 2")

        args = MockArgs(status="active")
        cmd_list(args, manager)

        captured = capsys.readouterr()
        assert "active" in captured.out


class TestCmdShow:
    """Tests for show command."""

    @pytest.fixture
    def manager(self):
        """Create a SessionManager with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SessionManager(Path(tmpdir))

    def test_cmd_show_existing_session(self, manager, capsys):
        """Test showing an existing session."""
        session_id, _ = manager.create_session("Test Session")

        args = MockArgs(id=session_id)
        cmd_show(args, manager)

        captured = capsys.readouterr()
        assert "Test Session" in captured.out
        assert "session_id:" in captured.out

    def test_cmd_show_not_found(self, manager, capsys):
        """Test showing a non-existent session."""
        args = MockArgs(id="nonexistent")

        with pytest.raises(SystemExit) as exc_info:
            cmd_show(args, manager)

        assert exc_info.value.code == 1


class TestCmdLog:
    """Tests for log command."""

    @pytest.fixture
    def manager(self):
        """Create a SessionManager with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SessionManager(Path(tmpdir))

    def test_cmd_log_user_message(self, manager, capsys):
        """Test adding a user log entry."""
        session_id, _ = manager.create_session("Test Session")

        args = MockArgs(id=session_id, user="Hello", ai=None)
        cmd_log(args, manager)

        captured = capsys.readouterr()
        assert "Added User log entry" in captured.out

    def test_cmd_log_ai_message(self, manager, capsys):
        """Test adding an AI log entry."""
        session_id, _ = manager.create_session("Test Session")

        args = MockArgs(id=session_id, user=None, ai="Hello back")
        cmd_log(args, manager)

        captured = capsys.readouterr()
        assert "Added AI log entry" in captured.out

    def test_cmd_log_no_message(self, manager, capsys):
        """Test log command without message."""
        session_id, _ = manager.create_session("Test Session")

        args = MockArgs(id=session_id, user=None, ai=None)

        with pytest.raises(SystemExit) as exc_info:
            cmd_log(args, manager)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Specify -u/--user or -a/--ai" in captured.err


class TestCmdTask:
    """Tests for task command."""

    @pytest.fixture
    def manager(self):
        """Create a SessionManager with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SessionManager(Path(tmpdir))

    def test_cmd_task_add(self, manager, capsys):
        """Test adding a task."""
        session_id, _ = manager.create_session("Test Session")

        args = MockArgs(id=session_id, action="add", text="New task")
        cmd_task(args, manager)

        captured = capsys.readouterr()
        assert "Added task: New task" in captured.out

    def test_cmd_task_list(self, manager, capsys):
        """Test listing tasks."""
        session_id, _ = manager.create_session("Test Session")
        manager.add_task(session_id, "Task 1")
        manager.add_task(session_id, "Task 2")

        args = MockArgs(id=session_id, action="list", text=None)
        cmd_task(args, manager)

        captured = capsys.readouterr()
        assert "Tasks for session" in captured.out
        assert "Task 1" in captured.out
        assert "Task 2" in captured.out

    def test_cmd_task_done(self, manager, capsys):
        """Test completing a task."""
        session_id, _ = manager.create_session("Test Session")
        manager.add_task(session_id, "Task to complete")

        args = MockArgs(id=session_id, action="done", text="1")
        cmd_task(args, manager)

        captured = capsys.readouterr()
        assert "Completed task 1" in captured.out


class TestCmdStatus:
    """Tests for status command."""

    @pytest.fixture
    def manager(self):
        """Create a SessionManager with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SessionManager(Path(tmpdir))

    def test_cmd_status_change(self, manager, capsys):
        """Test changing session status."""
        session_id, _ = manager.create_session("Test Session")

        args = MockArgs(id=session_id, status="completed")
        cmd_status(args, manager)

        captured = capsys.readouterr()
        assert "active -> completed" in captured.out

    def test_cmd_status_invalid(self, manager, capsys):
        """Test changing to invalid status."""
        session_id, _ = manager.create_session("Test Session")

        args = MockArgs(id=session_id, status="invalid_status")

        with pytest.raises(SystemExit) as exc_info:
            cmd_status(args, manager)

        assert exc_info.value.code == 1


class TestCmdClose:
    """Tests for close command."""

    @pytest.fixture
    def manager(self):
        """Create a SessionManager with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SessionManager(Path(tmpdir))

    def test_cmd_close_session(self, manager, capsys):
        """Test closing a session."""
        session_id, _ = manager.create_session("Test Session")

        args = MockArgs(id=session_id)
        cmd_close(args, manager)

        captured = capsys.readouterr()
        assert "active -> completed" in captured.out


class TestMain:
    """Tests for main entry point."""

    def test_main_no_args(self):
        """Test main without arguments."""
        with patch.object(sys, "argv", ["session-log"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2  # argparse error

    def test_main_new_command(self, capsys):
        """Test main with new command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(sys, "argv", ["session-log", "--dir", tmpdir, "new", "Test"]):
                main()

            captured = capsys.readouterr()
            assert "Created session:" in captured.out

    def test_main_list_command(self, capsys):
        """Test main with list command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(sys, "argv", ["session-log", "--dir", tmpdir, "list"]):
                main()

            captured = capsys.readouterr()
            assert "No sessions found" in captured.out
