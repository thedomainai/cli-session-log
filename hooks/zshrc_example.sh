# =============================================================================
# CLI Session Log - Shell Configuration Example
# =============================================================================
# Add this to your ~/.zshrc or ~/.bashrc
# Replace /path/to/cli-session-log with your actual installation path
# =============================================================================

# Auto session logging for AI CLI tools
claude() {
    python3 /path/to/cli-session-log/hooks/claude_session_hook.py start "Claude Session"
    command claude "$@"
    python3 /path/to/cli-session-log/hooks/claude_session_hook.py stop
}

gemini() {
    python3 /path/to/cli-session-log/hooks/claude_session_hook.py start "Gemini Session"
    command gemini "$@"
    python3 /path/to/cli-session-log/hooks/claude_session_hook.py stop
}
