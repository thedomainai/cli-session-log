"""Tests for Claude session hook."""

import sys
import tempfile
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

# Import hook functions
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
from hooks.claude_session_hook import (
    cmd_current,
    cmd_log,
    cmd_start,
    cmd_stop,
    get_current_session_id,
    import_conversation,
    set_ai_type,
    set_current_session_id,
)

from cli_session_log.extractors import Message
from cli_session_log.extractors.base import BaseExtractor
from cli_session_log.session import SessionManager


class MockExtractor(BaseExtractor):
    """Mock extractor for testing."""

    def __init__(self, messages: list[Message], session_path: Optional[Path] = None):
        self.messages = messages
        self._session_path = session_path
        super().__init__(Path("/tmp"))

    def find_latest_session(self) -> Optional[Path]:
        return self._session_path

    def extract_messages(self, session_path: Path, limit: int = 50) -> list[Message]:
        return self.messages[-limit:]


class TestStateManagement:
    """Tests for state file management."""

    @pytest.fixture
    def mock_config(self):
        """Mock config with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            mock_conf = MagicMock()
            mock_conf.CONFIG_DIR = tmpdir
            mock_conf.STATE_FILE = tmpdir / "current_session.txt"
            mock_conf.AI_TYPE_FILE = tmpdir / "current_ai_type.txt"
            mock_conf.sessions_dir = tmpdir / "sessions"
            mock_conf.task_extractor = None

            mock_conf.ensure_config_dir = lambda: mock_conf.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            yield mock_conf

    def test_set_get_current_session_id(self, mock_config):
        """Test setting and getting current session ID."""
        with patch("hooks.claude_session_hook.config", mock_config):
            mock_config.ensure_config_dir()

            # Set session ID
            set_current_session_id("test-session-123")

            # Get session ID
            result = get_current_session_id()
            assert result == "test-session-123"

            # Clear session ID
            set_current_session_id(None)
            result = get_current_session_id()
            assert result is None

    def test_set_get_ai_type(self, mock_config):
        """Test setting and getting AI type."""
        with patch("hooks.claude_session_hook.config", mock_config):
            mock_config.ensure_config_dir()

            # Set AI type
            set_ai_type("claude")

            # Get AI type
            result = mock_config.AI_TYPE_FILE.read_text().strip()
            assert result == "claude"

            # Clear AI type
            set_ai_type(None)
            assert not mock_config.AI_TYPE_FILE.exists()


class TestImportConversation:
    """Tests for conversation import function."""

    @pytest.fixture
    def manager(self):
        """Create a SessionManager with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SessionManager(Path(tmpdir))

    def test_import_conversation_success(self, manager, capsys):
        """Test successful conversation import."""
        session_id, _ = manager.create_session("Test Session")

        messages = [
            Message(role="User", content="Hello"),
            Message(role="AI", content="Hi there"),
            Message(role="User", content="How are you?"),
        ]

        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            extractor = MockExtractor(messages, Path(f.name))

            imported, skipped = import_conversation(
                manager, session_id, extractor, "Test AI"
            )

            assert imported == 3
            assert skipped == 0

            captured = capsys.readouterr()
            assert "Imported 3 messages" in captured.out

    def test_import_conversation_no_session_found(self, manager, capsys):
        """Test import when no session found."""
        session_id, _ = manager.create_session("Test Session")

        extractor = MockExtractor([], None)

        imported, skipped = import_conversation(
            manager, session_id, extractor, "Test AI"
        )

        assert imported == 0
        assert skipped == 0

        captured = capsys.readouterr()
        assert "No Test AI session found" in captured.err

    def test_import_conversation_with_duplicates(self, manager, capsys):
        """Test import skips duplicates."""
        session_id, _ = manager.create_session("Test Session")

        # Import first time
        messages = [
            Message(role="User", content="Hello"),
            Message(role="AI", content="Hi there"),
        ]

        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            extractor = MockExtractor(messages, Path(f.name))

            # First import
            imported1, skipped1 = import_conversation(
                manager, session_id, extractor, "Test AI"
            )

            # Clear output
            capsys.readouterr()

            # Second import (should skip duplicates)
            # Note: import_conversation uses check_duplicate=True
            imported2, skipped2 = import_conversation(
                manager, session_id, extractor, "Test AI"
            )

            assert imported1 == 2
            assert skipped1 == 0
            assert imported2 == 0
            assert skipped2 == 2


class TestCmdStart:
    """Tests for start command."""

    @pytest.fixture
    def mock_config(self):
        """Mock config with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            mock_conf = MagicMock()
            mock_conf.CONFIG_DIR = tmpdir
            mock_conf.STATE_FILE = tmpdir / "current_session.txt"
            mock_conf.AI_TYPE_FILE = tmpdir / "current_ai_type.txt"
            mock_conf.sessions_dir = tmpdir / "sessions"
            mock_conf.task_extractor = None

            mock_conf.ensure_config_dir = lambda: mock_conf.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            yield mock_conf

    def test_cmd_start_creates_session(self, mock_config, capsys):
        """Test starting a new session."""
        with patch("hooks.claude_session_hook.config", mock_config):
            mock_config.ensure_config_dir()

            session_id = cmd_start("Test Session", "claude")

            assert session_id is not None
            assert len(session_id) == 8

            captured = capsys.readouterr()
            assert "Session started:" in captured.out
            assert "claude" in captured.out

    def test_cmd_start_with_active_session(self, mock_config, capsys):
        """Test starting when session already active."""
        with patch("hooks.claude_session_hook.config", mock_config):
            mock_config.ensure_config_dir()

            # Start first session
            session_id1 = cmd_start("First Session", "claude")
            capsys.readouterr()

            # Try to start second session
            session_id2 = cmd_start("Second Session", "claude")

            # Should return the existing session
            assert session_id2 == session_id1

            captured = capsys.readouterr()
            assert "Session already active" in captured.err

    def test_cmd_start_detects_ai_type_from_title(self, mock_config, capsys):
        """Test AI type detection from title."""
        with patch("hooks.claude_session_hook.config", mock_config):
            mock_config.ensure_config_dir()

            # Test with "gemini" in title
            session_id = cmd_start("Gemini Code Review", None)

            captured = capsys.readouterr()
            assert "gemini" in captured.out.lower()


class TestCmdCurrent:
    """Tests for current command."""

    @pytest.fixture
    def mock_config(self):
        """Mock config with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            mock_conf = MagicMock()
            mock_conf.CONFIG_DIR = tmpdir
            mock_conf.STATE_FILE = tmpdir / "current_session.txt"
            mock_conf.AI_TYPE_FILE = tmpdir / "current_ai_type.txt"
            mock_conf.sessions_dir = tmpdir / "sessions"

            mock_conf.ensure_config_dir = lambda: mock_conf.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            yield mock_conf

    def test_cmd_current_with_active_session(self, mock_config, capsys):
        """Test showing current session ID."""
        with patch("hooks.claude_session_hook.config", mock_config):
            mock_config.ensure_config_dir()
            mock_config.STATE_FILE.write_text("test-123")

            cmd_current()

            captured = capsys.readouterr()
            assert "test-123" in captured.out

    def test_cmd_current_no_active_session(self, mock_config, capsys):
        """Test showing current when no session active."""
        with patch("hooks.claude_session_hook.config", mock_config):
            mock_config.ensure_config_dir()

            with pytest.raises(SystemExit) as exc_info:
                cmd_current()

            assert exc_info.value.code == 1

            captured = capsys.readouterr()
            assert "No active session" in captured.err
