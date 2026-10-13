# Todo App - Project Context

## Project Overview
A small command-line todo application written in Python. It lets users add, list, complete and delete tasks. Tasks are stored in a local SQLite database.

## Tech Stack
- Python 3.12
- SQLite (via the built-in sqlite3 module)
- argparse for the command-line interface
- pytest for testing
- Black and Ruff for formatting and linting

## Project Structure
- `todo/cli.py` - command-line entry point
- `todo/db.py` - database access layer
- `todo/models.py` - task data model
- `tests/` - pytest test suite

## Coding Rules
- Use type hints on every function signature.
- Follow PEP 8 naming: snake_case for functions and variables, PascalCase for classes.
- Keep functions under 30 lines.
- All database access must go through `db.py`. Never call sqlite3 directly from `cli.py`.
- Every new feature requires at least one pytest test.
- User-facing messages must be in English and must not include stack traces.

## Rule Update (2026-09-28)
Previously, the rule allowed functions up to 50 lines. As of 2026-09-28, the limit is now 30 lines. Older code should be refactored gradually.

## Testing
Run all tests with `pytest -q`. Tests must pass before every commit.