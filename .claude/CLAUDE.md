# CLAUDE.md - Project Guide for Claude Code

## Project Overview

**COBOL Anonymizer** is a Python tool that automatically anonymizes COBOL source code while preserving exact logical equivalence and structure. It transforms customer-specific COBOL code into generic, non-identifiable code suitable for public distribution.

## Quick Commands

```bash
# Run all tests (coverage report included automatically)
pytest

# Run all checks (format, lint, typecheck, test)
make all

# Generate HTML coverage report
make test-cov

# Run specific test file
pytest tests/test_anonymizer.py

# Format code
make format

# Lint code
make lint

# Type checking
make typecheck

# Run the CLI
python -m cobol_anonymizer --input <dir> --output <dir>
```

## Project Structure

```
src/cobol_anonymizer/
├── core/           # Core anonymization: anonymizer, classifier, mapper, tokenizer
├── cobol/          # COBOL-specific: column_handler, reserved_words, pic_parser
├── generators/     # Name generation: naming_schemes (5 strategies)
└── output/         # Output handling: writer, validator, report

tests/              # Comprehensive pytest suite
docs/               # Documentation (design, plans, analysis)
Makefile            # Development commands (make help for list)
README.md           # User documentation
CONTRIBUTING.md     # Contributor guidelines
```

## Documentation Naming Convention

When creating documents in the `docs/` folder in response to prompts from `prompts_for_claude_code/`:
- Prefix the document name with the prompt number (e.g., `15-DOCUMENT_NAME.md`)
- The prefix should match the prompt that triggered the document creation
- Check `prompts_for_claude_code/` for the current highest prompt number
- Add the new document to the "## Documentation" section of `README.md`

## Architecture

### Processing Pipeline (4 phases)
1. **Discovery**: Scan files, build COPY dependency graph, detect circular deps
2. **Mapping**: Generate consistent identifier mappings globally
3. **Transform**: Apply mappings respecting PIC clauses and column format
4. **Output**: Write files, validate, generate reports

### Token-Based Approach
This project uses **token-based processing with pattern recognition**, not AST parsing or pure regex. This is intentional because:
- COBOL's fixed-format column structure is critical
- Full AST parsing is too complex for COBOL's many dialects
- Column-aware tokenization is maintainable and reliable

## COBOL Domain Knowledge

### Column Structure (Fixed Format)
COBOL uses 80-column fixed format:
- **Cols 1-6**: Sequence/change tags (preserved as-is)
- **Col 7**: Indicator (`*` comment, `-` continuation, `D` debug)
- **Cols 8-11**: Area A (divisions, sections, level numbers)
- **Cols 12-72**: Area B (actual code)
- **Cols 73-80**: Identification area (often ignored)

### Critical Constraints
- **Max identifier length**: 30 characters (COBOL standard)
- **Column 72 limit**: Code must not exceed column 72
- **No trailing hyphens**: Identifiers cannot end with `-`
- **Reserved words**: ~400 COBOL reserved words must be avoided

### Never Anonymize
- **PIC clauses**: Data layout descriptors (e.g., `PIC X(10)`, `PIC 9(5)V99`)
- **EXTERNAL items**: Cross-program visible names
- **COBOL reserved words**: Keywords like `MOVE`, `PERFORM`, `IF`
- **Literals**: Quoted strings and numeric constants

### Identifier Types
```python
PROGRAM_NAME      # PROGRAM-ID value
COPYBOOK_NAME     # COPY statement target
SECTION_NAME      # SECTION keyword context
PARAGRAPH_NAME    # Paragraph headers
DATA_NAME         # Variables (levels 01-49, 66, 77)
CONDITION_NAME    # 88-level condition names
FILE_NAME         # FD/SD file names
INDEX_NAME        # INDEXED BY names
EXTERNAL_NAME     # EXTERNAL marked items
```

## Naming Schemes

Five pluggable strategies (Strategy Pattern):
1. **NUMERIC** (default): `D00000001`, `SC00000001` (zero-padded)
2. **ANIMALS**: `FLUFFY-LLAMA-1`, `GRUMPY-PENGUIN-2`
3. **FOOD**: `SPICY-TACO-1`, `CRISPY-WAFFLE-2`
4. **FANTASY**: `SNEAKY-DRAGON-1`, `BRAVE-PHOENIX-2`
5. **CORPORATE**: `AGILE-SYNERGY-1` (satirical buzzwords)

Word-based schemes use MD5 hashing for determinism and require minimum 5-char target length.

## Code Patterns

### Configuration via Dataclass
All configuration uses `@dataclass` with sensible defaults:
```python
config = Config(
    input_dir=Path("original/"),
    output_dir=Path("anonymized/"),
    naming_scheme=NamingScheme.ANIMALS,
    anonymize_comments=True,
    preserve_external=True,
)
```

### Exception Hierarchy
```python
AnonymizerError          # Base exception
├── ParseError           # Recoverable parsing issues
├── MappingError         # Mapping collisions
├── ValidationError      # Output validation failures
│   ├── ColumnOverflowError
│   └── IdentifierLengthError
├── ConfigError          # Configuration problems
├── CopyNotFoundError    # Missing copybook
└── CircularDependencyError
```

### Global Mapping Table
The `MappingTable` ensures cross-file consistency - same identifier always maps to the same anonymized name across all files in a batch.

## Testing Conventions

- **Framework**: pytest 7.0+
- **Structure**: Unit tests per module + integration tests
- **Fixtures**: Extensive shared fixtures in `conftest.py`
- **Sample data**: Realistic COBOL files in tests for edge cases

### Running Tests
```bash
# All tests (coverage report included automatically)
pytest

# All tests with HTML coverage report
make test-cov

# Specific module
pytest tests/test_naming_schemes.py

# Stop on first failure
pytest -x

# Run all checks (format, lint, typecheck, test)
make all
```

## Code Style

- **Formatter**: Black (line-length: 100)
- **Linter**: Ruff (line-length: 100, rules: E, W, F, I, B, C4, UP)
- **Type checker**: mypy (Python 3.9 target)
- **Python version**: 3.9+

### Naming Conventions
- Modules: `snake_case` (`column_handler.py`)
- Classes: `PascalCase` (`COBOLLine`, `MappingTable`)
- Functions: `snake_case` (`parse_line()`)
- Constants: `UPPER_CASE` (`MAX_IDENTIFIER_LENGTH`)

## Key Implementation Details

### Determinism is Critical
Same input must always produce identical output:
- Use zero-padded counters for numeric scheme
- Use MD5 hashing for word-based schemes
- Support `--seed` for reproducibility

### Change Tags Preservation
Non-numeric content in columns 1-6 (like `REPLAT`) are change tags that must be preserved exactly.

### Multi-line Constructs
Handle VALUE clauses and other constructs that span multiple lines with continuation markers.

### COPY REPLACING
Support parameterized COPY statements with identifier substitution.

## Common Tasks

### Adding a New Naming Scheme
1. Add scheme to `NamingScheme` enum in `generators/naming_schemes.py`
2. Create a new strategy class extending `WordBasedNamingStrategy` or `BaseNamingStrategy`
3. Add word lists (adjectives + nouns) if word-based
4. Register in `_STRATEGY_REGISTRY`
5. Add tests in `tests/test_naming_schemes.py`

### Adding New Identifier Type
1. Add type to `IdentifierType` enum in `core/classifier.py`
2. Update classification logic in `Classifier`
3. Add prefix mapping in naming schemes
4. Add tests

### Debugging Anonymization
Use `--dry-run --verbose` to see what would be changed without writing files.
The mapping file (`--mapping-file`) shows all identifier mappings as JSON and CSV (both formats are generated automatically).

## Don'ts

- Don't modify PIC clause contents
- Don't anonymize EXTERNAL items (cross-program references break)
- Don't generate identifiers > 30 chars
- Don't generate code past column 72
- Don't create identifiers ending in hyphens
- Don't use COBOL reserved words as anonymized names
