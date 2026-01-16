# COBOL Anonymizer

A Python tool that automatically anonymizes COBOL source code while preserving exact logical equivalence and structure. Transform customer-specific COBOL code into generic, non-identifiable code suitable for public distribution, testing, or sharing.

## Features

- **Preserves Logic**: Anonymized code maintains identical behavior to the original
- **Column-Aware**: Respects COBOL's 80-column fixed format structure
- **Multiple Naming Schemes**: Choose from NUMERIC, ANIMALS, FOOD, FANTASY, or CORPORATE styles
- **Cross-File Consistency**: Same identifier always maps to the same anonymized name
- **Protected Elements**: Never modifies PIC clauses, EXTERNAL items, or reserved words
- **Copybook Support**: Handles COPY statements with dependency resolution

## Installation

### From Source

```bash
pip install -e .
```

### For Development

```bash
pip install -e ".[dev]"
```

Or using Make:

```bash
make install-dev
```

## Quick Start

### Command Line

```bash
# Basic anonymization
cobol-anonymize --input original-cobol-source/ --output anonymized/

# With verbose output
cobol-anonymize --input original-cobol-source/ --output anonymized/ --verbose

# Using a specific naming scheme
cobol-anonymize --input original-cobol-source/ --output anonymized/ --naming-scheme animals

# Dry run (preview without writing files)
cobol-anonymize --input original-cobol-source/ --output anonymized/ --dry-run
```

### Python API

```python
from pathlib import Path
from cobol_anonymizer import anonymize_directory
from cobol_anonymizer.generators.naming_schemes import NamingScheme

# Basic usage
result = anonymize_directory(
    input_dir=Path("original-cobol-source/"),
    output_dir=Path("anonymized/"),
)

# With naming scheme
result = anonymize_directory(
    input_dir=Path("original-cobol-source/"),
    output_dir=Path("anonymized/"),
    naming_scheme=NamingScheme.ANIMALS,
)

print(f"Processed {len(result.file_results)} files")
print(f"Mappings saved to {result.mapping_file}")
```

## Naming Schemes

| Scheme | Example | Description |
|--------|---------|-------------|
| `numeric` | `D00000001`, `SC00000001` | Traditional prefix + counter |
| `animals` | `FLUFFY-LLAMA-1` | Adjective + animal |
| `food` | `SPICY-TACO-1` | Adjective + food item |
| `fantasy` | `SNEAKY-DRAGON-1` | Adjective + creature |
| `corporate` | `AGILE-SYNERGY-1` | Business buzzwords (default) |

## What Gets Anonymized

- Program names (PROGRAM-ID)
- Copybook names (COPY statements)
- Section and paragraph names
- Data item names (levels 01-49, 66, 77, 88)
- File names (FD/SD declarations)
- Index names (INDEXED BY)
- String literals (DISPLAY, VALUE clauses, etc.) - length preserved
- CALL statement program references
- Output file names

## What Is Preserved

- PIC clauses (data format descriptors)
- USAGE clauses (COMP, COMP-3, etc.)
- EXTERNAL items (cross-program references)
- COBOL reserved words
- Numeric literals
- Column structure (sequence, indicator, areas)
- Sequence numbers and change tags in columns 1-6 (only when using `--preserve-sequence-area`)
- String literals (when using `--protect-literals`)

## Development

### Setup

```bash
git clone https://github.com/your-org/cobol-data-structure-py.git
cd cobol-data-structure-py
make install-dev
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_anonymizer.py -v
```

### Code Quality

```bash
# Run all checks (format, lint, typecheck, test)
make all

# Individual commands
make format      # Format with black
make lint        # Lint with ruff
make typecheck   # Type check with mypy
```

## Project Structure

```
cobol-data-structure-py/
├── src/cobol_anonymizer/
│   ├── core/           # Core: anonymizer, classifier, mapper, tokenizer
│   ├── cobol/          # COBOL: column_handler, reserved_words, pic_parser
│   ├── generators/     # Name generation: naming_schemes
│   └── output/         # Output: writer, validator, report
├── tests/              # Comprehensive pytest suite
├── docs/               # Design documentation
├── pyproject.toml      # Project configuration
├── Makefile            # Development commands
└── README.md           # This file
```

## Documentation

- [Design Document](docs/01-DESIGN.md) - Architecture and design decisions
- [Implementation Plan](docs/01-IMPLEMENTATION_PLAN.md) - Development phases
- [Funny Naming Schemes Plan](docs/04-FUNNY_NAMING_SCHEMES_PLAN.md) - Alternative naming scheme implementation
- [CSV Export Plan](docs/08-CSV_EXPORT_PLAN.md) - CSV mapping export functionality
- [CLI/Main Refactoring](docs/10-CLI_MAIN_REFACTORING.md) - CLI and main module refactoring
- [Refactoring Opportunities](docs/11-REFACTORING_OPPORTUNITIES.md) - Code simplification opportunities
- [Project Organization Gaps](docs/13-PROJECT_ORGANIZATION_GAPS.md) - Project structure improvements
- [Test Coverage Analysis](docs/14-TEST_COVERAGE_ANALYSIS.md) - Test coverage configuration
- [CLAUDE.md Update Recommendations](docs/14-CLAUDE_MD_UPDATE_RECOMMENDATIONS.md) - AI guidance updates
- [File Name Anonymization Strategy](docs/16-FILE_NAME_ANONYMIZATION_STRATEGY.md) - Strategy for anonymizing COBOL file names
- [File Name Anonymization Plan](docs/16-FILE_NAME_ANONYMIZATION_PLAN.md) - Implementation plan for file name anonymization
- [Anonymization Gaps Analysis](docs/16-ANONYMIZATION_GAPS_ANALYSIS.md) - Analysis of gaps in anonymization logic
- [CLAUDE.md](.claude/CLAUDE.md) - AI assistant guidance

## CLI Options

```
Usage: cobol-anonymize [OPTIONS]

Options:
  -i, --input DIR          Input directory with COBOL files (required)
  -o, --output DIR         Output directory for anonymized files (required)
  --naming-scheme SCHEME   Naming scheme: numeric, animals, food, fantasy, corporate
  --mapping-file FILE      Path to save mapping table (JSON)
  --load-mappings FILE     Load existing mappings from file
  --copybook-path DIR      Additional copybook search path (repeatable)
  --no-comments            Don't anonymize comments
  --strip-comments         Remove comment content entirely
  --protect-literals       Keep string literals unchanged (default: anonymize them)
  --preserve-external      Keep EXTERNAL item names unchanged
  --preserve-sequence-area Keep columns 1-6 unchanged (default: clean with spaces)
  --dry-run                Process without writing files
  --validate-only          Only validate files, don't transform
  -v, --verbose            Enable verbose output
  -q, --quiet              Suppress normal output
  --seed N                 Random seed for deterministic output
  --encoding ENC           File encoding (default: latin-1)
  --version                Show version
  --help                   Show this help message
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## License

MIT License - see [LICENSE](LICENSE) for details.
