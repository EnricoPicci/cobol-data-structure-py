# COBOL Data Structure Parser - Design Analysis & Recommendations

## Executive Summary

**Recommended Approach:** Custom Line-by-Line Parser using regex patterns

This approach aligns with the project's emphasis on simplicity while effectively handling common COBOL DATA DIVISION patterns.

---

## Environment Assumptions

This design assumes COBOL running on **Unix/Linux systems**, which simplifies several aspects:

| Aspect | Assumption | Impact |
|--------|------------|--------|
| Character encoding | ASCII/UTF-8 (not EBCDIC) | No encoding conversion needed |
| Sign encoding | Explicit leading/trailing signs | No overpunch sign handling |
| Line format | Free-form or relaxed column rules | Simpler line preprocessing |
| Log data | Already converted to text | Direct string processing |

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
| PIC S9(n) | Signed numeric fields | Required |
| PIC 9(n)V9(m) | Decimal fields (implicit decimal) | Required |
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

**Cons:**

- **Scope mismatch:** Full parser libraries are designed for complete languages; we only need DATA DIVISION
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

---

## Detailed Specifications

### Core Data Classes

#### CobolField

```python
@dataclass
class CobolField:
    # Identity
    name: str                              # Field name (e.g., "CUSTOMER-NAME")
    level: int                             # Level number (01-49)
    line_number: int                       # Source line for error reporting

    # Hierarchy
    parent: Optional["CobolField"]         # Parent field reference
    children: List["CobolField"]           # Child fields for groups

    # Type information
    pic: Optional[PicClause]               # None for group items

    # Modifiers
    occurs_count: Optional[int]            # OCCURS n TIMES
    redefines_name: Optional[str]          # Name of field being redefined
    redefines_target: Optional["CobolField"]  # Resolved reference

    # Calculated values
    offset: int                            # Byte offset from record start
    storage_length: int                    # Bytes in storage (differs from display for COMP)

    # Metadata
    is_filler: bool                        # True if FILLER field
    warnings: List[str]                    # Any parsing warnings
```

#### PicClause

```python
@dataclass
class PicClause:
    raw: str                    # Original PIC string (e.g., "S9(5)V99")
    field_type: FieldType       # ALPHANUMERIC, NUMERIC, SIGNED_NUMERIC, etc.
    display_length: int         # Characters in display format
    storage_length: int         # Bytes in storage (same as display for non-COMP)
    decimal_positions: int      # Digits after V (implicit decimal)
    is_signed: bool             # True if PIC starts with S
    usage: str                  # DISPLAY, COMP, COMP-3
```

#### FieldType Enum

```python
class FieldType(Enum):
    ALPHANUMERIC = "X"       # PIC X(n)
    NUMERIC = "9"            # PIC 9(n)
    SIGNED_NUMERIC = "S9"    # PIC S9(n)
    COMP = "COMP"            # Binary
    COMP_3 = "COMP-3"        # Packed decimal
    GROUP = "GROUP"          # Group item (no PIC)
    FILLER = "FILLER"        # Unnamed field
    UNKNOWN = "UNKNOWN"      # Unrecognized pattern
```

### Regex Patterns Specification

```python
# Level number: 01-49, 66, 77, 88
LEVEL_PATTERN = re.compile(r"^\s*(\d{2})\s+")

# Field name (allows hyphens, must start with letter)
NAME_PATTERN = re.compile(r"^\s*\d{2}\s+([A-Za-z][A-Za-z0-9\-]*)")

# FILLER keyword
FILLER_PATTERN = re.compile(r"^\s*\d{2}\s+FILLER\b", re.IGNORECASE)

# PIC clause - captures the picture string
# Matches: PIC X(10), PIC IS 9(5), PICTURE S9(3)V99
PIC_PATTERN = re.compile(
    r"\bPIC(?:TURE)?\s+(?:IS\s+)?([SXV9\(\)\-\+]+)",
    re.IGNORECASE
)

# PIC component patterns for parsing the picture string
PIC_ALPHA = re.compile(r"X(?:\((\d+)\))?", re.IGNORECASE)      # X or X(n)
PIC_NUMERIC = re.compile(r"9(?:\((\d+)\))?", re.IGNORECASE)    # 9 or 9(n)
PIC_SIGNED = re.compile(r"^S", re.IGNORECASE)                   # Leading S
PIC_DECIMAL = re.compile(r"V", re.IGNORECASE)                   # Implicit decimal

# COMP usage clause
COMP_PATTERN = re.compile(
    r"\b(COMP-3|COMP-1|COMP-2|COMP|COMPUTATIONAL-3|COMPUTATIONAL)\b",
    re.IGNORECASE
)

# OCCURS clause
OCCURS_PATTERN = re.compile(r"\bOCCURS\s+(\d+)\s*(?:TIMES)?\b", re.IGNORECASE)

# REDEFINES clause
REDEFINES_PATTERN = re.compile(r"\bREDEFINES\s+([A-Za-z][A-Za-z0-9\-]*)", re.IGNORECASE)

# Statement terminator
PERIOD_PATTERN = re.compile(r"\.\s*$")
```

### Line Preprocessing Algorithm

```
Input: Raw COBOL source lines
Output: Clean statements ready for parsing

For each line:
    1. Skip empty lines
    2. Handle optional sequence numbers (columns 1-6):
       - If line starts with 6 digits, strip them
    3. Handle comment lines:
       - If column 7 (or first non-space after sequence) is '*', skip line
    4. Handle continuation:
       - If column 7 is '-', append to previous statement (remove leading spaces)
    5. Strip inline comments (*> to end of line)
    6. Accumulate until period found (statement terminator)
    7. Yield complete statement
```

### Hierarchy Building Algorithm

```
Input: List of parsed CobolField objects (flat)
Output: Tree structure with parent-child relationships

Initialize:
    stack = []           # Stack of (level, field) tuples
    current_record = None

For each field:
    If field.level == 1:
        # Start new record
        If current_record exists:
            yield current_record
        current_record = CobolRecord(name=field.name)
        stack = [(1, field)]
        current_record.root = field
    Else:
        # Find parent: pop until stack top has lower level
        While stack and stack[-1][0] >= field.level:
            stack.pop()

        If stack is empty:
            # Orphan field - warn and attach to record root
            Log warning
            parent = current_record.root
        Else:
            parent = stack[-1][1]

        # Establish relationship
        field.parent = parent
        parent.children.append(field)
        stack.append((field.level, field))

Yield current_record if exists
```

### Offset Calculation Algorithm

```
Input: CobolRecord with hierarchy built
Output: Each field has offset and storage_length set

Function calculate_offsets(field, current_offset):
    field.offset = current_offset

    If field is group (has children, no PIC):
        running = current_offset
        For each child in field.children:
            If child.redefines_target:
                # REDEFINES: use target's offset, don't advance
                child.offset = child.redefines_target.offset
                calculate_offsets(child, child.offset)
            Else:
                calculate_offsets(child, running)
                running += child.storage_length * (child.occurs_count or 1)
        field.storage_length = running - current_offset
    Else:
        # Leaf field: length from PIC
        field.storage_length = field.pic.storage_length

    Return field.storage_length * (field.occurs_count or 1)

# Entry point
calculate_offsets(record.root, 0)
record.total_length = record.root.storage_length
```

### COMP Storage Length Calculation

For Unix/Linux COBOL (GnuCOBOL and similar):

| PIC Clause | COMP (Binary) | COMP-3 (Packed) |
|------------|---------------|-----------------|
| 9(1-2) | 1 byte | 1 byte |
| 9(3-4) | 2 bytes | 2 bytes |
| 9(5-6) | 3 bytes | 3 bytes |
| 9(7-9) | 4 bytes | 4-5 bytes |
| 9(10-18) | 8 bytes | 6-10 bytes |

**COMP-3 formula:** `ceil((digits + 1) / 2)` bytes

### Data Extraction (fill_from_bytes)

```
Input: Raw bytes/string from log, CobolRecord structure
Output: DataHolder with field values populated

Function fill_from_bytes(data, record):
    holder = DataHolder(record)

    Function extract_field(field, data):
        start = field.offset
        end = start + field.storage_length
        raw_bytes = data[start:end]

        If field.occurs_count > 1:
            # Array: extract each occurrence
            values = []
            item_length = field.storage_length
            For i in range(field.occurs_count):
                item_start = start + (i * item_length)
                item_bytes = data[item_start:item_start + item_length]
                values.append(convert_value(field, item_bytes))
            Return values

        If field is group:
            # Recurse into children
            result = {}
            For child in field.children:
                If not child.is_filler:
                    result[child.name] = extract_field(child, data)
            Return result

        Return convert_value(field, raw_bytes)

    For each top-level field:
        holder._data[field.name] = extract_field(field, data)

    Return holder
```

### Type Conversion (convert_value)

```
Function convert_value(field, raw_bytes):
    # Decode bytes to string (ASCII for Unix COBOL)
    text = raw_bytes.decode('ascii', errors='replace')

    Match field.pic.field_type:
        Case ALPHANUMERIC:
            Return text  # Preserve as-is, user can .strip()

        Case NUMERIC:
            # Remove leading zeros, convert to int
            cleaned = text.lstrip('0') or '0'
            Return int(cleaned)

        Case SIGNED_NUMERIC:
            # Handle explicit sign (leading or trailing)
            If text.startswith('-') or text.endswith('-'):
                Return -int(text.replace('-', '').lstrip('0') or '0')
            Else:
                Return int(text.replace('+', '').lstrip('0') or '0')

        Case field with decimal_positions > 0:
            # Implicit decimal point
            value = int(text.replace('-', '').replace('+', '').lstrip('0') or '0')
            result = value / (10 ** field.pic.decimal_positions)
            If text.startswith('-') or text.endswith('-'):
                result = -result
            Return result

        Case COMP, COMP_3:
            Return f"<{field.pic.usage} value>"  # Placeholder

        Case UNKNOWN:
            Return text  # Return raw text
```

### API Access Patterns

```python
# DataHolder supports multiple access patterns

class DataHolder:
    def __getattr__(self, name: str) -> Any:
        """Attribute access: holder.customer_name"""
        # Convert Python name to COBOL name
        cobol_name = name.upper().replace('_', '-')
        return self._get_field(cobol_name)

    def __getitem__(self, key: str) -> Any:
        """Dict access: holder["CUSTOMER-NAME"]"""
        return self._get_field(key.upper())

    def _get_field(self, name: str) -> Any:
        """Case-insensitive field lookup."""
        # Try exact match first
        if name in self._data:
            return self._data[name]
        # Try case-insensitive
        for key in self._data:
            if key.upper() == name.upper():
                return self._data[key]
        raise KeyError(f"Field not found: {name}")

# Usage:
holder.customer_name      # Returns value of CUSTOMER-NAME
holder["CUSTOMER-NAME"]   # Same value
holder["customer-name"]   # Same value (case-insensitive)
```

### FILLER Handling

```
- Multiple FILLERs: Auto-number as FILLER-1, FILLER-2, etc.
- Skip in attribute access (no holder.filler_1)
- Include in to_dict() with special marker: {"FILLER-1": "<filler:5>"}
- Count toward offset calculations (they occupy bytes)
```

---

## Edge Case Handling Strategy

| Edge Case | Handling |
|-----------|----------|
| Unknown PIC pattern | Log warning, set type to UNKNOWN, extract as raw text |
| COMP/COMP-3 | Placeholder text: `"<COMP-3 value>"` |
| Missing period | Attempt parse, warn if ambiguous |
| Level 66 (RENAMES) | Skip with warning (virtual field, out of scope) |
| Level 77 (independent) | Parse as standalone record |
| Level 88 (conditions) | Skip silently (not data, just metadata) |
| INDEXED BY | Ignore (index variables, not data) |
| VALUE clause | Ignore (initial values, not structure) |
| OCCURS DEPENDING ON | Use maximum count, log warning |
| REDEFINES target not found | Log warning, use declared offset |
| REDEFINES larger than target | Allow, log warning |
| Multiple REDEFINES same target | Allow (valid COBOL) |
| Circular REDEFINES | Detect and error (invalid COBOL) |
| Data shorter than expected | Fill missing fields with None, log warning |
| Data longer than expected | Truncate to record length, ignore excess |
| Non-digit in numeric field | Set to None, log warning |
| Invalid sign character | Set to None, log warning |

---

## Error Handling Strategy

### Exception Hierarchy

```python
class CobolError(Exception):
    """Base exception for all COBOL parsing errors."""

class CobolParseError(CobolError):
    """Invalid COBOL syntax during parsing."""

class CobolDataError(CobolError):
    """Data doesn't match expected structure."""

class CobolFieldError(CobolError):
    """Field not found or type mismatch."""
```

### Strict vs Lenient Mode

```python
# Global default
cobol_data_structure.strict_mode = False  # Lenient by default

# Per-operation override
record = parse_string(source, strict=True)
holder.fill_from_bytes(data, strict=False)

# Behavior differences:
# Lenient: Log warnings, use defaults/None for failures
# Strict: Raise exceptions on first error
```

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

# Access fields (multiple patterns supported)
print(holder.name)           # "John Doe  " (raw, user can .strip())
print(holder["NAME"])        # Same value
print(holder.name.strip())   # "John Doe" (trimmed by user)
print(holder.code)           # "<COMP-3 value>"
print(holder.to_dict())      # All fields as dict

# Nested access for groups
print(holder.type.code)      # Access nested field
print(holder["TYPE"]["CODE"])  # Dict style

# OCCURS array access
print(holder.items[0])       # First occurrence
print(holder.items[0].code)  # Nested field in occurrence
```

---

## Implementation Phases

### Phase 1: Core Parsing

- `models.py` - CobolField, CobolRecord, PicClause dataclasses
- `patterns.py` - Regex patterns for PIC, OCCURS, REDEFINES
- `parser.py` - Line preprocessing and statement parsing

### Phase 2: Hierarchy & Calculations

- Level-based hierarchy building (stack algorithm)
- Byte offset calculations
- REDEFINES resolution

### Phase 3: Data Extraction

- `data_holder.py` - Fill from bytes/string
- Type conversion (alphanumeric, numeric, signed, decimal)
- COMP placeholder handling

### Phase 4: Polish

- FILLER handling with auto-numbering
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
- Offset calculation verification
- Type conversion for all field types

**Integration Tests:**

- Complete COBOL structures from fixtures
- Fill-from-bytes verification
- End-to-end parsing scenarios
- Error handling in strict/lenient modes

**Test Fixtures:**

```
tests/fixtures/
    simple_record.cob      # Basic structure
    nested_record.cob      # Multi-level hierarchy
    occurs_record.cob      # OCCURS examples
    redefines_record.cob   # REDEFINES examples
    mixed_types.cob        # Various PIC types
    edge_cases.cob         # Unusual but valid patterns
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

## Design Review Summary

This design was reviewed for gaps and potential issues. Key findings addressed:

| Issue | Resolution |
|-------|------------|
| No concrete regex patterns | Added detailed patterns specification |
| Missing line preprocessing | Added preprocessing algorithm |
| Data model incomplete | Added parent reference, line_number, storage vs display length |
| Offset calculation vague | Added detailed algorithm with REDEFINES handling |
| Sign encoding unspecified | Specified leading/trailing explicit signs (Unix COBOL) |
| API access for hyphenated names | Added underscore-to-hyphen conversion |
| Case sensitivity unclear | Specified case-insensitive lookup |
| Error handling vague | Added exception hierarchy and strict/lenient modes |
| FILLER collisions | Added auto-numbering for multiple FILLERs |

**Not applicable (Unix/Linux environment):**
- EBCDIC encoding (uses ASCII)
- Overpunch sign encoding (uses explicit signs)
- Column-based formatting (relaxed in modern COBOL)

---

## Conclusion

The **custom line-by-line parser** approach is recommended because it:

1. **Matches the scope** - We need DATA DIVISION parsing, not full COBOL
2. **Prioritizes simplicity** - Direct regex patterns vs. grammar rules
3. **Proven pattern** - Used successfully by similar libraries
4. **Easy to debug** - Clear error messages, isolated components
5. **Extensible** - Easy to add new patterns as needed

This design handles FILLER, OCCURS, and REDEFINES while gracefully degrading on edge cases with warnings rather than failures.
