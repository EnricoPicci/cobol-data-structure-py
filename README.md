# COBOL Data Structure

A Python library for handling COBOL data structures.

## Installation

### From source

```bash
pip install -e .
```

### For development

```bash
pip install -e ".[dev]"
```

## Usage

```python
from cobol_data_structure import __version__

print(__version__)
```

## Development

### Setup

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

### Running Tests

```bash
pytest
```

### Code Quality

This project uses several tools to maintain code quality:

- **black**: Code formatting
- **ruff**: Linting
- **mypy**: Type checking
- **pytest**: Testing

Run all checks:

```bash
# Format code
black src tests

# Lint code
ruff src tests

# Type check
mypy src

# Run tests with coverage
pytest
```

## Project Structure

```
cobol-data-structure-py/
├── src/
│   └── cobol_data_structure/
│       ├── __init__.py
│       └── py.typed
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_example.py
├── pyproject.toml
├── README.md
└── .gitignore
```

## License

MIT
