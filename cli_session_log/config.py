"""Centralized configuration management."""

import os
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None


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

    def __init__(self):
        self._config: dict = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        if not self.CONFIG_FILE.exists():
            return

        if yaml is None:
            return

        try:
            with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        except Exception:
            self._config = {}

    @property
    def sessions_dir(self) -> Path:
        """Get sessions directory from config, environment, or default."""
        # 1. Environment variable (highest priority)
        env_dir = os.environ.get("SESSION_LOG_DIR")
        if env_dir:
            return Path(env_dir)

        # 2. Config file
        if self._config.get("sessions_dir"):
            return Path(self._config["sessions_dir"]).expanduser()

        # 3. Default
        return self.DEFAULT_SESSIONS_DIR

    @property
    def claude_projects_dir(self) -> Path:
        """Get Claude projects directory."""
        if self._config.get("claude_projects_dir"):
            return Path(self._config["claude_projects_dir"]).expanduser()
        return self.CLAUDE_PROJECTS_DIR

    @property
    def gemini_tmp_dir(self) -> Path:
        """Get Gemini tmp directory."""
        if self._config.get("gemini_tmp_dir"):
            return Path(self._config["gemini_tmp_dir"]).expanduser()
        return self.GEMINI_TMP_DIR

    @property
    def task_extractor(self) -> Optional[Path]:
        """Get task extractor path (optional external tool)."""
        if self._config.get("task_extractor"):
            return Path(self._config["task_extractor"]).expanduser()
        return self.DEFAULT_TASK_EXTRACTOR

    def ensure_config_dir(self) -> None:
        """Ensure config directory exists."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)


# Singleton instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
