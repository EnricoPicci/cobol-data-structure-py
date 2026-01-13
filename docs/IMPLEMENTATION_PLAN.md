# COBOL Code Anonymizer - Implementation Plan

## Overview

This document provides a step-by-step implementation plan for building the COBOL anonymization tool. The implementation is organized into phases, with each phase building upon the previous one.

**Key Design Decisions (from review):**
- Use zero-padded counters for name generation (NOT hyphen padding)
- Enforce 30-character COBOL identifier limit
- Preserve EXTERNAL items without anonymization
- Detect and handle change tags in sequence area
- Validate column 72 overflow

---

## Phase 1: Project Foundation

### 1.1 Project Structure Setup

Create the basic project structure:

```bash
cobol-data-structure-py/
├── src/
│   └── cobol_anonymizer/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── main.py
│       ├── exceptions.py          # NEW: All exception classes
│       ├── logging_config.py      # NEW: Logging configuration
│       ├── core/
│       │   ├── __init__.py
│       │   ├── tokenizer.py
│       │   ├── classifier.py
│       │   ├── anonymizer.py
│       │   ├── mapper.py
│       │   └── utils.py           # NEW: Utility functions
│       ├── cobol/
│       │   ├── __init__.py
│       │   ├── column_handler.py
│       │   ├── reserved_words.py
│       │   ├── pic_parser.py      # NEW: PIC clause detection
│       │   ├── copy_resolver.py
│       │   └── level_handler.py   # NEW: Level hierarchy tracking
│       ├── generators/
│       │   ├── __init__.py
│       │   ├── name_generator.py
│       │   └── comment_generator.py
│       └── output/
│           ├── __init__.py
│           ├── writer.py
│           ├── validator.py       # NEW: Separate validator module
│           └── report.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── test_column_handler.py
│   ├── test_tokenizer.py
│   └── ...
├── docs/
├── original/                     # (gitignored - customer source)
├── anonymized/                   # Output directory
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
- `logging` (stdlib)
- `pytest` (dev dependency)
- `pytest-cov` (dev dependency)

**pyproject.toml:**
```toml
[project]
name = "cobol-anonymizer"
version = "0.1.0"
description = "Anonymize COBOL source code while preserving logic"
requires-python = ">=3.9,<4.0"

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov>=4.0", "black", "mypy"]

[project.scripts]
cobol-anonymize = "cobol_anonymizer.cli:main"
```

### 1.3 Error Handling Infrastructure (NEW)

**File:** `src/cobol_anonymizer/exceptions.py`

**Tasks:**
1. Implement base `AnonymizerError` exception
2. Implement `ParseError` with file/line context
3. Implement `MappingError` for mapping issues
4. Implement `ValidationError` base class
5. Implement `ColumnOverflowError` for column 72 violations
6. Implement `IdentifierLengthError` for >30 char names
7. Implement `CopyNotFoundError` for missing copybooks
8. Implement `CircularDependencyError` for COPY cycles
9. Implement `ConfigError` for configuration issues

**Test Cases:**
```python
def test_parse_error_includes_location():
    """ParseError message includes file:line"""

def test_column_overflow_error():
    """ColumnOverflowError raised when code exceeds column 72"""
```

### 1.4 Logging Configuration (NEW)

**File:** `src/cobol_anonymizer/logging_config.py`

**Tasks:**
1. Configure structured logging with levels (DEBUG, INFO, WARNING, ERROR)
2. Support console and file output
3. Include timestamp, module, and message in format
4. Allow log level configuration via Config

### 1.5 Utilities Module (NEW)

**File:** `src/cobol_anonymizer/core/utils.py`

**Tasks:**
1. Implement column position calculation helpers
2. Implement string padding/truncation with COBOL rules
3. Implement COBOL identifier validation (30 chars, no trailing hyphen)
4. Implement case-insensitive comparison helpers

**Test Cases:**
```python
def test_validate_identifier_max_length():
    """Reject identifiers over 30 characters"""

def test_validate_identifier_no_trailing_hyphen():
    """Reject identifiers ending with hyphen"""

def test_validate_identifier_no_leading_hyphen():
    """Reject identifiers starting with hyphen"""

def test_validate_identifier_must_start_with_letter():
    """Reject identifiers starting with digit"""
```

### 1.6 Deliverables

- [ ] Project directory structure created
- [ ] `pyproject.toml` configured
- [ ] `exceptions.py` with all exception classes
- [ ] `logging_config.py` with logging setup
- [ ] `utils.py` with validation helpers
- [ ] Virtual environment setup
- [ ] Git branch ready for development
- [ ] Unit tests for exceptions and utilities passing

---

## Phase 2: COBOL Column Handler

### 2.1 Column Parsing Module

**File:** `src/cobol_anonymizer/cobol/column_handler.py`

**Tasks:**
1. Implement `COBOLLine` dataclass with ALL required fields:
   - `raw`, `line_number`, `sequence`, `indicator`
   - `area_a`, `area_b`, `identification`
   - `original_length` (NEW: preserve original line length)
   - `line_ending` (NEW: preserve \n, \r\n, or \r)
   - `has_change_tag` (NEW: detect BENIQ, CDR, etc.)
2. Implement `parse_line()` function for fixed-format parsing
3. Implement `reconstruct_line()` for output generation
4. Handle edge cases: short lines, long lines, empty lines

**Test Cases (including negative cases):**
```python
def test_parse_standard_line():
    """Parse a typical 80-column COBOL line"""

def test_parse_comment_line():
    """Parse line with * in column 7"""

def test_parse_short_line():
    """Handle lines shorter than 80 characters"""

def test_reconstruct_preserves_columns():
    """Round-trip parsing maintains exact format"""

def test_parse_change_tag_beniq():
    """Detect BENIQ change tag in sequence area"""

def test_parse_change_tag_cdr():
    """Detect CDR change tag in sequence area"""

def test_preserve_original_length():
    """original_length field matches input line length"""

def test_preserve_line_ending_unix():
    """Preserve \\n line ending"""

def test_preserve_line_ending_windows():
    """Preserve \\r\\n line ending"""

# Negative test cases
def test_parse_malformed_line():
    """Handle lines with unexpected format gracefully"""

def test_parse_empty_line():
    """Handle empty lines without error"""

def test_parse_line_with_tabs():
    """Handle lines containing tab characters"""
```

### 2.2 Indicator Handling

**Tasks:**
1. Detect comment lines (`*` in column 7)
2. Detect continuation lines (`-` in column 7)
3. Detect debug lines (`D` in column 7)
4. Handle change tags in sequence area (e.g., `BENIQ`, `CDR`, `DM2724`, `REPLAT`)

### 2.3 Column Overflow Validation (NEW)

**Tasks:**
1. Implement `validate_code_area()` function
2. Check that area_a + area_b <= 65 characters (columns 8-72)
3. Raise `ColumnOverflowError` with exact location on violation

**Test Cases:**
```python
def test_validate_code_area_within_limit():
    """Accept code area within 65 characters"""

def test_validate_code_area_overflow():
    """Raise ColumnOverflowError when exceeding column 72"""
```

### 2.4 Deliverables

- [ ] `column_handler.py` implemented with all fields
- [ ] Change tag detection working
- [ ] Line ending preservation working
- [ ] Column overflow validation implemented
- [ ] Unit tests passing (including negative cases)
- [ ] Can parse all 47 files in `original/` without errors

---

## Phase 3: Reserved Words, PIC Parser, and Tokenizer

**IMPORTANT:** This phase has internal dependencies. Complete in order: 3.1 → 3.2 → 3.3

### 3.1 Reserved Words Module (FIRST)

**File:** `src/cobol_anonymizer/cobol/reserved_words.py`

**Tasks:**
1. Create comprehensive COBOL reserved word set (~400 words)
2. Include COBOL-85 and COBOL-2002 keywords
3. Include common IBM extensions
4. Implement case-insensitive lookup
5. Include clause keywords: REDEFINES, VALUE, OCCURS, INDEXED, EXTERNAL, JUSTIFIED

**Source:** Use official COBOL standard documentation.

**Test Cases:**
```python
def test_reserved_word_move():
    """MOVE is a reserved word"""

def test_reserved_word_case_insensitive():
    """move, MOVE, Move all detected as reserved"""

def test_not_reserved_word():
    """WS-FIELD is not a reserved word"""

def test_external_is_reserved():
    """EXTERNAL is a reserved word"""

def test_justified_is_reserved():
    """JUSTIFIED and JUST are reserved words"""
```

### 3.2 PIC Clause Parser (NEW - SECOND)

**File:** `src/cobol_anonymizer/cobol/pic_parser.py`

**Tasks:**
1. Implement `PICParser` class
2. Detect all PIC clause patterns:
   - `PIC X(n)`, `PIC 9(n)`, `PIC S9(n)`
   - `PIC S9(n)V9(m)` (decimal)
   - `PIC Z(n)9`, `PIC -(n)9` (edited)
3. Detect USAGE clauses: COMP, COMP-3, DISPLAY, BINARY
4. Return position ranges to protect from modification
5. Implement `is_in_pic_clause()` check

**Test Cases:**
```python
def test_detect_pic_x():
    """Detect PIC X(10) pattern"""

def test_detect_pic_9():
    """Detect PIC 9(5) pattern"""

def test_detect_pic_signed_decimal():
    """Detect PIC S9(8)V9(2) pattern"""

def test_detect_pic_comp3():
    """Detect PIC S9(12)V9(03) COMP-3 pattern"""

def test_pic_range_protection():
    """Position within PIC clause is protected"""

def test_pic_followed_by_identifier():
    """Identifier after PIC clause is not protected"""
```

### 3.3 Basic Tokenizer (THIRD - depends on 3.1 and 3.2)

**File:** `src/cobol_anonymizer/core/tokenizer.py`

**Tasks:**
1. Implement token extraction from code area
2. Use reserved words module for keyword detection
3. Use PIC parser to protect PIC clauses
4. Classify tokens: keywords, identifiers, literals, operators
5. Preserve whitespace information for reconstruction
6. Handle string literals (single and double quotes)
7. Track token position (area A vs area B)

**Token Types:**
- `KEYWORD` - Reserved words
- `IDENTIFIER` - User-defined names
- `LEVEL_NUMBER` - 01, 02, ..., 49, 66, 77, 88
- `PIC_CLAUSE` - Entire PIC clause (protected)
- `LITERAL_STRING` - Quoted strings
- `LITERAL_NUMBER` - Numeric values
- `OPERATOR` - =, <, >, etc.
- `PUNCTUATION` - Period, comma, parentheses
- `WHITESPACE` - Spaces (preserved)
- `CLAUSE_KEYWORD` - REDEFINES, VALUE, OCCURS, etc.

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

def test_pic_clause_single_token():
    """PIC X(10) COMP-3 is a single protected token"""

def test_tokenize_with_whitespace():
    """Whitespace between tokens is preserved"""

def test_tokenize_qualified_name():
    """WS-FIELD OF WS-GROUP tokenized as three tokens"""
```

### 3.4 Deliverables

- [ ] `reserved_words.py` with complete word list
- [ ] `pic_parser.py` with PIC clause detection
- [ ] `tokenizer.py` with PIC-aware tokenization
- [ ] Unit tests for all modules
- [ ] Can tokenize representative lines from codebase

---

## Phase 4: Identifier Classification

### 4.1 Classifier Module

**File:** `src/cobol_anonymizer/core/classifier.py`

**Tasks:**
1. Detect PROGRAM-ID declarations
2. Detect COPY statements (including REPLACING)
3. Detect SECTION/PARAGRAPH names
4. Detect data names (with level numbers 01-49, 66, 77)
5. Detect 88-level condition names
6. Detect FD/SD file names
7. Detect INDEXED BY names
8. Detect EXTERNAL declarations (mark as do-not-anonymize)

**Context Tracking:**
```python
@dataclass
class FileContext:
    filename: str
    current_division: Optional[str]  # IDENTIFICATION, ENVIRONMENT, DATA, PROCEDURE
    current_section: Optional[str]   # WORKING-STORAGE, LINKAGE, FILE, etc.
    in_data_definition: bool
    current_level: int
    level_stack: List[int]
    in_configuration_section: bool   # NEW: Track CONFIGURATION SECTION
    is_external_block: bool          # NEW: Track EXTERNAL declarations
```

**Classification Algorithm (Pseudo-code):**
```
IF line matches "PROGRAM-ID. name" THEN PROGRAM_NAME
ELSE IF line matches "COPY name" THEN COPYBOOK_NAME
ELSE IF line matches "name SECTION." THEN SECTION_NAME
ELSE IF context=PROCEDURE_DIVISION AND line matches "name." THEN PARAGRAPH_NAME
ELSE IF line matches "level-number name" AND has PIC/VALUE/REDEFINES THEN DATA_NAME
ELSE IF line matches "88 name" THEN CONDITION_NAME
ELSE IF line matches "FD name" OR "SD name" THEN FILE_NAME
ELSE IF line contains "INDEXED BY name" THEN INDEX_NAME
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
| `INDEXED BY name` | INDEX_NAME |
| `01 name EXTERNAL` | EXTERNAL_NAME (do not anonymize) |

### 4.2 EXTERNAL Detection (NEW)

**Tasks:**
1. Detect `EXTERNAL` keyword in data definitions
2. Mark the data item and all its children as EXTERNAL
3. Store in mapper's `external_names` set
4. Return original name (not anonymized) when encountered

**Test Cases:**
```python
def test_detect_external_declaration():
    """01 MSMFS-GRP EXTERNAL detected as EXTERNAL"""

def test_external_children_preserved():
    """Children of EXTERNAL item also preserved"""
```

### 4.3 Test Cases

```python
def test_classify_program_id():
    """Detect program name from PROGRAM-ID"""

def test_classify_copy_statement():
    """Detect copybook reference from COPY"""

def test_classify_copy_with_replacing():
    """Detect copybook and REPLACING patterns from COPY"""

def test_classify_data_name():
    """Detect data name from level + name pattern"""

def test_classify_88_level():
    """Detect condition name from 88 level"""

def test_context_tracking():
    """Context updates as divisions change"""

def test_classify_indexed_by():
    """Detect index name from INDEXED BY clause"""

def test_classify_all_level_numbers():
    """Support levels 01-15, 66, 77, 88"""

# Negative test cases
def test_filler_not_classified():
    """FILLER is not classified as identifier"""

def test_reserved_word_not_classified():
    """Reserved words are not classified as identifiers"""
```

### 4.4 Deliverables

- [ ] `classifier.py` implemented
- [ ] Context tracking working
- [ ] All identifier types detected (including EXTERNAL, INDEXED BY)
- [ ] Support for all level numbers (01-49, 66, 77, 88)
- [ ] Unit tests passing

---

## Phase 5: Name Generator and Mapper

### 5.1 Name Generator

**File:** `src/cobol_anonymizer/generators/name_generator.py`

**Tasks:**
1. Generate unique anonymized names by type
2. Use ZERO-PADDED COUNTERS (NOT hyphen padding)
3. Use SHORT type-specific prefixes: PG, CP, SC, PA, D, C, FL, IX
4. Ensure no collision with reserved words
5. Enforce 30-character maximum length
6. Validate no trailing/leading hyphens
7. Support deterministic generation (with seed)

**Name Generation Algorithm:**
```python
def generate_name(original: str, id_type: IdentifierType, counter: int) -> str:
    prefix = PREFIXES[id_type]  # e.g., 'D' for DATA_NAME
    target_len = min(len(original), 30)
    available_digits = target_len - len(prefix)

    if available_digits < 1:
        return f"{prefix}{counter}"

    # Zero-padded counter, NO hyphens
    format_str = f"{prefix}{{:0{available_digits}d}}"
    return format_str.format(counter)
```

**Name Generation Rules (UPDATED):**
| Type | Prefix | Example (8 chars) | Example (30 chars) |
|------|--------|-------------------|---------------------|
| PROGRAM_NAME | PG | PG000001 | PG0000000000000000000000000001 |
| COPYBOOK_NAME | CP | CP000001 | CP0000000000000000000000000001 |
| SECTION_NAME | SC | SC000001 | SC0000000000000000000000000001 |
| PARAGRAPH_NAME | PA | PA000001 | PA0000000000000000000000000001 |
| DATA_NAME | D | D0000001 | D00000000000000000000000000001 |
| CONDITION_NAME | C | C0000001 | C00000000000000000000000000001 |
| FILE_NAME | FL | FL000001 | FL0000000000000000000000000001 |
| INDEX_NAME | IX | IX000001 | IX0000000000000000000000000001 |

### 5.2 Mapping Table

**File:** `src/cobol_anonymizer/core/mapper.py`

**Tasks:**
1. Implement `MappingEntry` dataclass with `is_external` flag
2. Implement `MappingTable` with get_or_create logic
3. Track `external_names` set for EXTERNAL items
4. Case-insensitive lookup (COBOL is case-insensitive)
5. Validate generated names before storing
6. Persistence: save/load JSON mappings (including external_names)
7. Track occurrence counts and first-seen locations

### 5.3 Test Cases

```python
def test_name_generation_uniqueness():
    """Each call generates unique name"""

def test_length_preservation():
    """Generated name matches original length (up to 30)"""

def test_no_trailing_hyphens():
    """Generated names never end with hyphen"""

def test_no_leading_hyphens():
    """Generated names never start with hyphen"""

def test_max_30_characters():
    """Generated names never exceed 30 characters"""

def test_mapping_consistency():
    """Same input always returns same output"""

def test_mapping_persistence():
    """Save and load preserves all mappings"""

def test_no_reserved_collision():
    """Generated names never match reserved words"""

def test_external_not_anonymized():
    """EXTERNAL items return original name"""

def test_case_insensitive_lookup():
    """WS-FIELD and ws-field map to same anonymized name"""

# Negative test cases
def test_reject_invalid_identifier():
    """Raise error for invalid generated identifier"""
```

### 5.4 Deliverables

- [ ] `name_generator.py` with zero-padded counters
- [ ] `mapper.py` with EXTERNAL support
- [ ] Identifier validation (30 chars, no trailing hyphens)
- [ ] JSON persistence working (including external_names)
- [ ] Unit tests passing

---

## Phase 6: COPY Statement Handling

### 6.1 COPY Resolver

**File:** `src/cobol_anonymizer/cobol/copy_resolver.py`

**Tasks:**
1. Parse COPY statements with FULL regex:
   ```python
   COPY_REGEX = re.compile(
       r'COPY\s+(\w+)'                    # Copybook name
       r'(?:\s+OF\s+(\w+))?'              # Optional library
       r'(?:\s+REPLACING\s+(.+?))?'       # Optional REPLACING
       r'\s*\.',                           # Terminating period
       re.IGNORECASE | re.DOTALL
   )
   ```
2. Parse REPLACING clause patterns:
   - `==pattern== BY ==replacement==`
   - `identifier BY identifier`
3. Build dependency graph between files
4. Implement topological sort for processing order
5. Detect circular dependencies (raise `CircularDependencyError`)
6. Validate copybooks exist (raise `CopyNotFoundError` if missing)
7. Rename copybook files to match anonymized names

**COPY Statement Patterns:**
```cobol
COPY copyname.
COPY copyname OF library.
COPY copyname REPLACING ==pattern== BY ==replacement==.
COPY copyname REPLACING pattern-1 BY replacement-1
                        pattern-2 BY replacement-2.
```

### 6.2 COPY REPLACING Implementation (NEW - Detailed)

**Tasks:**
1. Implement `CopyStatement` dataclass:
   ```python
   @dataclass
   class CopyStatement:
       copybook_name: str
       library: Optional[str]
       replacements: List[Tuple[str, str]]  # (pattern, replacement) pairs
   ```
2. Implement `parse_replacing_clause()` to extract all patterns
3. Anonymize copybook name
4. Anonymize patterns that look like identifier prefixes
5. Handle cases where same copybook is used with different REPLACING

**Test Cases:**
```python
def test_parse_copy_with_pseudo_text():
    """Parse COPY name REPLACING ==:TAG:== BY ==WS-==."""

def test_parse_copy_with_multiple_replacing():
    """Parse COPY with multiple REPLACING pairs"""

def test_anonymize_replacing_pattern():
    """Anonymize identifier patterns in REPLACING"""
```

### 6.3 Dependency Graph

**Tasks:**
1. Scan all files for COPY statements
2. Build directed graph: file → copybooks it uses
3. Handle nested COPY (copybook that COPYs another)
4. Implement topological sort for processing order
5. Detect and report circular dependencies

**Test Cases:**
```python
def test_parse_simple_copy():
    """Extract copybook name from COPY statement"""

def test_parse_copy_replacing():
    """Handle COPY with REPLACING clause"""

def test_dependency_order():
    """Copybooks processed before files that use them"""

def test_circular_dependency_detection():
    """Detect and report circular COPY references"""

def test_nested_copy_dependency():
    """Handle copybook that COPYs another copybook"""

# Negative test cases
def test_missing_copybook_error():
    """Raise CopyNotFoundError for missing copybook"""
```

### 6.4 Deliverables

- [ ] `copy_resolver.py` with full REPLACING support
- [ ] `CopyStatement` dataclass implemented
- [ ] Dependency graph construction working
- [ ] Circular dependency detection working
- [ ] Missing copybook detection working
- [ ] Unit tests passing

---

## Phase 7: Core Anonymizer

### 7.1 Main Anonymizer Module

**File:** `src/cobol_anonymizer/core/anonymizer.py`

**Tasks:**
1. Implement main `Anonymizer` class
2. Coordinate all phases (discovery, mapping, transform)
3. Handle file-by-file processing in dependency order
4. Apply mappings to tokenized lines
5. Reconstruct anonymized lines
6. Validate column boundaries after transformation

### 7.2 Line Transformation

**Tasks:**
1. Transform identifiers using mapping table
2. Preserve PIC clauses unchanged (use PIC parser)
3. Handle REDEFINES references correctly (including nested)
4. Handle qualified names (transform each component)
5. Transform string literals (preserve length)
6. Transform comments (optional)
7. Preserve EXTERNAL items unchanged
8. Validate output doesn't overflow column 72

**Special Handling:**
- PIC clauses: Never modify (protected by PIC parser)
- REDEFINES: Map the referenced name using RedefinesTracker
- VALUE clauses: Anonymize literals, preserve length
- Qualified names: Transform each component of `X OF Y`
- EXTERNAL: Return original name unchanged
- Column 72: Validate after transformation

### 7.3 REDEFINES Tracker (NEW)

**Tasks:**
1. Implement `RedefinesTracker` class
2. Track REDEFINES relationships at all nesting levels
3. Map REDEFINES target to anonymized name
4. Handle FILLER REDEFINES (keep FILLER)

**Test Cases:**
```python
def test_nested_redefines_three_levels():
    """Handle 3-level nested REDEFINES correctly"""

def test_filler_redefines_preserved():
    """FILLER REDEFINES keeps FILLER"""
```

### 7.4 Test Cases

```python
def test_transform_data_definition():
    """Data names are anonymized correctly"""

def test_pic_clause_preserved():
    """PIC clauses remain unchanged"""

def test_redefines_reference():
    """REDEFINES points to correct anonymized name"""

def test_nested_redefines():
    """Multi-level REDEFINES handled correctly"""

def test_value_literal_transformation():
    """VALUE literals anonymized with length preserved"""

def test_qualified_name_transformation():
    """Each component of qualified name transformed"""

def test_external_preserved():
    """EXTERNAL items are never anonymized"""

def test_column_overflow_detection():
    """Raise error if transformation overflows column 72"""

# Negative test cases
def test_transform_invalid_line():
    """Handle malformed lines gracefully"""
```

### 7.5 Deliverables

- [ ] `anonymizer.py` implemented
- [ ] `RedefinesTracker` implemented
- [ ] Line transformation working
- [ ] Column overflow validation
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
4. Remove system identifiers (CRQ numbers, INC numbers)
5. Preserve comment structure and indentation
6. Option to strip all comments

**Comment Transformation Strategy:**
- Remove employee names (e.g., "MASON", "LUPO")
- Remove system identifiers (e.g., "CRQ000002478171")
- Replace Italian terms with English equivalents
- Keep structural markers (dashes, asterisks)
- Optionally anonymize identifiers mentioned in comments

### 8.2 Test Cases

```python
def test_comment_anonymization():
    """Comment text is replaced"""

def test_comment_structure_preserved():
    """Comment indentation and formatting kept"""

def test_personal_names_removed():
    """Names in comments are anonymized"""

def test_crq_numbers_removed():
    """CRQ/INC identifiers are removed"""
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
4. Preserve line endings (platform-appropriate)
5. Validate column boundaries before writing

### 9.2 Validator (NEW - Separate Module)

**File:** `src/cobol_anonymizer/output/validator.py`

**Tasks:**
1. Validate output column format (max 80 columns)
2. Validate code area doesn't exceed column 72
3. Validate cross-file consistency
4. Validate COPY references exist
5. Validate REDEFINES targets exist
6. Validate identifier length (<= 30 chars)
7. Report warnings for unusual patterns

**Validation Checks:**
```python
def validate_column_format(files: List[Path]) -> List[ValidationError]:
    """Check all lines <= 80 columns"""

def validate_code_area(files: List[Path]) -> List[ColumnOverflowError]:
    """Check code area <= 65 chars (columns 8-72)"""

def validate_cross_file_consistency(mapper: MappingTable) -> List[MappingError]:
    """Same identifier maps to same name across files"""

def validate_copy_references(files: List[Path]) -> List[CopyNotFoundError]:
    """All COPY statements reference existing files"""

def validate_redefines_targets(files: List[Path]) -> List[MappingError]:
    """All REDEFINES targets exist and are mapped"""

def validate_identifier_lengths(mapper: MappingTable) -> List[IdentifierLengthError]:
    """All identifiers <= 30 characters"""
```

### 9.3 Report Generator

**File:** `src/cobol_anonymizer/output/report.py`

**Tasks:**
1. Generate JSON mapping report
2. Include statistics (files, lines, identifiers by type)
3. Include external names list
4. Include transformation details per file
5. Optionally generate HTML report

### 9.4 Test Cases

```python
def test_output_column_format():
    """All output lines <= 80 columns"""

def test_output_code_area_limit():
    """Code area never exceeds column 72"""

def test_copy_references_valid():
    """COPY statements reference existing files"""

def test_report_generation():
    """Report contains all mappings"""

def test_external_names_in_report():
    """Report includes external_names list"""
```

### 9.5 Deliverables

- [ ] `writer.py` implemented
- [ ] `validator.py` implemented with all checks
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
6. Add new options: `--validate-only`, `--dry-run`, `--preserve-external`

**CLI Usage:**
```bash
cobol-anonymize --input original/ --output anonymized/
cobol-anonymize --input original/ --output anonymized/ --config config.json
cobol-anonymize --input original/ --output anonymized/ --no-comments
cobol-anonymize --input original/ --output anonymized/ --verbose
cobol-anonymize --input original/ --output anonymized/ --validate-only
cobol-anonymize --input original/ --output anonymized/ --dry-run
cobol-anonymize --input original/ --output anonymized/ --preserve-external
```

### 10.2 Configuration

**File:** `src/cobol_anonymizer/config.py`

**Tasks:**
1. Implement `Config` dataclass with all options
2. Support JSON configuration file
3. Support command-line overrides
4. Validate configuration values
5. Add encoding option (default: utf-8)
6. Add preserve_external option (default: True)

**Configuration Schema:**
```python
@dataclass
class Config:
    input_dir: Path
    output_dir: Path
    extensions: List[str] = ['.cob', '.cbl', '.cpy']
    encoding: str = 'utf-8'
    anonymize_program_names: bool = True
    anonymize_copybook_names: bool = True
    # ... (see DESIGN.md for full list)
    preserve_external: bool = True
    validate_columns: bool = True
    validate_identifier_length: bool = True
    log_level: str = 'INFO'
```

### 10.3 Main Entry Point

**File:** `src/cobol_anonymizer/main.py`

**Tasks:**
1. Orchestrate full anonymization pipeline
2. Handle progress reporting
3. Generate final summary
4. Support dry-run mode

### 10.4 Deliverables

- [ ] `cli.py` implemented with all options
- [ ] `config.py` implemented with validation
- [ ] `main.py` implemented
- [ ] End-to-end tool working

---

## Phase 11: Integration Testing

### 11.1 Full Pipeline Tests

**Tasks:**
1. Test anonymization of complete `original/` folder
2. Verify all 47 files processed successfully
3. Verify cross-file consistency
4. Verify deterministic output (multiple runs identical)

### 11.2 Edge Case Tests

**Test Files from Codebase:**

| File | Test Focus |
|------|------------|
| `EQTRHORI.cbl` | Full program with all divisions, CONFIGURATION SECTION |
| `EDMCA000.cpy` | 3-level nested REDEFINES structures |
| `EGECMS01.cob` | Multi-line VALUE THRU, change tags (REPLAT) |
| `ELSCQ130.cob` | Deep nesting, COMP-3 fields, 88-levels |
| `ITBCPA01.cpy` | JUSTIFIED clause |
| `MSMFSDTA.cob` | EXTERNAL clause |

### 11.3 Logical Equivalence Verification (NEW)

**Tasks:**
1. Define verification strategy:
   - Structural: Same line count, same PIC clauses, same structure
   - Reference integrity: All COPY/REDEFINES targets valid
   - Determinism: Multiple runs produce identical output
2. Implement verification checks
3. Generate verification report

**Verification Checks:**
```python
def verify_structural_equivalence(original: Path, anonymized: Path) -> bool:
    """Same number of lines, same structure"""

def verify_pic_clauses_unchanged(original: Path, anonymized: Path) -> bool:
    """All PIC clauses identical"""

def verify_determinism(input_dir: Path, runs: int = 2) -> bool:
    """Multiple runs produce identical output"""
```

### 11.4 Performance Testing (NEW)

**Tasks:**
1. Benchmark against full 47-file set
2. Measure memory usage
3. Measure processing time per file
4. Identify any performance bottlenecks

**Benchmarks:**
```python
def test_performance_47_files():
    """Process all 47 files in reasonable time"""

def test_memory_usage():
    """Memory usage stays within bounds"""
```

### 11.5 Regression Tests

**Tasks:**
1. Create golden output files for reference
2. Define golden file creation procedure
3. Compare new runs against golden files (byte-for-byte)
4. Detect unintended changes

### 11.6 Deliverables

- [ ] Integration test suite created
- [ ] All 47 files anonymize successfully
- [ ] No cross-file consistency errors
- [ ] Logical equivalence verification passing
- [ ] Performance benchmarks established
- [ ] Golden files established

---

## Phase 12: Documentation and Packaging

### 12.1 User Documentation

**Tasks:**
1. Write README.md with usage instructions
2. Document configuration options
3. Document output format
4. Include examples
5. Document error messages and troubleshooting

### 12.2 Developer Documentation

**Tasks:**
1. Add docstrings to all public functions
2. Document architecture decisions
3. Create contribution guidelines
4. Document testing strategy

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

| Phase | Description | Dependencies | New Items |
|-------|-------------|--------------|-----------|
| 1 | Project Foundation | None | exceptions.py, logging, utils.py |
| 2 | Column Handler | Phase 1 | change tags, overflow validation |
| 3 | Reserved Words, PIC Parser, Tokenizer | Phase 2 | pic_parser.py (NEW) |
| 4 | Identifier Classification | Phase 3 | EXTERNAL detection |
| 5 | Name Generator & Mapper | Phase 4 | zero-padded counters, 30-char limit |
| 6 | COPY Statement Handling | Phase 5 | full REPLACING support |
| 7 | Core Anonymizer | Phase 6 | RedefinesTracker, overflow check |
| 8 | Comment Handler | Phase 7 | - |
| 9 | Output Writer & Validator | Phase 8 | validator.py (separate) |
| 10 | CLI & Configuration | Phase 9 | --validate-only, --dry-run |
| 11 | Integration Testing | Phase 10 | equivalence verification, performance |
| 12 | Documentation & Packaging | Phase 11 | - |

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|------------|
| Complex COBOL syntax variations | Test against all 47 files early |
| Column alignment issues | Strict validation after each phase |
| Cross-file consistency | Global mapping table, process copybooks first |
| Performance with large files | Stream processing, lazy loading |
| Invalid identifier generation | Validate 30-char limit, no trailing hyphens |
| Column 72 overflow | Validate after every transformation |
| EXTERNAL items broken | Detect and preserve automatically |
| Nested REDEFINES | Track at all levels with RedefinesTracker |

### Quality Assurance

- Unit tests for each module before moving to next phase
- Negative test cases for error handling
- Integration tests after each major phase
- Manual verification of sample output files
- Comparison with original files for logical equivalence
- Performance benchmarks

---

## Success Criteria

1. **Functional**: All 47 COBOL files anonymize without errors
2. **Consistent**: Same identifier maps to same name across all files
3. **Deterministic**: Multiple runs produce identical output
4. **Format-Preserving**: All output files maintain valid COBOL column format
5. **Syntactically Valid**: All generated identifiers are valid COBOL (≤30 chars, no trailing hyphens)
6. **EXTERNAL Preserved**: EXTERNAL items remain unchanged
7. **Traceable**: Complete mapping report generated
8. **Documented**: Clear usage instructions and examples
