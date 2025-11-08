# Python Code Directives

## Dependency Management
- You MUST NOT edit `pyproject.toml` directly unless explicitly told to do so.
- You MUST use `poetry run <command>` to execute commands within the project's virtual environment.
- You MUST use `poetry add <package>` or `poetry remove <package>` for dependency management.
- You MUST use `poetry` or `make` commands to ensure proper environment isolation.

## Schema and Configuration Changes
- You MUST update the JSON schema first when changing the configuration structure.
- You MUST ensure dataclass attribute names match the JSON schema property names exactly.
- You SHOULD maintain alignment with boto3 API parameter names for `assumed_role` properties.

## Code Style
### Formatting
- You MUST use the ruff formatter with an 88-character line length.
- Files MUST end with a single newline.
- You MUST NOT have trailing whitespace.
- JSON files MUST NOT contain a Byte Order Mark (BOM).

### Naming Conventions
- Class names MUST use `PascalCase`.
- Functions and variables MUST use `snake_case`.
- Constants MUST use `UPPER_SNAKE_CASE`.
- Internal-only members SHOULD be prefixed with an underscore (`_`).

### Import Style
- You MUST set imports with standard library first, then third-party, then local application imports.
- You MUST use `ruff` to enforce this.
- You MUST define imports at the top of each file, never inline within a function.
- You SHOULD use `from __future__ import annotations` for type hints.
- You SHOULD use a `TYPE_CHECKING` block for type-only imports.

### Error Handling
- You MUST use `as error` for the variable in an `except` block (e.g., `except ValueError as error:`).
- You MUST log errors using the project's configured logger.
- You MUST, when logging caught exceptions, follow this pattern:
  1. Log a simple, descriptive error message: `LOG.error("Operation failed")`
  2. Log the full exception details: `LOG.exception(error)`
- You SHOULD use specific exception types (e.g., `botocore.exceptions.ClientError`) instead of generic `Exception`.

### Logging and Output
- You MUST NOT use icons or emojis in logging messages or code comments.
- You MUST use clear and professional text-only logging messages.
- You SHOULD keep log messages concise and informative.

## Commands
### Testing
- **Run tests:** `make test`
- **Run tests with coverage:** `make coverage`
