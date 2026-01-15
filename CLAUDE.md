# GitHub Automator - Claude Code Project Memory

## Project Overview

This repository provides an automated GitHub Issue-driven development workflow with Claude Code.
All GitHub content (Issues, commits, PRs) must be written in **native English**.

## Development Workflow

### Issue-Driven Development

1. **Start Task**: Use `/start-task` to create an Issue and feature branch
2. **Development**: Implement the feature with Claude Code assistance
3. **Commit**: Use `/quick-commit` for intermediate commits
4. **Finish Task**: Use `/finish-task` to push and create a PR

### Branch Naming Convention

```
<type>/<issue-number>-<short-description>
```

**Important**: No `#` symbol in branch names (causes shell issues).

Examples:
- `feat/1-user-authentication`
- `fix/23-login-redirect-bug`
- `docs/45-api-documentation`

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Task State Management

The current task state is stored in `.claude/current-task.json`:

```json
{
  "issue_number": 1,
  "issue_title": "Add user authentication",
  "branch": "feat/1-user-authentication",
  "type": "feat",
  "description": "Implement user login and registration",
  "created_at": "2024-01-15T12:00:00Z"
}
```

This file:
- Is created by `/start-task`
- Is read by `/quick-commit` and `/finish-task` for Issue reference
- Is deleted by `/finish-task` after PR creation
- Should be in `.gitignore`

## Git Rules

### Commit Message Format (Conventional Commits)

```
<type>(<scope>): <description> (#<issue>)

[optional body]

[optional footer]
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

**Types:**
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring without functionality changes
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(auth): implement JWT token validation (#12)
fix(api): resolve null pointer in user endpoint (#34)
docs(readme): add installation instructions (#56)
```

### Important Rules

- **All commit messages MUST be in English**
- **Always reference the Issue number** in commits: `(#123)`
- **Never commit directly to main** - always use feature branches
- **PR titles** should match the Issue title
- **PR body** must include `Closes #<issue-number>`

## Slash Commands

| Command | Description |
|---------|-------------|
| `/start-task` | Create Issue + branch + state file, start development |
| `/quick-commit` | Quick commit with auto-generated message (reads state) |
| `/finish-task` | Commit, push, create PR, clean up state |

## File Structure

```
.github/
├── ISSUE_TEMPLATE/     # Issue templates
└── PULL_REQUEST_TEMPLATE.md
.claude/
├── commands/           # Slash commands
├── rules/              # Additional rules
├── settings.json       # Hooks configuration
└── current-task.json   # Current task state (gitignored)
```

## Code Style

- Follow existing patterns in the codebase
- Write clear, self-documenting code
- Add comments only when logic is not self-evident
