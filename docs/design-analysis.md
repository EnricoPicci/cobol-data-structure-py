# COBOL Data Structure Parser - Design Analysis & Recommendations

## Executive Summary

**Recommended Approach:** Custom Line-by-Line Parser using regex patterns

This approach aligns with the project's emphasis on simplicity while effectively handling common COBOL DATA DIVISION patterns.

---

## Requirements Analysis

### Core Functionality

1. Read COBOL source files and parse DATA DIVISION structures
2. Build Python objects representing COBOL data hierarchies
3. Fill Python objects from raw byte/string data (e.g., from logs)
4. Support field access by name

### COBOL Patterns to Support

| Pattern | Description | Priority |
|---------|-------------|----------|
| Level numbers (01-49) | Define field hierarchy | Required |
| PIC X(n) | Alphanumeric fields | Required |
| PIC 9(n) | Numeric fields | Required |
| FILLER | Unnamed spacing fields | Required |
| OCCURS n TIMES | Array repetitions | Required |
| REDEFINES | Union-like overlays | Required |
| COMP/COMP-3 | Binary/packed decimal (placeholder only) | Required |

### Constraints

- Focus on common cases, not completeness
- Prefer simplicity over exhaustive coverage
- Handle edge cases gracefully (log warning, mark as "unknown")
- COMP values: placeholder text only (no conversion)

---

## Approach Evaluation

### Option 1: Formal Grammar Parser (Lark, PLY, pyparsing)

**How it works:** Define a formal grammar with tokens, production rules, and parse trees.

**Pros:**

- Robust handling of complex, nested structures
- Well-tested parsing algorithms (Earley, LALR)
- Good error reporting for syntax errors
- Academic rigor

**Cons:**

- **Scope mismatch:** Full parser libraries are designed for complete languages; we only need DATA DIVISION
- **COBOL peculiarities:** Column-based formatting (cols 1-6 sequence, col 7 indicator, cols 8-72 code) makes traditional tokenization awkward
- **Overhead:** Setting up grammar requires tokens, production rules, AST definitions - overkill for our scope
- **Learning curve:** Grammar syntax adds cognitive load
- **Debugging:** Grammar-based parsers produce cryptic errors

**Verdict:** Over-engineered for this use case.

### Option 2: Custom Line-by-Line Parser (Recommended)

**How it works:** Process COBOL source line-by-line using regex patterns to extract level numbers, names, PIC clauses, and modifiers.

**Pros:**

- **Proven approach:** Libraries like [python-cobol](https://github.com/royopa/python-cobol) successfully use this pattern
- **Simplicity:** Each line processed independently after handling continuations
- **Direct control:** Easy to add warnings for edge cases
- **Testability:** Each regex pattern tested in isolation
- **Debuggability:** Clear, actionable error messages
- **Pythonic:** Aligns with project's "clarity over cleverness" principle

**Cons:**

- May miss obscure edge cases (acceptable per requirements)
- Manual hierarchy tracking (straightforward with a stack)

**Verdict:** Best fit for requirements.

---

## Recommended Architecture

### Module Structure

```
src/cobol_data_structure/
    __init__.py           # Public API exports
    models.py             # Data classes (CobolField, CobolRecord, PicClause)
    patterns.py           # Regex patterns for COBOL syntax
    parser.py             # Main parser logic
    data_holder.py        # Runtime data container with fill_from_bytes()
    converters.py         # PIC-to-Python type conversion
    warnings_log.py       # Warning collection utility
```

### Data Flow

```
COBOL Source File
       |
       v
+------------------+
|   Parser         |  1. Read lines, handle continuations
|   (parser.py)    |  2. Extract tokens via regex
|                  |  3. Build hierarchy from levels
+------------------+
       |
       v
+------------------+
|   CobolRecord    |  Hierarchical structure of
|   (models.py)    |  CobolField objects
+------------------+
       |
       v
+------------------+
|   DataHolder     |  Runtime container
|   (data_holder.py)|  with fill_from_bytes()
+------------------+
       |
       v
    Python dict/object
    (field access by name)
```

### Core Classes

1. **CobolField** - Represents a single field definition
   - Properties: level, name, pic, occurs, redefines, children, offset

2. **CobolRecord** - Root container for 01-level record
   - Properties: name, fields (tree), total_length, warnings

3. **PicClause** - Parsed PIC clause information
   - Properties: raw, field_type, length, decimal_positions

4. **DataHolder** - Runtime container for extracted data
   - Methods: fill_from_bytes(), fill_from_string(), to_dict()
   - Access: attribute style (holder.name) or dict style (holder["NAME"])

### Key Algorithms

**Hierarchy Building (from level numbers):**

```
Stack-based approach:
- Level 01: start new record
- Higher level (03, 05): find parent by popping stack until top < current
- Add as child to parent, push to stack
```

**Offset Calculation:**

```
Recursive traversal:
- Track running offset from record start
- Each field's offset = current position
- Group fields: offset of first child
- REDEFINES: inherit target field's offset
```

---

## Edge Case Handling Strategy

| Edge Case | Handling |
|-----------|----------|
| Unknown PIC pattern | Log warning, set type to UNKNOWN, length to 0 |
| COMP/COMP-3 | Placeholder text: `"<COMP-3 value>"` |
| Missing period | Attempt parse, warn if ambiguous |
| Level 66/77/88 | Skip with warning (special purpose levels) |
| INDEXED BY | Ignore (index variables, not data) |
| VALUE clause | Ignore (initial values, not structure) |
| OCCURS DEPENDING ON | Use static count, log warning |
| Target not found for REDEFINES | Log warning, skip resolution |

---

## Public API Design

```python
from cobol_data_structure import parse_copybook, parse_string, DataHolder

# Parse from file
record = parse_copybook(Path("customer.cpy"))

# Parse from string
record = parse_string("""
01 LAST-DATA.
    03 NAME PIC X(10).
    03 TYPE.
        05 CODE PIC 9(5) COMP-3.
        05 DESC PIC X(10).
""")

# Fill from raw data
holder = DataHolder(record)
holder.fill_from_string("John Doe  12345Description")

# Access fields
print(holder.name)           # "John Doe"
print(holder["DESC"])        # "Description"
print(holder.code)           # "<COMP-3 value>"
print(holder.to_dict())      # All fields as dict
```

---

## Implementation Phases

### Phase 1: Core Parsing

- `models.py` - CobolField, CobolRecord, PicClause dataclasses
- `patterns.py` - Regex patterns for PIC, OCCURS, REDEFINES
- `parser.py` - Line parsing, basic structure extraction

### Phase 2: Hierarchy & Calculations

- Level-based hierarchy building
- Byte offset calculations
- REDEFINES resolution

### Phase 3: Data Extraction

- `data_holder.py` - Fill from bytes/string
- Type conversion (alphanumeric, numeric)
- COMP placeholder handling

### Phase 4: Polish

- FILLER handling
- OCCURS array support
- Warning logging to file
- Edge case handling

### Phase 5: Testing & Documentation

- Unit tests for patterns and parsing
- Integration tests with complete COBOL examples
- API documentation

---

## Testing Strategy

**Unit Tests:**

- Each regex pattern in isolation
- PIC clause parsing with parametrized tests
- Hierarchy building edge cases

**Integration Tests:**

- Complete COBOL structures from fixtures
- Fill-from-bytes verification
- End-to-end parsing scenarios

**Test Fixtures:**

```
tests/fixtures/
    simple_record.cob      # Basic structure
    nested_record.cob      # Multi-level hierarchy
    occurs_record.cob      # OCCURS examples
    redefines_record.cob   # REDEFINES examples
    mixed_types.cob        # Various PIC types
```

---

## Verification Plan

1. **Run tests:** `make test` - ensure all pass with coverage
2. **Type checking:** `make typecheck` - no mypy errors
3. **Linting:** `make lint` - no ruff errors
4. **Manual verification:** Parse sample COBOL, fill from known data, verify field values

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/cobol_data_structure/models.py` | Create | Data classes |
| `src/cobol_data_structure/patterns.py` | Create | Regex patterns |
| `src/cobol_data_structure/parser.py` | Create | Parser logic |
| `src/cobol_data_structure/data_holder.py` | Create | Data container |
| `src/cobol_data_structure/converters.py` | Create | Type conversion |
| `src/cobol_data_structure/warnings_log.py` | Create | Warning handling |
| `src/cobol_data_structure/__init__.py` | Modify | Export public API |
| `tests/test_patterns.py` | Create | Pattern tests |
| `tests/test_parser.py` | Create | Parser tests |
| `tests/test_data_holder.py` | Create | Data holder tests |
| `tests/test_integration.py` | Create | End-to-end tests |
| `tests/fixtures/*.cob` | Create | COBOL test files |

---

## Conclusion

The **custom line-by-line parser** approach is recommended because it:

1. **Matches the scope** - We need DATA DIVISION parsing, not full COBOL
2. **Prioritizes simplicity** - Direct regex patterns vs. grammar rules
3. **Proven pattern** - Used successfully by similar libraries
4. **Easy to debug** - Clear error messages, isolated components
5. **Extensible** - Easy to add new patterns as needed

This design handles FILLER, OCCURS, and REDEFINES while gracefully degrading on edge cases with warnings rather than failures.
