# Claude Code Hooks Integration

This directory contains hooks for automatic session logging integration with Claude Code and Gemini CLI.

## Setup

### 1. Shell Alias (Automate Session Start/Stop)

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
# Claude Code with auto session logging
# Replace /path/to/cli-session-log with your actual installation path

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
```

Then reload your shell:
```bash
source ~/.zshrc  # or source ~/.bashrc
```

### 2. Claude Code Settings (Alternative: Hook-based Stop)

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/cli-session-log/hooks/claude_session_hook.py stop"
          }
        ]
      }
    ]
  }
}
```

## Usage

### Automatic Session Management

```bash
# Just use claude or gemini as usual
claude
gemini

# Sessions are automatically started and stopped
```

### Manual Operations

```bash
# Start session
python3 hooks/claude_session_hook.py start "Session Title"

# Check current session
python3 hooks/claude_session_hook.py current

# Add log entry
python3 hooks/claude_session_hook.py log User "User message"
python3 hooks/claude_session_hook.py log AI "AI response"

# Stop session
python3 hooks/claude_session_hook.py stop
```

## Session Storage

Sessions are stored in your configured sessions directory:
```
~/.local/share/cli-session-log/sessions/YYYY-MM/session-XXXXXXXX.md
```

You can customize the sessions directory in `~/.config/cli-session-log/config.yaml`:
```yaml
sessions_dir: ~/path/to/your/sessions
```
