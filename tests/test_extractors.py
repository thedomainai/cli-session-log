"""Tests for conversation extractors."""

import json
import tempfile
from pathlib import Path

import pytest

from cli_session_log.exceptions import ExtractorError
from cli_session_log.extractors import ClaudeExtractor, GeminiExtractor, Message


class TestMessage:
    """Tests for Message dataclass."""

    def test_message_creation(self):
        """Test creating a Message."""
        msg = Message(role="User", content="Hello", timestamp="2025-01-01")

        assert msg.role == "User"
        assert msg.content == "Hello"
        assert msg.timestamp == "2025-01-01"

    def test_message_truncate(self):
        """Test truncating message content."""
        msg = Message(role="User", content="A" * 2000)
        truncated = msg.truncate(100)

        assert len(truncated.content) == 100
        assert truncated.role == msg.role

    def test_message_truncate_short_content(self):
        """Test truncate doesn't modify short content."""
        msg = Message(role="User", content="Short")
        truncated = msg.truncate(100)

        assert truncated.content == "Short"
        assert truncated is msg  # Same object returned


class TestClaudeExtractor:
    """Tests for Claude Code extractor."""

    @pytest.fixture
    def temp_claude_dir(self):
        """Create a temporary Claude projects directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_jsonl_content(self):
        """Sample Claude Code JSONL content."""
        entries = [
            {
                "type": "user",
                "message": {"role": "user", "content": "Hello Claude"},
                "timestamp": "2025-01-01T10:00:00"
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Hello! How can I help?"}]
                },
                "timestamp": "2025-01-01T10:00:01"
            },
            {
                "type": "user",
                "message": {"role": "user", "content": "What is Python?"},
                "timestamp": "2025-01-01T10:01:00"
            },
        ]
        return "\n".join(json.dumps(e) for e in entries)

    def test_find_latest_session(self, temp_claude_dir, sample_jsonl_content):
        """Test finding latest session file."""
        project_dir = temp_claude_dir / "project1"
        project_dir.mkdir()

        # Create two session files
        session1 = project_dir / "session1.jsonl"
        session2 = project_dir / "session2.jsonl"

        session1.write_text(sample_jsonl_content)
        session2.write_text(sample_jsonl_content)

        # Make session2 newer
        import time
        time.sleep(0.1)
        session2.touch()

        extractor = ClaudeExtractor(temp_claude_dir)
        latest = extractor.find_latest_session()

        assert latest == session2

    def test_find_latest_session_no_dir(self, temp_claude_dir):
        """Test finding session when directory doesn't exist."""
        extractor = ClaudeExtractor(temp_claude_dir / "nonexistent")
        assert extractor.find_latest_session() is None

    def test_find_latest_session_no_files(self, temp_claude_dir):
        """Test finding session when no JSONL files exist."""
        project_dir = temp_claude_dir / "project1"
        project_dir.mkdir()

        extractor = ClaudeExtractor(temp_claude_dir)
        assert extractor.find_latest_session() is None

    def test_extract_messages(self, temp_claude_dir, sample_jsonl_content):
        """Test extracting messages from JSONL file."""
        project_dir = temp_claude_dir / "project1"
        project_dir.mkdir()
        session_file = project_dir / "session.jsonl"
        session_file.write_text(sample_jsonl_content)

        extractor = ClaudeExtractor(temp_claude_dir)
        messages = extractor.extract_messages(session_file)

        assert len(messages) == 3
        assert messages[0].role == "User"
        assert messages[0].content == "Hello Claude"
        assert messages[1].role == "AI"
        assert "Hello!" in messages[1].content

    def test_extract_messages_with_limit(self, temp_claude_dir, sample_jsonl_content):
        """Test extracting limited number of messages."""
        project_dir = temp_claude_dir / "project1"
        project_dir.mkdir()
        session_file = project_dir / "session.jsonl"
        session_file.write_text(sample_jsonl_content)

        extractor = ClaudeExtractor(temp_claude_dir)
        messages = extractor.extract_messages(session_file, limit=2)

        assert len(messages) == 2
        # Should return last 2 messages
        assert messages[0].role == "AI"
        assert messages[1].role == "User"

    def test_extract_messages_malformed_json(self, temp_claude_dir):
        """Test handling malformed JSON lines."""
        project_dir = temp_claude_dir / "project1"
        project_dir.mkdir()
        session_file = project_dir / "session.jsonl"

        content = '{"type": "user", "message": {"role": "user", "content": "Valid"}}\n'
        content += "invalid json line\n"
        content += '{"type": "user", "message": {"role": "user", "content": "Also valid"}}'
        session_file.write_text(content)

        extractor = ClaudeExtractor(temp_claude_dir)
        messages = extractor.extract_messages(session_file)

        # Should extract 2 valid messages, skip 1 invalid
        assert len(messages) == 2

    def test_extract_messages_file_not_found(self, temp_claude_dir):
        """Test error handling for missing file."""
        extractor = ClaudeExtractor(temp_claude_dir)

        with pytest.raises(ExtractorError):
            extractor.extract_messages(temp_claude_dir / "nonexistent.jsonl")

    def test_extract_latest(self, temp_claude_dir, sample_jsonl_content):
        """Test extracting from latest session."""
        project_dir = temp_claude_dir / "project1"
        project_dir.mkdir()
        session_file = project_dir / "session.jsonl"
        session_file.write_text(sample_jsonl_content)

        extractor = ClaudeExtractor(temp_claude_dir)
        messages = extractor.extract_latest()

        assert len(messages) == 3


class TestGeminiExtractor:
    """Tests for Gemini extractor."""

    @pytest.fixture
    def temp_gemini_dir(self):
        """Create a temporary Gemini tmp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_json_content(self):
        """Sample Gemini session JSON content."""
        return json.dumps({
            "messages": [
                {"type": "user", "content": "Hello Gemini", "timestamp": "2025-01-01T10:00:00"},
                {"type": "model", "content": "Hello! How can I assist?", "timestamp": "2025-01-01T10:00:01"},
                {"type": "user", "content": "What is AI?", "timestamp": "2025-01-01T10:01:00"},
            ]
        })

    def test_find_latest_session(self, temp_gemini_dir, sample_json_content):
        """Test finding latest Gemini session file."""
        project_dir = temp_gemini_dir / "project1" / "chats"
        project_dir.mkdir(parents=True)

        session1 = project_dir / "session-001.json"
        session2 = project_dir / "session-002.json"

        session1.write_text(sample_json_content)
        session2.write_text(sample_json_content)

        # Make session2 newer
        import time
        time.sleep(0.1)
        session2.touch()

        extractor = GeminiExtractor(temp_gemini_dir)
        latest = extractor.find_latest_session()

        assert latest == session2

    def test_find_latest_session_no_dir(self, temp_gemini_dir):
        """Test finding session when directory doesn't exist."""
        extractor = GeminiExtractor(temp_gemini_dir / "nonexistent")
        assert extractor.find_latest_session() is None

    def test_find_latest_session_no_chats(self, temp_gemini_dir):
        """Test finding session when no chats directory exists."""
        project_dir = temp_gemini_dir / "project1"
        project_dir.mkdir()  # No 'chats' subdirectory

        extractor = GeminiExtractor(temp_gemini_dir)
        assert extractor.find_latest_session() is None

    def test_extract_messages(self, temp_gemini_dir, sample_json_content):
        """Test extracting messages from JSON file."""
        project_dir = temp_gemini_dir / "project1" / "chats"
        project_dir.mkdir(parents=True)
        session_file = project_dir / "session-001.json"
        session_file.write_text(sample_json_content)

        extractor = GeminiExtractor(temp_gemini_dir)
        messages = extractor.extract_messages(session_file)

        assert len(messages) == 3
        assert messages[0].role == "User"
        assert messages[0].content == "Hello Gemini"
        assert messages[1].role == "AI"
        assert "Hello!" in messages[1].content

    def test_extract_messages_with_limit(self, temp_gemini_dir, sample_json_content):
        """Test extracting limited number of messages."""
        project_dir = temp_gemini_dir / "project1" / "chats"
        project_dir.mkdir(parents=True)
        session_file = project_dir / "session-001.json"
        session_file.write_text(sample_json_content)

        extractor = GeminiExtractor(temp_gemini_dir)
        messages = extractor.extract_messages(session_file, limit=2)

        assert len(messages) == 2

    def test_extract_messages_invalid_json(self, temp_gemini_dir):
        """Test handling invalid JSON file."""
        project_dir = temp_gemini_dir / "project1" / "chats"
        project_dir.mkdir(parents=True)
        session_file = project_dir / "session-001.json"
        session_file.write_text("not valid json")

        extractor = GeminiExtractor(temp_gemini_dir)

        with pytest.raises(ExtractorError):
            extractor.extract_messages(session_file)

    def test_extract_messages_file_not_found(self, temp_gemini_dir):
        """Test error handling for missing file."""
        extractor = GeminiExtractor(temp_gemini_dir)

        with pytest.raises(ExtractorError):
            extractor.extract_messages(temp_gemini_dir / "nonexistent.json")

    def test_extract_messages_empty_messages(self, temp_gemini_dir):
        """Test handling session with no messages."""
        project_dir = temp_gemini_dir / "project1" / "chats"
        project_dir.mkdir(parents=True)
        session_file = project_dir / "session-001.json"
        session_file.write_text('{"messages": []}')

        extractor = GeminiExtractor(temp_gemini_dir)
        messages = extractor.extract_messages(session_file)

        assert messages == []

    def test_extract_latest(self, temp_gemini_dir, sample_json_content):
        """Test extracting from latest session."""
        project_dir = temp_gemini_dir / "project1" / "chats"
        project_dir.mkdir(parents=True)
        session_file = project_dir / "session-001.json"
        session_file.write_text(sample_json_content)

        extractor = GeminiExtractor(temp_gemini_dir)
        messages = extractor.extract_latest()

        assert len(messages) == 3
