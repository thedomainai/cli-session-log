"""Centralized configuration management."""

import os
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None

from .exceptions import PathTraversalError
from .logging_config import get_logger

logger = get_logger("config")


def validate_path(path: Path, allowed_bases: Optional[list[Path]] = None) -> Path:
    """Validate and resolve a path, checking for traversal attacks.

    Args:
        path: Path to validate
        allowed_bases: Optional list of allowed base directories

    Returns:
        Resolved absolute path

    Raises:
        PathTraversalError: If path contains traversal sequences outside allowed bases
    """
    # Expand user (~) and resolve to absolute path
    resolved = path.expanduser().resolve()

    # Check for suspicious patterns in original path string
    path_str = str(path)
    if ".." in path_str:
        logger.warning("Path contains traversal sequence: %s", path)

    # If allowed_bases specified, verify path is under one of them
    if allowed_bases:
        is_allowed = False
        for base in allowed_bases:
            base_resolved = base.expanduser().resolve()
            try:
                resolved.relative_to(base_resolved)
                is_allowed = True
                break
            except ValueError:
                continue

        if not is_allowed:
            logger.error(
                "Path traversal detected: %s not under allowed bases %s",
                resolved,
                [str(b) for b in allowed_bases]
            )
            raise PathTraversalError(str(path), str(allowed_bases))

    return resolved


class Config:
    """Application configuration."""

    # Default paths (XDG Base Directory compliant)
    DEFAULT_SESSIONS_DIR = Path.home() / ".local" / "share" / "cli-session-log" / "sessions"
    CONFIG_DIR = Path.home() / ".config" / "cli-session-log"
    CONFIG_FILE = CONFIG_DIR / "config.yaml"

    # State files
    STATE_FILE = CONFIG_DIR / "current_session.txt"
    AI_TYPE_FILE = CONFIG_DIR / "current_ai_type.txt"

    # AI tool paths (standard locations)
    CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
    GEMINI_TMP_DIR = Path.home() / ".gemini" / "tmp"

    # External tools (optional - None by default)
    DEFAULT_TASK_EXTRACTOR: Optional[Path] = None

    # Allowed base directories for session storage (security)
    ALLOWED_SESSION_BASES = [
        Path.home(),  # Anywhere under home directory is allowed
    ]

    def __init__(self):
        self._config: dict = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        if not self.CONFIG_FILE.exists():
            logger.debug("Config file not found: %s", self.CONFIG_FILE)
            return

        if yaml is None:
            logger.warning("PyYAML not installed, skipping config file")
            return

        try:
            with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
            logger.debug("Loaded config from: %s", self.CONFIG_FILE)
        except yaml.YAMLError as e:
            logger.error("Failed to parse config file: %s", e)
            self._config = {}
        except OSError as e:
            logger.error("Failed to read config file: %s", e)
            self._config = {}

    @property
    def sessions_dir(self) -> Path:
        """Get sessions directory from config, environment, or default.

        Returns:
            Validated path to sessions directory

        Raises:
            PathTraversalError: If configured path is outside allowed bases
        """
        path: Path

        # 1. Environment variable (highest priority)
        env_dir = os.environ.get("SESSION_LOG_DIR")
        if env_dir:
            path = Path(env_dir)
        # 2. Config file
        elif self._config.get("sessions_dir"):
            path = Path(self._config["sessions_dir"])
        # 3. Default
        else:
            return self.DEFAULT_SESSIONS_DIR

        # Validate the path
        return validate_path(path, self.ALLOWED_SESSION_BASES)

    @property
    def claude_projects_dir(self) -> Path:
        """Get Claude projects directory."""
        if self._config.get("claude_projects_dir"):
            path = Path(self._config["claude_projects_dir"])
            return validate_path(path, [Path.home()])
        return self.CLAUDE_PROJECTS_DIR

    @property
    def gemini_tmp_dir(self) -> Path:
        """Get Gemini tmp directory."""
        if self._config.get("gemini_tmp_dir"):
            path = Path(self._config["gemini_tmp_dir"])
            return validate_path(path, [Path.home()])
        return self.GEMINI_TMP_DIR

    @property
    def task_extractor(self) -> Optional[Path]:
        """Get task extractor path (optional external tool)."""
        if self._config.get("task_extractor"):
            path = Path(self._config["task_extractor"])
            return validate_path(path, [Path.home()])
        return self.DEFAULT_TASK_EXTRACTOR

    def ensure_config_dir(self) -> None:
        """Ensure config directory exists."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def ensure_sessions_dir(self) -> None:
        """Ensure sessions directory exists."""
        self.sessions_dir.mkdir(parents=True, exist_ok=True)


# Singleton instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> None:
    """Reset the global config instance (for testing)."""
    global _config
    _config = None
