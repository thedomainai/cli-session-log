"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from cli_session_log.config import Config, get_config, reset_config, validate_path
from cli_session_log.exceptions import PathTraversalError


class TestValidatePath:
    """Tests for path validation."""

    def test_validate_path_expands_user(self):
        """Test that ~ is expanded."""
        path = validate_path(Path("~/test"))
        assert str(path).startswith(str(Path.home()))

    def test_validate_path_resolves_absolute(self):
        """Test that path is resolved to absolute."""
        path = validate_path(Path("./relative"))
        assert path.is_absolute()

    def test_validate_path_with_allowed_bases(self):
        """Test validation against allowed base directories."""
        home = Path.home()
        path = validate_path(home / "test", allowed_bases=[home])
        assert path == home / "test"

    def test_validate_path_outside_allowed_bases(self):
        """Test path outside allowed bases raises error."""
        home = Path.home()
        allowed = home / "allowed-only"

        with pytest.raises(PathTraversalError):
            validate_path(Path("/etc/passwd"), allowed_bases=[allowed])

    def test_validate_path_with_dotdot(self):
        """Test path with .. is detected (warning logged)."""
        # This should work but log a warning
        path = validate_path(Path.home() / "foo" / ".." / "bar")
        assert path.is_absolute()


class TestConfig:
    """Tests for Config class."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset config singleton before each test."""
        reset_config()
        yield
        reset_config()

    def test_default_sessions_dir_no_config_file(self):
        """Test default sessions directory when no config file exists."""
        # Patch CONFIG_FILE to a non-existent path
        fake_config = Path("/nonexistent/config.yaml")
        with patch.object(Config, "CONFIG_FILE", fake_config):
            config = Config()
            assert config.sessions_dir == Config.DEFAULT_SESSIONS_DIR

    def test_sessions_dir_from_env(self):
        """Test sessions directory from environment variable."""
        # Use a path under home directory to pass validation
        test_dir = Path.home() / "test-sessions-env"
        with patch.dict(os.environ, {"SESSION_LOG_DIR": str(test_dir)}):
            with patch.object(Config, "CONFIG_FILE", Path("/nonexistent/config.yaml")):
                config = Config()
                assert config.sessions_dir == test_dir

    def test_sessions_dir_from_config_file(self):
        """Test sessions directory from config file."""
        # Create config file under home directory
        config_dir = Path.home() / ".config" / "cli-session-log-test"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.yaml"

        # Sessions dir also under home
        sessions_dir = Path.home() / "test-sessions-config"

        try:
            config_file.write_text(f"sessions_dir: {sessions_dir}")

            with patch.object(Config, "CONFIG_DIR", config_dir):
                with patch.object(Config, "CONFIG_FILE", config_file):
                    config = Config()
                    assert config.sessions_dir == sessions_dir
        finally:
            # Cleanup
            if config_file.exists():
                config_file.unlink()
            if config_dir.exists():
                config_dir.rmdir()

    def test_env_overrides_config_file(self):
        """Test that environment variable has higher priority than config file."""
        config_dir = Path.home() / ".config" / "cli-session-log-test2"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.yaml"

        env_dir = Path.home() / "env-sessions"
        file_dir = Path.home() / "file-sessions"

        try:
            config_file.write_text(f"sessions_dir: {file_dir}")

            with patch.dict(os.environ, {"SESSION_LOG_DIR": str(env_dir)}):
                with patch.object(Config, "CONFIG_DIR", config_dir):
                    with patch.object(Config, "CONFIG_FILE", config_file):
                        config = Config()
                        assert config.sessions_dir == env_dir
        finally:
            if config_file.exists():
                config_file.unlink()
            if config_dir.exists():
                config_dir.rmdir()

    def test_claude_projects_dir_default(self):
        """Test default Claude projects directory."""
        with patch.object(Config, "CONFIG_FILE", Path("/nonexistent/config.yaml")):
            config = Config()
            assert config.claude_projects_dir == Config.CLAUDE_PROJECTS_DIR

    def test_gemini_tmp_dir_default(self):
        """Test default Gemini tmp directory."""
        with patch.object(Config, "CONFIG_FILE", Path("/nonexistent/config.yaml")):
            config = Config()
            assert config.gemini_tmp_dir == Config.GEMINI_TMP_DIR

    def test_task_extractor_default_none(self):
        """Test task extractor is None by default."""
        with patch.object(Config, "CONFIG_FILE", Path("/nonexistent/config.yaml")):
            config = Config()
            assert config.task_extractor is None

    def test_ensure_config_dir(self):
        """Test ensuring config directory exists."""
        test_dir = Path.home() / ".config" / "cli-session-log-ensure-test"
        try:
            with patch.object(Config, "CONFIG_DIR", test_dir):
                with patch.object(Config, "CONFIG_FILE", Path("/nonexistent/config.yaml")):
                    config = Config()
                    config.ensure_config_dir()
                    assert test_dir.exists()
        finally:
            if test_dir.exists():
                test_dir.rmdir()

    def test_ensure_sessions_dir(self):
        """Test ensuring sessions directory exists."""
        test_dir = Path.home() / "test-ensure-sessions"
        try:
            with patch.object(Config, "DEFAULT_SESSIONS_DIR", test_dir):
                with patch.object(Config, "CONFIG_FILE", Path("/nonexistent/config.yaml")):
                    config = Config()
                    config.ensure_sessions_dir()
                    assert test_dir.exists()
        finally:
            if test_dir.exists():
                test_dir.rmdir()


class TestGetConfig:
    """Tests for get_config singleton."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset config singleton before each test."""
        reset_config()
        yield
        reset_config()

    def test_get_config_returns_same_instance(self):
        """Test get_config returns singleton."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_reset_config_clears_singleton(self):
        """Test reset_config clears the singleton."""
        config1 = get_config()
        reset_config()
        config2 = get_config()
        assert config1 is not config2
