"""Custom exceptions for cli-session-log."""


class SessionLogError(Exception):
    """Base exception for cli-session-log."""

    pass


class SessionNotFoundError(SessionLogError):
    """Raised when a session cannot be found."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class SessionWriteError(SessionLogError):
    """Raised when a session file cannot be written."""

    def __init__(self, message: str, path: str = ""):
        self.path = path
        super().__init__(message)


class SessionParseError(SessionLogError):
    """Raised when a session file cannot be parsed."""

    def __init__(self, message: str, path: str = ""):
        self.path = path
        super().__init__(message)


class ConfigError(SessionLogError):
    """Raised for configuration errors."""

    pass


class PathTraversalError(ConfigError):
    """Raised when path traversal attack is detected."""

    def __init__(self, path: str, allowed_base: str = ""):
        self.path = path
        self.allowed_base = allowed_base
        super().__init__(f"Path traversal detected: {path}")


class ExtractorError(SessionLogError):
    """Raised when message extraction fails."""

    def __init__(self, message: str, source: str = ""):
        self.source = source
        super().__init__(message)
