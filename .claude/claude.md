# Project Guidelines for Claude Code

This document contains project-specific guidelines for the COBOL Data Structure Python package.

## Core Principles

1. **Write Pythonic Code**: Follow Python idioms and conventions
2. **Cross-Platform Compatibility**: Code must run correctly on Windows, macOS, and Linux
3. **Type Safety**: Use type hints for all functions and methods
4. **Test Everything**: Write tests for all new features and bug fixes
5. **Keep It Simple**: Avoid over-engineering; prefer clarity over cleverness

## Python Best Practices

### Code Style

- Follow PEP 8 style guide
- Use `black` for formatting (line length: 100)
- Use `ruff` for linting
- Use `mypy` for type checking
- All code must pass: `make all` before committing

### Type Hints

Always use type hints for function signatures:

```python
from typing import List, Optional, Dict, Any
from pathlib import Path

def process_data(
    input_file: Path,
    options: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Process data from input file."""
    ...
```

### Docstrings

Use Google-style docstrings for all public functions, classes, and modules:

```python
def calculate_total(items: List[float], tax_rate: float = 0.0) -> float:
    """Calculate total price including tax.

    Args:
        items: List of item prices.
        tax_rate: Tax rate as decimal (e.g., 0.08 for 8%). Defaults to 0.0.

    Returns:
        Total price including tax.

    Raises:
        ValueError: If tax_rate is negative.

    Example:
        >>> calculate_total([10.0, 20.0], 0.08)
        32.4
    """
    ...
```

### Pythonic Patterns

**Prefer:**
- List comprehensions over `map()` and `filter()`
- Context managers (`with` statements) for resource management
- `pathlib.Path` over `os.path` for file operations
- f-strings over `%` or `.format()` for string formatting
- `dataclasses` or `pydantic` for data structures
- Generator expressions for large datasets

**Example:**
```python
from pathlib import Path

# Good - Pythonic
files = [f for f in Path("data").glob("*.txt") if f.stat().st_size > 0]

# Avoid - Unpythonic
import os
files = []
for f in os.listdir("data"):
    if f.endswith(".txt") and os.path.getsize(os.path.join("data", f)) > 0:
        files.append(os.path.join("data", f))
```

## Cross-Platform Compatibility

### File Paths

**ALWAYS use `pathlib.Path` for file operations:**

```python
from pathlib import Path

# Good - Cross-platform
config_file = Path("config") / "settings.json"
data_dir = Path(__file__).parent / "data"

# Bad - Platform-specific
config_file = "config\\settings.json"  # Windows-only
data_dir = os.path.join(os.path.dirname(__file__), "data")  # Old style
```

### Path Separators

- **Never** hardcode path separators (`/` or `\`)
- Use `Path` objects or `os.path.join()` (though `Path` is preferred)
- Use `Path.as_posix()` only for display/logging, not file operations

### Line Endings

- Git should handle line endings (`.gitattributes`)
- Use `open(file, "r", newline=None)` for text files (default behavior)
- For binary files, always use `"rb"` or `"wb"` mode

### Case Sensitivity

- Assume file systems are case-sensitive (Linux/macOS can be)
- Never rely on case-insensitive file matching
- Use exact case in imports and file references

### Home Directory

```python
from pathlib import Path

# Good - Cross-platform
home = Path.home()
config = home / ".config" / "myapp"

# Bad - Platform-specific
home = os.path.expanduser("~")  # Works but Path.home() is better
config = "/home/user/.config/myapp"  # Linux-only
```

### Environment Variables

```python
import os
from pathlib import Path

# Good - Cross-platform with fallback
cache_dir = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))

# Handle Windows vs Unix differences
if os.name == "nt":  # Windows
    app_data = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
else:  # Unix-like
    app_data = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
```

### Shell Commands

- Avoid shell commands when possible; use Python libraries instead
- If necessary, use `subprocess.run()` with `shell=False`
- Never assume shell availability (Windows cmd vs PowerShell vs bash)

```python
import subprocess

# Good - Cross-platform
result = subprocess.run(
    ["python", "-m", "pytest"],
    capture_output=True,
    text=True,
    check=True
)

# Bad - Platform-specific
os.system("python -m pytest")  # Shell-dependent
```

### File Permissions

- Windows doesn't support Unix permissions
- Use `os.chmod()` carefully with fallback handling
- Check `os.name` or `platform.system()` when needed

```python
import os
import stat

def make_executable(file_path: Path) -> None:
    """Make file executable (Unix-like systems only)."""
    if os.name != "nt":  # Not Windows
        file_path.chmod(file_path.stat().st_mode | stat.S_IXUSR)
```

## Testing Guidelines

### Test Structure

- Place tests in `tests/` directory mirroring `src/` structure
- Use `test_*.py` naming convention
- Group related tests in classes: `class TestFeatureName`
- One test file per module

### Writing Tests

```python
import pytest
from pathlib import Path

def test_feature_description():
    """Test should have clear descriptive name and docstring."""
    # Arrange
    input_data = [1, 2, 3]

    # Act
    result = process_data(input_data)

    # Assert
    assert result == expected_output

@pytest.mark.parametrize("input,expected", [
    ([1, 2], 3),
    ([0, 0], 0),
    ([-1, 1], 0),
])
def test_feature_multiple_cases(input, expected):
    """Use parametrize for multiple test cases."""
    assert sum(input) == expected
```

### Cross-Platform Testing

- Use `tmp_path` fixture for temporary files (automatically cleaned up)
- Test with different path separators (implicitly via `Path`)
- Mock system-specific behavior when needed

```python
def test_file_operations(tmp_path: Path):
    """Test file operations work across platforms."""
    test_file = tmp_path / "subdir" / "test.txt"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("test data")

    assert test_file.exists()
    assert test_file.read_text() == "test data"

def test_platform_specific_feature():
    """Test platform-specific features with appropriate skips."""
    if os.name == "nt":
        pytest.skip("Unix-only feature")

    # Unix-specific test code
```

### Fixtures

Use fixtures for common setup:

```python
@pytest.fixture
def sample_data_file(tmp_path: Path) -> Path:
    """Create sample data file for testing."""
    data_file = tmp_path / "data.txt"
    data_file.write_text("sample data\n")
    return data_file
```

## Error Handling

- Use specific exception types
- Provide helpful error messages
- Don't catch exceptions you can't handle
- Use `raise ... from e` to preserve traceback

```python
def load_config(config_path: Path) -> dict:
    """Load configuration from file.

    Args:
        config_path: Path to configuration file.

    Returns:
        Configuration dictionary.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config file is invalid JSON.
    """
    try:
        return json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {config_path}: {e}") from e
```

## Common Pitfalls to Avoid

### ❌ Don't

```python
# Hardcoded paths
config = "/etc/myapp/config.ini"

# String path concatenation
path = dir + "/" + filename

# Platform-specific commands
os.system("rm -rf /tmp/data")

# Mutable default arguments
def process(items=[]):  # Bug!
    items.append(1)
    return items

# Bare except
try:
    risky_operation()
except:  # Catches everything, including KeyboardInterrupt!
    pass

# Direct file operations without context manager
f = open("file.txt")
data = f.read()
f.close()  # May not be called if exception occurs
```

### ✅ Do

```python
# Use Path objects
from pathlib import Path
config = Path("/etc") / "myapp" / "config.ini"

# Path operations
path = Path(dir) / filename

# Python libraries instead of shell
import shutil
shutil.rmtree(Path("/tmp/data"), ignore_errors=True)

# Immutable defaults
def process(items: Optional[List] = None) -> List:
    if items is None:
        items = []
    items.append(1)
    return items

# Specific exception handling
try:
    risky_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise

# Context managers
with open("file.txt") as f:
    data = f.read()
```

## Code Organization

### Module Structure

```python
"""Module docstring describing purpose.

This module handles COBOL data structure parsing and conversion.
"""

# Standard library imports
import json
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

# Third-party imports
import pytest

# Local imports
from cobol_data_structure.parser import Parser
from cobol_data_structure.utils import validate_input

# Constants
DEFAULT_ENCODING = "utf-8"
MAX_LINE_LENGTH = 80

# Module code...
```

### Package Structure

- Keep modules focused on single responsibility
- Use `__init__.py` to expose public API
- Use `py.typed` marker for type hint support
- Private modules start with underscore: `_internal.py`

## Version Compatibility

- Support Python 3.9+ (as specified in pyproject.toml)
- Don't use features from newer Python versions without updating `requires-python`
- Use `from __future__ import annotations` for forward compatibility if needed

## Documentation

- Update README.md when adding features
- Keep docstrings up to date
- Add examples for complex functionality
- Document any platform-specific behavior

## Pre-Commit Checklist

Before committing code, ensure:

1. ✅ Code is formatted: `make format`
2. ✅ Linting passes: `make lint`
3. ✅ Type checking passes: `make typecheck`
4. ✅ All tests pass: `make test`
5. ✅ New features have tests
6. ✅ Documentation is updated

Run all checks: `make all`

## Additional Resources

- [PEP 8 - Style Guide](https://peps.python.org/pep-0008/)
- [PEP 257 - Docstring Conventions](https://peps.python.org/pep-0257/)
- [pathlib documentation](https://docs.python.org/3/library/pathlib.html)
- [pytest documentation](https://docs.pytest.org/)
- [Type hints cheat sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
