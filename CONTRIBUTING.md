# Contributing to COBOL Data Structure

Thank you for your interest in contributing to this project!

## Development Setup

1. Fork and clone the repository
2. Install development dependencies:
   ```bash
   make install-dev
   ```

## Development Workflow

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes

3. Run code quality checks:
   ```bash
   make all
   ```

4. Commit your changes with a clear message

5. Push to your fork and create a pull request

## Code Standards

This project follows Python best practices:

- **PEP 8** style guide (enforced by black and ruff)
- **Type hints** for all functions and methods (checked by mypy)
- **Test coverage** for new features and bug fixes
- **Clear documentation** in docstrings

## Running Tests

```bash
make test
```

## Code Formatting

We use black for code formatting:

```bash
make format
```

## Linting

We use ruff for linting:

```bash
make lint
```

## Type Checking

We use mypy for static type checking:

```bash
make typecheck
```

## Pull Request Process

1. Ensure all tests pass
2. Update documentation as needed
3. Add tests for new features
4. Follow the existing code style
5. Write clear commit messages

## Questions?

Feel free to open an issue for any questions or concerns.
