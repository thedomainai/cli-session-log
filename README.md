# cli-session-log

CLI session management tool with conversation logs and task tracking. Sessions are stored as Markdown files, compatible with Obsidian and other Markdown editors.

## Features

- Create and manage CLI sessions
- Track conversation logs (User/AI messages)
- Task management with checkbox syntax
- Session status management (active/paused/completed)
- Markdown format for easy viewing in Obsidian

## Installation

```bash
pip install cli-session-log
```

Or install from source:

```bash
git clone https://github.com/yourusername/cli-session-log.git
cd cli-session-log
pip install -e .
```

## Usage

### Create a new session

```bash
session-log new "My Session Title"
```

### List sessions

```bash
session-log list
session-log list --status active
```

### Add conversation logs

```bash
session-log log <session-id> -u "User message here"
session-log log <session-id> -a "AI response here"
```

### Manage tasks

```bash
session-log task add <session-id> "Task description"
session-log task done <session-id> 1
session-log task list <session-id>
```

### Change session status

```bash
session-log status <session-id> paused
session-log status <session-id> active
session-log close <session-id>  # Sets status to completed
```

### View session details

```bash
session-log show <session-id>
```

## Configuration

### Sessions Directory

By default, sessions are stored in `./sessions`. You can change this:

```bash
# Using command line option
session-log --dir /path/to/sessions list

# Using environment variable
export SESSION_LOG_DIR=/path/to/sessions
session-log list
```

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
sessions/
  2025-01/
    session-abc12345.md
    session-def67890.md
  2025-02/
    session-xyz11111.md
```

## License

MIT
