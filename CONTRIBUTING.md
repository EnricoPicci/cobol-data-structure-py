# Contributing to COBOL Anonymizer

Thank you for your interest in contributing to COBOL Anonymizer!

## Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/your-username/cobol-data-structure-py.git
   cd cobol-data-structure-py
   ```

2. Install development dependencies:
   ```bash
   make install-dev
   ```
   Or manually:
   ```bash
   pip install -e ".[dev]"
   ```

3. Verify your setup:
   ```bash
   make test
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
   This runs formatting, linting, type checking, and tests.

4. Commit your changes with a clear message:
   ```bash
   git commit -m "feat: add support for new naming scheme"
   ```

5. Push to your fork and create a pull request

## Code Standards

This project follows Python best practices:

- **PEP 8** style guide (enforced by black and ruff)
- **Type hints** for all functions and methods (checked by mypy)
- **Test coverage** for new features and bug fixes
- **Clear documentation** in docstrings

### Naming Conventions

- Modules: `snake_case` (e.g., `column_handler.py`)
- Classes: `PascalCase` (e.g., `COBOLLine`, `MappingTable`)
- Functions: `snake_case` (e.g., `parse_line()`)
- Constants: `UPPER_CASE` (e.g., `MAX_IDENTIFIER_LENGTH`)

### COBOL-Specific Guidelines

When working with COBOL-related code:

- Never modify PIC clause contents
- Never anonymize EXTERNAL items
- Generated identifiers must be ≤30 characters
- Code must not exceed column 72
- Never create identifiers ending in hyphens
- Never use COBOL reserved words as anonymized names

## Running Tests

```bash
# All tests
make test

# With coverage report
make test-cov

# Specific test file
pytest tests/test_anonymizer.py -v

# Specific test class
pytest tests/test_anonymizer.py::TestLineTransformer -v

# Stop on first failure
pytest -x
```

## Code Formatting

We use black for code formatting with a line length of 100:

```bash
make format
```

Or manually:
```bash
black src tests --line-length 100
```

## Linting

We use ruff for linting:

```bash
make lint
```

Or manually:
```bash
ruff check src tests
```

## Type Checking

We use mypy for static type checking:

```bash
make typecheck
```

Or manually:
```bash
mypy src
```

## Project Structure

```
src/cobol_anonymizer/
├── core/           # Core anonymization logic
│   ├── anonymizer.py    # Main anonymization engine
│   ├── classifier.py    # Identifier classification
│   ├── mapper.py        # Name mapping table
│   ├── tokenizer.py     # COBOL tokenization
│   └── utils.py         # Shared utilities
├── cobol/          # COBOL-specific handling
│   ├── column_handler.py   # 80-column format
│   ├── reserved_words.py   # Reserved word list
│   ├── pic_parser.py       # PIC clause parsing
│   └── copy_resolver.py    # Copybook resolution
├── generators/     # Name generation
│   ├── naming_schemes.py   # Strategy pattern schemes
│   └── name_generator.py   # Name generation logic
└── output/         # Output handling
    ├── writer.py       # File writing
    ├── validator.py    # Output validation
    └── report.py       # Report generation
```

## Adding a New Naming Scheme

1. Add scheme to `NamingScheme` enum in `generators/naming_schemes.py`
2. Create a new strategy class extending `WordBasedNamingStrategy` or `BaseNamingStrategy`
3. Add word lists (adjectives + nouns) if word-based
4. Register in `_STRATEGY_REGISTRY`
5. Add tests in `tests/test_naming_schemes.py`

## Pull Request Process

1. Ensure all tests pass (`make test`)
2. Ensure code is formatted (`make format`)
3. Ensure linting passes (`make lint`)
4. Ensure type checking passes (`make typecheck`)
5. Update documentation as needed
6. Add tests for new features
7. Write clear commit messages following conventional commits:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `refactor:` for code refactoring
   - `test:` for adding tests

## Commit Message Format

```
<type>: <short description>

<optional longer description>

<optional footer>
```

Examples:
```
feat: add FANTASY naming scheme with mythical creatures

fix: handle REDEFINES clause with nested structures

docs: update README with new CLI options

refactor: extract token iteration helper in classifier
```

## Reporting Issues

When reporting issues, please include:

1. A clear description of the problem
2. Steps to reproduce
3. Expected vs actual behavior
4. Sample COBOL code (anonymized if sensitive)
5. Python version and OS

## Questions?

Feel free to open an issue for any questions or concerns.
