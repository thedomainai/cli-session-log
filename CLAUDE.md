# cli-session-log - Claude Code Project Memory

## Project Overview

CLI session management tool with conversation logs and task tracking.
All GitHub content (Issues, commits, PRs) must be written in **native English**.

---

## IMPORTANT: Automatic Workflow (Full-Auto Mode)

**Claude Code MUST automatically execute the following workflow without waiting for user commands.**

### When User Requests a New Feature/Task:

1. **IMMEDIATELY create a GitHub Issue** using `gh issue create`
   - Title and body in native English
   - Apply appropriate labels

2. **Create a feature branch** linked to the Issue
   - Format: `<type>/<issue-number>-<short-description>`

3. **Save task state** to `.claude/current-task.json`

4. **Implement the feature**

5. **Commit changes** with Conventional Commits format
   - Always reference Issue number: `(#<issue>)`

6. **When implementation is complete**, automatically:
   - Push to remote
   - Create Pull Request with `Closes #<issue>`
   - Clean up state file

### Automatic Triggers:

| Situation | Action |
|-----------|--------|
| User says "implement X" / "add X" / "create X" | → Create Issue + branch, start work |
| Significant code changes made | → Commit with proper message |
| Feature implementation complete | → Push + Create PR |
| User says "done" / "finish" / "complete" | → Finalize PR if not already done |

---

## Project-Specific Information

### Tech Stack
- Python 3.8+
- argparse for CLI
- YAML for config
- Markdown for session files

### Key Files
- `cli_session_log/cli.py` - CLI commands
- `cli_session_log/session.py` - Session management logic

### Commands
```bash
session-log new "Title"      # Create session
session-log list             # List sessions
session-log show <id>        # Show session
session-log log <id> -u/-a   # Add log entry
session-log task <action>    # Manage tasks
session-log stats            # Show statistics
```

---

## Git Rules

### Branch Naming
```
<type>/<issue-number>-<short-description>
```

### Commit Format (Conventional Commits)
```
<type>(<scope>): <description> (#<issue>)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Code Style

- Follow existing patterns in the codebase
- Type hints for function parameters
- Docstrings for public functions
