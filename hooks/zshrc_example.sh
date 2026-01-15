# =============================================================================
# CLI Session Log - Shell Configuration Example
# =============================================================================
# Add this to your ~/.zshrc or ~/.bashrc
# =============================================================================

# Auto session logging for AI CLI tools
claude() {
    python ~/workspace/obsidian_vault/docs/03_project/00_thedomainai/cli-session-log/hooks/claude_session_hook.py start "Claude Session"
    command claude "$@"
    python ~/workspace/obsidian_vault/docs/03_project/00_thedomainai/cli-session-log/hooks/claude_session_hook.py stop
}

gemini() {
    python ~/workspace/obsidian_vault/docs/03_project/00_thedomainai/cli-session-log/hooks/claude_session_hook.py start "Gemini Session"
    command gemini "$@"
    python ~/workspace/obsidian_vault/docs/03_project/00_thedomainai/cli-session-log/hooks/claude_session_hook.py stop
}
