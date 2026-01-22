"""Centralized configuration management."""

import os
from pathlib import Path
from typing import Optional

import yaml

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
        # If no allowed_bases specified, reject paths with traversal sequences
        if not allowed_bases:
            raise PathTraversalError(str(path), "no base directories allowed")
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

    # State files (legacy - single session)
    STATE_FILE = CONFIG_DIR / "current_session.txt"
    AI_TYPE_FILE = CONFIG_DIR / "current_ai_type.txt"

    # State directory for multi-session support
    STATE_DIR = CONFIG_DIR / "sessions"

    # Supported AI types
    AI_TYPES = ("claude", "gemini")

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

    def ensure_state_dir(self) -> None:
        """Ensure state directory for multi-session support exists."""
        self.STATE_DIR.mkdir(parents=True, exist_ok=True)

    def ensure_sessions_dir(self) -> None:
        """Ensure sessions directory exists."""
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def get_terminal_id(self) -> Optional[str]:
        """Get terminal ID from environment variable.

        Returns:
            Terminal ID if available, None otherwise
        """
        return os.environ.get("CURSOR_TERMINAL_ID")

    def get_session_state_file(self, ai_type: str, cwd: str, terminal_id: Optional[str] = None) -> Path:
        """Get state file path for a specific AI type and terminal/directory.

        Priority:
        1. terminal_id parameter (if provided)
        2. CURSOR_TERMINAL_ID environment variable
        3. Fallback to cwd-based (for non-Cursor environments)

        Args:
            ai_type: AI type (claude/gemini)
            cwd: Working directory path (used as fallback)
            terminal_id: Optional terminal ID override

        Returns:
            Path to the session state file
        """
        # Priority 1: explicit terminal_id parameter
        # Priority 2: CURSOR_TERMINAL_ID environment variable
        tid = terminal_id or self.get_terminal_id()

        if tid:
            # Terminal ID based (preferred - supports multiple terminals in same dir)
            return self.STATE_DIR / f"{tid}_{ai_type}.json"
        else:
            # Fallback: cwd-based (for non-Cursor environments)
            safe_cwd = cwd.replace("/", "_").replace("\\", "_").strip("_")
            if not safe_cwd:
                safe_cwd = "default"
            return self.STATE_DIR / f"{ai_type}_{safe_cwd}.json"

    def get_ai_type_state_file(self, ai_type: str) -> Path:
        """Get the state file for a specific AI type (legacy compatibility).

        Args:
            ai_type: AI type (claude/gemini)

        Returns:
            Path to the AI type specific state file
        """
        return self.CONFIG_DIR / f"{ai_type}_session_id.txt"

    def list_active_sessions(self, ai_type: Optional[str] = None) -> list[Path]:
        """List all active session state files.

        Args:
            ai_type: Optional filter by AI type

        Returns:
            List of session state file paths
        """
        if not self.STATE_DIR.exists():
            return []

        if ai_type:
            # Match both terminal-based ({terminal_id}_{ai_type}.json)
            # and cwd-based ({ai_type}_{safe_cwd}.json) patterns
            terminal_pattern = f"*_{ai_type}.json"
            cwd_pattern = f"{ai_type}_*.json"
            files = set(self.STATE_DIR.glob(terminal_pattern))
            files.update(self.STATE_DIR.glob(cwd_pattern))
            return list(files)
        else:
            return list(self.STATE_DIR.glob("*.json"))

    def find_session_by_terminal_id(self, terminal_id: str, ai_type: Optional[str] = None) -> Optional[Path]:
        """Find session state file by terminal ID.

        Args:
            terminal_id: Terminal ID to search for
            ai_type: Optional AI type filter

        Returns:
            Path to session state file if found, None otherwise
        """
        if not self.STATE_DIR.exists():
            return None

        if ai_type:
            state_file = self.STATE_DIR / f"{terminal_id}_{ai_type}.json"
            return state_file if state_file.exists() else None
        else:
            # Search for any AI type
            for at in self.AI_TYPES:
                state_file = self.STATE_DIR / f"{terminal_id}_{at}.json"
                if state_file.exists():
                    return state_file
            return None


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
