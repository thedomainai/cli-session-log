# cli-session-log

CLI session management tool with conversation logs and task tracking. Sessions are stored as Markdown files, compatible with Obsidian and other Markdown editors.

## Features

- Create and manage CLI sessions
- **Automatic conversation import** from Claude Code and Gemini CLI
- Track conversation logs (User/AI messages)
- Task management with checkbox syntax
- Session status management (active/paused/completed)
- Markdown format for easy viewing in Obsidian

## Installation

```bash
git clone https://github.com/thedomainai/cli-session-log.git
cd cli-session-log
pip install -e .
```

## Quick Start

### Manual Usage

```bash
# Create a new session
session-log new "My Session Title"

# List sessions
session-log list

# Add conversation logs
session-log log <session-id> -u "User message"
session-log log <session-id> -a "AI response"

# Close session
session-log close <session-id>
```

### Automatic Session Logging (Recommended)

Add shell wrapper functions to automatically record sessions when using Claude Code or Gemini CLI.

**Add to your `~/.zshrc` or `~/.bashrc`:**

```bash
# Auto session logging for AI CLI tools
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

Now when you run `claude` or `gemini`, sessions are automatically:
1. Created when you start
2. Conversation imported from the AI tool's history
3. Closed when you exit

## Configuration

### Default Paths

| Item | Default Location |
|------|------------------|
| Sessions | `~/.local/share/cli-session-log/sessions/` |
| Config | `~/.config/cli-session-log/config.yaml` |
| State | `~/.config/cli-session-log/` |

### Custom Configuration

Create `~/.config/cli-session-log/config.yaml`:

```yaml
# Custom sessions directory (e.g., for Obsidian vault)
sessions_dir: ~/Documents/obsidian-vault/sessions

# Optional: Custom AI tool paths (usually not needed)
# claude_projects_dir: ~/.claude/projects
# gemini_tmp_dir: ~/.gemini/tmp

# Optional: External task extractor script
# task_extractor: ~/tools/task_extractor.py
```

### Environment Variables

```bash
# Override sessions directory
export SESSION_LOG_DIR=/path/to/sessions
```

### Command Line Option

```bash
session-log --dir /path/to/sessions list
```

**Priority:** Command line > Environment variable > Config file > Default

## CLI Commands

| Command | Description |
|---------|-------------|
| `session-log new [title]` | Create a new session |
| `session-log list [--status STATUS]` | List sessions |
| `session-log show <id>` | Show session details |
| `session-log log <id> -u/-a "msg"` | Add log entry |
| `session-log task add <id> "text"` | Add task |
| `session-log task done <id> <num>` | Complete task |
| `session-log task list <id>` | List tasks |
| `session-log status <id> <status>` | Change status |
| `session-log close <id>` | Close session |

## Session File Format

Sessions are stored as Markdown files with YAML frontmatter:

```markdown
---
session_id: abc12345
title: My Session
created_at: '2025-01-15T10:00:00'
updated_at: '2025-01-15T12:30:00'
status: active
tags: []
---

# Session: My Session

## Tasks
- [x] Completed task
- [ ] Pending task

## Conversation Log

### 2025-01-15 10:00:00
**User**: Hello, I need help with...

### 2025-01-15 10:01:00
**AI**: Sure, I can help you with...
```

## Directory Structure

```
~/.local/share/cli-session-log/
  sessions/
    2025-01/
      session-abc12345.md
      session-def67890.md
    2025-02/
      session-xyz11111.md
```

## How Automatic Import Works

When a session ends (via the shell wrapper), the tool:

1. Finds the latest conversation file from the AI tool:
   - **Claude Code**: `~/.claude/projects/*/*.jsonl`
   - **Gemini CLI**: `~/.gemini/tmp/*/chats/session-*.json`

2. Extracts user and AI messages from the conversation

3. Appends them to the session Markdown file

## Requirements

- Python 3.8+
- PyYAML (optional, for config file support)
- python-frontmatter

## License

MIT
