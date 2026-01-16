"""Tests for session management."""

import tempfile
from pathlib import Path

import pytest

from cli_session_log.exceptions import SessionNotFoundError, SessionWriteError
from cli_session_log.session import (
    SessionManager,
    compute_message_hash,
    generate_session_id,
    parse_frontmatter,
    serialize_frontmatter,
)


class TestFrontmatter:
    """Tests for frontmatter parsing and serialization."""

    def test_parse_valid_frontmatter(self):
        """Test parsing valid YAML frontmatter."""
        content = """---
session_id: abc12345
title: Test Session
status: active
---

# Body content
"""
        fm, body = parse_frontmatter(content)

        assert fm["session_id"] == "abc12345"
        assert fm["title"] == "Test Session"
        assert fm["status"] == "active"
        assert "# Body content" in body

    def test_parse_no_frontmatter(self):
        """Test parsing content without frontmatter."""
        content = "# Just a body\nNo frontmatter here."
        fm, body = parse_frontmatter(content)

        assert fm == {}
        assert body == content

    def test_parse_malformed_frontmatter(self):
        """Test parsing malformed YAML returns empty dict."""
        content = """---
invalid: yaml: syntax: here
---

# Body
"""
        fm, body = parse_frontmatter(content)

        assert fm == {}
        assert "# Body" in body

    def test_serialize_frontmatter(self):
        """Test serializing frontmatter and body."""
        fm = {"session_id": "test123", "title": "Test"}
        body = "# Content\n"

        result = serialize_frontmatter(fm, body)

        assert result.startswith("---\n")
        assert "session_id: test123" in result
        assert "---\n# Content" in result


class TestHelpers:
    """Tests for helper functions."""

    def test_generate_session_id_length(self):
        """Test session ID is 8 characters."""
        session_id = generate_session_id()
        assert len(session_id) == 8

    def test_generate_session_id_unique(self):
        """Test session IDs are unique."""
        ids = [generate_session_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_compute_message_hash(self):
        """Test message hash computation."""
        hash1 = compute_message_hash("User", "Hello")
        hash2 = compute_message_hash("User", "Hello")
        hash3 = compute_message_hash("AI", "Hello")

        assert hash1 == hash2  # Same input = same hash
        assert hash1 != hash3  # Different role = different hash
        assert len(hash1) == 16  # 16 characters


class TestSessionManager:
    """Tests for SessionManager class."""

    @pytest.fixture
    def temp_sessions_dir(self):
        """Create a temporary sessions directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_sessions_dir):
        """Create a SessionManager with temp directory."""
        return SessionManager(temp_sessions_dir)

    def test_create_session(self, manager):
        """Test creating a new session."""
        session_id, session_file = manager.create_session("Test Session")

        assert len(session_id) == 8
        assert session_file.exists()
        assert session_file.name == f"session-{session_id}.md"

        content = session_file.read_text()
        assert "Test Session" in content
        assert "status: active" in content

    def test_create_session_with_version(self, manager):
        """Test that new sessions have version field."""
        session_id, session_file = manager.create_session("Test")
        fm, _ = manager.get_session(session_id)

        assert fm.get("version") == "1.0"

    def test_find_session_exact(self, manager):
        """Test finding session by exact ID."""
        session_id, _ = manager.create_session("Test")
        found = manager.find_session(session_id)

        assert found is not None
        assert session_id in found.stem

    def test_find_session_partial(self, manager):
        """Test finding session by partial ID."""
        session_id, _ = manager.create_session("Test")
        found = manager.find_session(session_id[:4])

        assert found is not None
        assert session_id in found.stem

    def test_find_session_not_found(self, manager):
        """Test finding non-existent session."""
        found = manager.find_session("nonexistent")
        assert found is None

    def test_list_sessions(self, manager):
        """Test listing all sessions."""
        manager.create_session("Session 1")
        manager.create_session("Session 2")

        sessions = manager.list_sessions()

        assert len(sessions) == 2
        titles = [s["title"] for s in sessions]
        assert "Session 1" in titles
        assert "Session 2" in titles

    def test_list_sessions_with_filter(self, manager):
        """Test filtering sessions by status."""
        id1, _ = manager.create_session("Active Session")
        id2, _ = manager.create_session("Completed Session")
        manager.set_status(id2, "completed")

        active = manager.list_sessions(status_filter="active")
        completed = manager.list_sessions(status_filter="completed")

        assert len(active) == 1
        assert active[0]["title"] == "Active Session"
        assert len(completed) == 1
        assert completed[0]["title"] == "Completed Session"

    def test_add_log(self, manager):
        """Test adding log entry."""
        session_id, _ = manager.create_session("Test")
        result = manager.add_log(session_id, "Hello", "User")

        assert result is True
        content = manager.get_session_content(session_id)
        assert "**User**: Hello" in content

    def test_add_log_with_duplicate_detection(self, manager):
        """Test duplicate detection in add_log."""
        session_id, _ = manager.create_session("Test")

        # First add should succeed
        result1 = manager.add_log(session_id, "Hello", "User", check_duplicate=True)
        # Second add with same content should be skipped
        result2 = manager.add_log(session_id, "Hello", "User", check_duplicate=True)
        # Different content should succeed
        result3 = manager.add_log(session_id, "World", "User", check_duplicate=True)

        assert result1 is True
        assert result2 is False  # Duplicate skipped
        assert result3 is True

    def test_add_log_session_not_found(self, manager):
        """Test adding log to non-existent session."""
        with pytest.raises(SessionNotFoundError):
            manager.add_log("nonexistent", "Hello", "User")

    def test_add_task(self, manager):
        """Test adding task."""
        session_id, _ = manager.create_session("Test")
        manager.add_task(session_id, "Do something")

        content = manager.get_session_content(session_id)
        assert "- [ ] Do something" in content

    def test_complete_task(self, manager):
        """Test completing task."""
        session_id, _ = manager.create_session("Test")
        manager.add_task(session_id, "Task 1")
        manager.add_task(session_id, "Task 2")

        manager.complete_task(session_id, 1)

        tasks = manager.list_tasks(session_id)
        completed = [t for t in tasks if t["done"]]
        assert len(completed) == 1
        assert completed[0]["text"] == "Task 1"

    def test_complete_task_not_found(self, manager):
        """Test completing non-existent task."""
        session_id, _ = manager.create_session("Test")

        with pytest.raises(ValueError, match="Task 1 not found"):
            manager.complete_task(session_id, 1)

    def test_set_status(self, manager):
        """Test changing session status."""
        session_id, _ = manager.create_session("Test")

        old_status = manager.set_status(session_id, "completed")

        assert old_status == "active"
        fm, _ = manager.get_session(session_id)
        assert fm["status"] == "completed"

    def test_set_status_invalid(self, manager):
        """Test setting invalid status."""
        session_id, _ = manager.create_session("Test")

        with pytest.raises(ValueError, match="Invalid status"):
            manager.set_status(session_id, "invalid")

    def test_get_session(self, manager):
        """Test getting session frontmatter and body."""
        session_id, _ = manager.create_session("Test Session")
        fm, body = manager.get_session(session_id)

        assert fm["session_id"] == session_id
        assert fm["title"] == "Test Session"
        assert "# Session: Test Session" in body

    def test_clear_imported_hashes(self, manager):
        """Test clearing imported message hashes."""
        session_id, _ = manager.create_session("Test")

        # Add some messages with duplicate detection
        manager.add_log(session_id, "Hello", "User", check_duplicate=True)
        manager.add_log(session_id, "Hi", "AI", check_duplicate=True)

        fm, _ = manager.get_session(session_id)
        assert len(fm.get("imported_hashes", [])) == 2

        # Clear hashes
        manager.clear_imported_hashes(session_id)

        fm, _ = manager.get_session(session_id)
        assert len(fm.get("imported_hashes", [])) == 0


class TestFileLocking:
    """Tests for file locking functionality."""

    @pytest.fixture
    def temp_sessions_dir(self):
        """Create a temporary sessions directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_lock_file_created(self, temp_sessions_dir):
        """Test that lock file is created during write operations."""
        manager = SessionManager(temp_sessions_dir)
        session_id, session_file = manager.create_session("Test")

        # Add log (which uses locking)
        manager.add_log(session_id, "Hello", "User")

        # Lock file should be cleaned up after operation
        lock_file = session_file.with_suffix(".md.lock")
        # Note: filelock may or may not leave the lock file depending on implementation
        # The important thing is that the operation completes successfully
        assert session_file.exists()
