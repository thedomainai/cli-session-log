# Contributing to cli-session-log

Thank you for your interest in contributing to cli-session-log! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/thedomainai/cli-session-log.git
   cd cli-session-log
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install in development mode with dev dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cli_session_log --cov-report=term-missing

# Run specific test file
pytest tests/test_session.py -v
```

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Use the bug report template
3. Include:
   - Python version
   - OS and version
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages/logs

### Suggesting Features

1. Check existing issues and discussions
2. Use the feature request template
3. Describe the use case and expected behavior

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch:
   ```bash
   git checkout -b feat/your-feature-name
   ```

3. Make your changes following the code style guidelines

4. Write or update tests as needed

5. Run tests and ensure they pass:
   ```bash
   pytest
   ```

6. Commit with conventional commit messages:
   ```bash
   git commit -m "feat(scope): add new feature"
   ```

7. Push and create a Pull Request

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(cli): add stats command for session statistics
fix(session): handle empty frontmatter gracefully
docs(readme): update installation instructions
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function parameters and return values
- Write docstrings for public functions and classes
- Keep functions focused and reasonably sized

## Project Structure

```
cli-session-log/
├── cli_session_log/       # Main package
│   ├── __init__.py
│   ├── cli.py            # CLI commands
│   ├── session.py        # Session management
│   ├── config.py         # Configuration
│   ├── constants.py      # Constants and enums
│   ├── exceptions.py     # Custom exceptions
│   └── extractors/       # AI tool extractors
├── hooks/                 # Shell integration hooks
├── tests/                 # Test suite
└── pyproject.toml        # Project configuration
```

## Questions?

Feel free to open an issue for any questions about contributing.
