# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-01-22

### Added

- Initial release
- Session management with Markdown files
- YAML frontmatter for metadata
- Automatic conversation import from Claude Code and Gemini CLI
- Task management with checkbox syntax
- Session status management (active/paused/completed/archived)
- Multi-terminal support via CURSOR_TERMINAL_ID
- File locking for concurrent access safety
- XDG Base Directory compliant paths
- Configurable sessions directory

### CLI Commands

- `session-log new [title]` - Create a new session
- `session-log list [--status STATUS]` - List sessions
- `session-log show <id>` - Show session details
- `session-log log <id> -u/-a "msg"` - Add log entry
- `session-log task add <id> "text"` - Add task
- `session-log task done <id> <num>` - Complete task
- `session-log task list <id>` - List tasks
- `session-log status <id> <status>` - Change status
- `session-log close <id>` - Close session
- `session-log stats` - Show statistics

### Extractors

- Claude Code extractor (`.claude/projects/` JSONL files)
- Gemini CLI extractor (`.gemini/tmp/` JSON files)

[Unreleased]: https://github.com/thedomainai/cli-session-log/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/thedomainai/cli-session-log/releases/tag/v0.1.0
