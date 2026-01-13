# COBOL Code Anonymizer - Implementation Plan

## Overview

This document provides a step-by-step implementation plan for building the COBOL anonymization tool. The implementation is organized into phases, with each phase building upon the previous one.

---

## Phase 1: Project Foundation

### 1.1 Project Structure Setup

Create the basic project structure:

```bash
cobol-data-structure-py/
├── src/
│   └── cobol_anonymizer/
│       ├── __init__.py
│       ├── core/
│       │   └── __init__.py
│       ├── cobol/
│       │   └── __init__.py
│       ├── generators/
│       │   └── __init__.py
│       └── output/
│           └── __init__.py
├── tests/
│   └── __init__.py
├── docs/
├── original/              # (gitignored - customer source)
├── anonymized/            # Output directory
├── pyproject.toml
└── README.md
```

### 1.2 Dependencies

**Required packages:**
- `dataclasses` (stdlib)
- `pathlib` (stdlib)
- `re` (stdlib)
- `json` (stdlib)
- `argparse` (stdlib)
- `pytest` (dev dependency)
- `pytest-cov` (dev dependency)

**pyproject.toml:**
```toml
[project]
name = "cobol-anonymizer"
version = "0.1.0"
description = "Anonymize COBOL source code while preserving logic"
requires-python = ">=3.9"

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov>=4.0"]

[project.scripts]
cobol-anonymize = "cobol_anonymizer.cli:main"
```

### 1.3 Deliverables

- [ ] Project directory structure created
- [ ] `pyproject.toml` configured
- [ ] Virtual environment setup
- [ ] Git branch ready for development

---

## Phase 2: COBOL Column Handler

### 2.1 Column Parsing Module

**File:** `src/cobol_anonymizer/cobol/column_handler.py`

**Tasks:**
1. Implement `COBOLLine` dataclass with column areas
2. Implement `parse_line()` function for fixed-format parsing
3. Implement `reconstruct_line()` for output generation
4. Handle edge cases: short lines, long lines, empty lines

**Test Cases:**
```python
def test_parse_standard_line():
    """Parse a typical 80-column COBOL line"""

def test_parse_comment_line():
    """Parse line with * in column 7"""

def test_parse_short_line():
    """Handle lines shorter than 80 characters"""

def test_reconstruct_preserves_columns():
    """Round-trip parsing maintains exact format"""
```

### 2.2 Indicator Handling

**Tasks:**
1. Detect comment lines (`*` in column 7)
2. Detect continuation lines (`-` in column 7)
3. Detect debug lines (`D` in column 7)
4. Handle change tags in sequence area (e.g., `BENIQ`, `CDR`)

### 2.3 Deliverables

- [ ] `column_handler.py` implemented
- [ ] Unit tests passing
- [ ] Can parse all 47 files in `original/` without errors

---

## Phase 3: Reserved Words and Tokenizer

### 3.1 Reserved Words Module

**File:** `src/cobol_anonymizer/cobol/reserved_words.py`

**Tasks:**
1. Create comprehensive COBOL reserved word set (~400 words)
2. Include COBOL-85 and COBOL-2002 keywords
3. Include common IBM extensions
4. Implement case-insensitive lookup

**Source:** Use official COBOL standard documentation.

### 3.2 Basic Tokenizer

**File:** `src/cobol_anonymizer/core/tokenizer.py`

**Tasks:**
1. Implement token extraction from code area
2. Classify tokens: keywords, identifiers, literals, operators
3. Preserve whitespace information for reconstruction
4. Handle string literals (single and double quotes)

**Token Types:**
- `KEYWORD` - Reserved words
- `IDENTIFIER` - User-defined names
- `LEVEL_NUMBER` - 01, 05, 77, 88, etc.
- `LITERAL_STRING` - Quoted strings
- `LITERAL_NUMBER` - Numeric values
- `OPERATOR` - =, <, >, etc.
- `PUNCTUATION` - Period, comma, parentheses
- `WHITESPACE` - Spaces (preserved)

**Test Cases:**
```python
def test_tokenize_data_definition():
    """Tokenize: 05 WS-FIELD PIC X(10)."""

def test_tokenize_move_statement():
    """Tokenize: MOVE WS-A TO WS-B."""

def test_tokenize_string_literal():
    """Tokenize: MOVE 'HELLO' TO WS-MSG."""

def test_reserved_word_detection():
    """Keywords are classified correctly"""
```

### 3.3 Deliverables

- [ ] `reserved_words.py` with complete word list
- [ ] `tokenizer.py` with basic tokenization
- [ ] Unit tests for tokenization
- [ ] Can tokenize representative lines from codebase

---

## Phase 4: Identifier Classification

### 4.1 Classifier Module

**File:** `src/cobol_anonymizer/core/classifier.py`

**Tasks:**
1. Detect PROGRAM-ID declarations
2. Detect COPY statements
3. Detect SECTION/PARAGRAPH names
4. Detect data names (with level numbers)
5. Detect 88-level condition names
6. Detect FD/SD file names

**Context Tracking:**
```python
@dataclass
class FileContext:
    current_division: Optional[str]  # IDENTIFICATION, DATA, PROCEDURE
    current_section: Optional[str]   # WORKING-STORAGE, LINKAGE, etc.
    in_data_definition: bool
    current_level: int
    level_stack: List[int]
```

**Detection Patterns:**
| Pattern | Identifier Type |
|---------|-----------------|
| `PROGRAM-ID. name` | PROGRAM_NAME |
| `COPY name` | COPYBOOK_NAME |
| `name SECTION.` | SECTION_NAME |
| `name.` (in PROCEDURE) | PARAGRAPH_NAME |
| `nn name PIC` | DATA_NAME |
| `88 name VALUE` | CONDITION_NAME |
| `FD name` | FILE_NAME |

### 4.2 Test Cases

```python
def test_classify_program_id():
    """Detect program name from PROGRAM-ID"""

def test_classify_copy_statement():
    """Detect copybook reference from COPY"""

def test_classify_data_name():
    """Detect data name from level + name pattern"""

def test_classify_88_level():
    """Detect condition name from 88 level"""

def test_context_tracking():
    """Context updates as divisions change"""
```

### 4.3 Deliverables

- [ ] `classifier.py` implemented
- [ ] Context tracking working
- [ ] All identifier types detected
- [ ] Unit tests passing

---

## Phase 5: Name Generator and Mapper

### 5.1 Name Generator

**File:** `src/cobol_anonymizer/generators/name_generator.py`

**Tasks:**
1. Generate unique anonymized names by type
2. Preserve original name length when possible
3. Use type-specific prefixes (VAR, PARA, PROG, etc.)
4. Ensure no collision with reserved words
5. Support deterministic generation (with seed)

**Name Generation Rules:**
| Type | Prefix | Example |
|------|--------|---------|
| PROGRAM_NAME | PROG | PROG0001 |
| COPYBOOK_NAME | COPY | COPY0001 |
| SECTION_NAME | SECT | SECT0001 |
| PARAGRAPH_NAME | PARA | PARA0001 |
| DATA_NAME | VAR | VAR0001-- |
| CONDITION_NAME | COND | COND0001 |
| FILE_NAME | FILE | FILE0001 |

### 5.2 Mapping Table

**File:** `src/cobol_anonymizer/core/mapper.py`

**Tasks:**
1. Implement `MappingEntry` dataclass
2. Implement `MappingTable` with get_or_create logic
3. Case-insensitive lookup (COBOL is case-insensitive)
4. Persistence: save/load JSON mappings
5. Track occurrence counts and first-seen locations

### 5.3 Test Cases

```python
def test_name_generation_uniqueness():
    """Each call generates unique name"""

def test_length_preservation():
    """Generated name matches original length when possible"""

def test_mapping_consistency():
    """Same input always returns same output"""

def test_mapping_persistence():
    """Save and load preserves all mappings"""

def test_no_reserved_collision():
    """Generated names never match reserved words"""
```

### 5.4 Deliverables

- [ ] `name_generator.py` implemented
- [ ] `mapper.py` implemented
- [ ] JSON persistence working
- [ ] Unit tests passing

---

## Phase 6: COPY Statement Handling

### 6.1 COPY Resolver

**File:** `src/cobol_anonymizer/cobol/copy_resolver.py`

**Tasks:**
1. Parse COPY statements to extract copybook names
2. Handle COPY REPLACING syntax
3. Build dependency graph between files
4. Determine processing order (topological sort)
5. Rename copybook files to match anonymized names

**COPY Statement Patterns:**
```cobol
COPY copyname.
COPY copyname REPLACING ==pattern== BY ==replacement==.
COPY copyname OF library.
```

### 6.2 Dependency Graph

**Tasks:**
1. Scan all files for COPY statements
2. Build directed graph: file → copybooks it uses
3. Topological sort for processing order
4. Detect circular dependencies (error)

### 6.3 Test Cases

```python
def test_parse_simple_copy():
    """Extract copybook name from COPY statement"""

def test_parse_copy_replacing():
    """Handle COPY with REPLACING clause"""

def test_dependency_order():
    """Copybooks processed before files that use them"""

def test_circular_dependency_detection():
    """Detect and report circular COPY references"""
```

### 6.4 Deliverables

- [ ] `copy_resolver.py` implemented
- [ ] COPY parsing working
- [ ] Dependency graph construction working
- [ ] Unit tests passing

---

## Phase 7: Core Anonymizer

### 7.1 Main Anonymizer Module

**File:** `src/cobol_anonymizer/core/anonymizer.py`

**Tasks:**
1. Implement main `Anonymizer` class
2. Coordinate all phases (discovery, mapping, transform)
3. Handle file-by-file processing
4. Apply mappings to tokenized lines
5. Reconstruct anonymized lines

### 7.2 Line Transformation

**Tasks:**
1. Transform identifiers using mapping table
2. Preserve PIC clauses unchanged
3. Handle REDEFINES references correctly
4. Transform string literals (preserve length)
5. Transform comments (optional)

**Special Handling:**
- PIC clauses: Never modify
- REDEFINES: Map the referenced name
- VALUE clauses: Anonymize literals, preserve length
- Qualified names: Transform each component

### 7.3 Test Cases

```python
def test_transform_data_definition():
    """Data names are anonymized correctly"""

def test_pic_clause_preserved():
    """PIC clauses remain unchanged"""

def test_redefines_reference():
    """REDEFINES points to correct anonymized name"""

def test_value_literal_transformation():
    """VALUE literals anonymized with length preserved"""

def test_qualified_name_transformation():
    """Each component of qualified name transformed"""
```

### 7.4 Deliverables

- [ ] `anonymizer.py` implemented
- [ ] Line transformation working
- [ ] All special cases handled
- [ ] Unit tests passing

---

## Phase 8: Comment Handler

### 8.1 Comment Anonymization

**File:** `src/cobol_anonymizer/generators/comment_generator.py`

**Tasks:**
1. Detect comment lines (column 7 = `*`)
2. Replace Italian business terms with generic text
3. Remove personal names and dates
4. Preserve comment structure and indentation
5. Option to strip all comments

**Comment Transformation Strategy:**
- Remove employee names (e.g., "MASON", "LUPO")
- Remove system identifiers (e.g., "CRQ000002478171")
- Replace Italian terms with English equivalents
- Keep structural markers (dashes, asterisks)

### 8.2 Test Cases

```python
def test_comment_anonymization():
    """Comment text is replaced"""

def test_comment_structure_preserved():
    """Comment indentation and formatting kept"""

def test_personal_names_removed():
    """Names in comments are anonymized"""
```

### 8.3 Deliverables

- [ ] `comment_generator.py` implemented
- [ ] Comment transformation working
- [ ] Unit tests passing

---

## Phase 9: Output Writer and Validator

### 9.1 Output Writer

**File:** `src/cobol_anonymizer/output/writer.py`

**Tasks:**
1. Write anonymized lines with exact column alignment
2. Rename output files (programs and copybooks)
3. Preserve original file encoding
4. Handle line endings (platform-appropriate)

### 9.2 Validator

**Tasks:**
1. Validate output column format (max 80 columns)
2. Validate cross-file consistency
3. Validate COPY references exist
4. Report warnings for unusual patterns

### 9.3 Report Generator

**File:** `src/cobol_anonymizer/output/report.py`

**Tasks:**
1. Generate JSON mapping report
2. Include statistics (files, lines, identifiers)
3. Include transformation details per file
4. Optionally generate HTML report

### 9.4 Test Cases

```python
def test_output_column_format():
    """All output lines <= 80 columns"""

def test_copy_references_valid():
    """COPY statements reference existing files"""

def test_report_generation():
    """Report contains all mappings"""
```

### 9.5 Deliverables

- [ ] `writer.py` implemented
- [ ] `report.py` implemented
- [ ] Validation checks working
- [ ] Unit tests passing

---

## Phase 10: CLI and Configuration

### 10.1 Command-Line Interface

**File:** `src/cobol_anonymizer/cli.py`

**Tasks:**
1. Implement argument parsing with argparse
2. Support input/output directory options
3. Support configuration file loading
4. Implement verbose/quiet modes
5. Handle errors gracefully

**CLI Usage:**
```bash
cobol-anonymize --input original/ --output anonymized/
cobol-anonymize --input original/ --output anonymized/ --config config.json
cobol-anonymize --input original/ --output anonymized/ --no-comments
cobol-anonymize --input original/ --output anonymized/ --verbose
```

### 10.2 Configuration

**File:** `src/cobol_anonymizer/config.py`

**Tasks:**
1. Implement `Config` dataclass
2. Support JSON configuration file
3. Support command-line overrides
4. Validate configuration values

### 10.3 Main Entry Point

**File:** `src/cobol_anonymizer/main.py`

**Tasks:**
1. Orchestrate full anonymization pipeline
2. Handle progress reporting
3. Generate final summary

### 10.4 Deliverables

- [ ] `cli.py` implemented
- [ ] `config.py` implemented
- [ ] `main.py` implemented
- [ ] End-to-end tool working

---

## Phase 11: Integration Testing

### 11.1 Full Pipeline Tests

**Tasks:**
1. Test anonymization of complete `original/` folder
2. Verify all 47 files processed successfully
3. Verify cross-file consistency
4. Verify deterministic output

### 11.2 Edge Case Tests

**Test Files from Codebase:**

| File | Test Focus |
|------|------------|
| `EQTRHORI.cbl` | Full program with all divisions |
| `EDMCA000.cpy` | Complex REDEFINES structures |
| `EGECMS01.cob` | 88-level conditions, VALUE THRU |
| `ELSCQ130.cob` | Deep nesting, COMP-3 fields |
| `ITBCPA01.cpy` | COPY REPLACING pattern |

### 11.3 Regression Tests

**Tasks:**
1. Create golden output files for reference
2. Compare new runs against golden files
3. Detect unintended changes

### 11.4 Deliverables

- [ ] Integration test suite created
- [ ] All 47 files anonymize successfully
- [ ] No cross-file consistency errors
- [ ] Golden files established

---

## Phase 12: Documentation and Packaging

### 12.1 User Documentation

**Tasks:**
1. Write README.md with usage instructions
2. Document configuration options
3. Document output format
4. Include examples

### 12.2 Developer Documentation

**Tasks:**
1. Add docstrings to all public functions
2. Document architecture decisions
3. Create contribution guidelines

### 12.3 Packaging

**Tasks:**
1. Finalize pyproject.toml
2. Create distribution package
3. Test installation in clean environment

### 12.4 Deliverables

- [ ] README.md complete
- [ ] All modules documented
- [ ] Package installable via pip

---

## Implementation Schedule Summary

| Phase | Description | Dependencies |
|-------|-------------|--------------|
| 1 | Project Foundation | None |
| 2 | Column Handler | Phase 1 |
| 3 | Reserved Words & Tokenizer | Phase 2 |
| 4 | Identifier Classification | Phase 3 |
| 5 | Name Generator & Mapper | Phase 4 |
| 6 | COPY Statement Handling | Phase 5 |
| 7 | Core Anonymizer | Phase 6 |
| 8 | Comment Handler | Phase 7 |
| 9 | Output Writer & Validator | Phase 8 |
| 10 | CLI & Configuration | Phase 9 |
| 11 | Integration Testing | Phase 10 |
| 12 | Documentation & Packaging | Phase 11 |

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|------------|
| Complex COBOL syntax variations | Test against all 47 files early |
| Column alignment issues | Strict validation after each phase |
| Cross-file consistency | Global mapping table, process copybooks first |
| Performance with large files | Stream processing, lazy loading |

### Quality Assurance

- Unit tests for each module before moving to next phase
- Integration tests after each major phase
- Manual verification of sample output files
- Comparison with original files for logical equivalence

---

## Success Criteria

1. **Functional**: All 47 COBOL files anonymize without errors
2. **Consistent**: Same identifier maps to same name across all files
3. **Deterministic**: Multiple runs produce identical output
4. **Format-Preserving**: All output files maintain valid COBOL column format
5. **Traceable**: Complete mapping report generated
6. **Documented**: Clear usage instructions and examples
