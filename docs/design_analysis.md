# Design Analysis: COBOL Data Structure Parser

## 1. Requirements Summary

### Core Goal
Build a Python application that:
1. Reads COBOL source code and extracts data structure definitions from the `DATA DIVISION`
2. Creates Python representations of these structures
3. Enables parsing raw data (from logs) into the structure, allowing field-by-field value access

### Scope Boundaries
| In Scope | Out of Scope |
|----------|--------------|
| Common PIC types (X, 9, A, S, V) | Edge cases and exotic PIC formats |
| FILLER handling | COMP value conversion (placeholder only) |
| OCCURS (arrays) | EBCDIC encoding |
| REDEFINES | Full COBOL syntax compliance |
| Level numbers 01-49, 77 | Level 66 (RENAMES), 78 (constants), 88 (conditions) |
| Warning file for unsupported constructs | COPY/COPYBOOK expansion |
| Case-insensitive parsing | DEPENDING ON (variable-length arrays) |

### Design Values
- **Simplicity over completeness**: Handle common cases well; gracefully degrade for edge cases
- **Maintainability**: Code should be easy to understand and extend
- **Robustness**: Log warnings for unsupported constructs rather than failing

---

## 2. COBOL DATA DIVISION Syntax Overview

### Basic Structure
COBOL data definitions follow a hierarchical structure using level numbers:

```cobol
01 CUSTOMER-RECORD.
    05 CUST-ID           PIC 9(5).
    05 CUST-NAME         PIC X(30).
    05 CUST-ADDRESS.
        10 STREET        PIC X(40).
        10 CITY          PIC X(20).
        10 ZIP           PIC 9(5).
    05 ORDER-COUNT       PIC 9(3) COMP-3.
```

### COBOL Source Format (Fixed-Format)
| Columns | Name | Purpose |
|---------|------|---------|
| 1-6 | Sequence Area | Line numbers (ignored) |
| 7 | Indicator | `*` = comment, `-` = continuation, `D` = debug |
| 8-11 | Area A | Level numbers 01, 77; division/section headers |
| 12-72 | Area B | Data definitions, statements |
| 73-80 | Identification | Program ID (ignored) |

### Key Syntax Elements

| Element | Description | Example |
|---------|-------------|---------|
| **Level Number** | Hierarchy indicator (01-49, 77) | `05 FIELD-NAME` |
| **Data Name** | Field identifier | `CUST-NAME` |
| **FILLER** | Anonymous placeholder | `05 FILLER PIC X(10).` |
| **PIC/PICTURE** | Data type and size | `PIC X(30)`, `PIC 9(5)V99` |
| **OCCURS** | Array definition | `OCCURS 10 TIMES` |
| **REDEFINES** | Storage overlay | `REDEFINES OTHER-FIELD` |
| **USAGE** | Storage format | `COMP`, `COMP-3`, `DISPLAY` |

### Common PIC Clause Patterns
| Pattern | Meaning | Size (bytes) |
|---------|---------|--------------|
| `X(n)` | n alphanumeric characters | n |
| `9(n)` | n numeric digits | n |
| `A(n)` | n alphabetic characters | n |
| `S9(n)` | Signed numeric (trailing overpunch) | n |
| `S9(n) SIGN SEPARATE` | Signed with separate sign byte | n + 1 |
| `9(n)V9(m)` | Numeric with implied decimal | n + m |
| `S9(n)V9(m)` | Signed with implied decimal | n + m |

### COMP Types (Storage Formats)
| Type | Description | Size | Our Handling |
|------|-------------|------|--------------|
| `COMP` / `COMP-4` | Binary | See table below | Placeholder: "COMP value" |
| `COMP-3` | Packed decimal | `(digits + 1) / 2` rounded up | Placeholder: "COMP-3 value" |
| `COMP-1` | Single-precision float | 4 bytes (no PIC) | Placeholder: "COMP-1 value" |
| `COMP-2` | Double-precision float | 8 bytes (no PIC) | Placeholder: "COMP-2 value" |

---

## 3. Approach Analysis

### Option A: Formal Parser (Grammar + Lexer)

**Description**: Use a parsing library (PLY, Lark, pyparsing, ANTLR) with a formal grammar definition.

**Architecture**:
```
COBOL Source → Lexer → Token Stream → Parser → AST → Python Objects
```

**Pros**:
- Clean separation of lexical and syntactic analysis
- Handles complex/ambiguous grammars well
- Industry-standard approach for language processing
- Easier to extend grammar for new features

**Cons**:
- **High complexity**: Requires grammar specification, lexer rules, parser rules
- **Steep learning curve**: Team must understand parsing theory
- **Overkill**: Full COBOL grammar is complex; we only need DATA DIVISION
- **More dependencies**: External parsing libraries required
- **Harder to debug**: Errors can be obscure

**Effort Estimate**: High (grammar design + implementation + testing)

---

### Option B: Custom Line-by-Line Parser with Regex

**Description**: Process COBOL source line by line using regex patterns to extract components, building the structure based on level numbers.

**Architecture**:
```
COBOL Source → Line Iterator → Regex Extraction → Structure Builder → Python Objects
```

**Pros**:
- **Simple and transparent**: Easy to understand what each line does
- **Easy to debug**: Step through line by line
- **No external dependencies**: Uses only Python standard library
- **Fast implementation**: Can be built incrementally
- **Sufficient for scope**: Handles common patterns well
- **Graceful degradation**: Easy to log warnings for unsupported patterns

**Cons**:
- Less elegant for multi-line continuations
- May require refactoring if scope expands significantly
- Regex patterns can become complex

**Effort Estimate**: Low to Medium

---

### Comparison Matrix

| Criteria | Formal Parser | Custom Regex Parser |
|----------|--------------|---------------------|
| Simplicity | Low | **High** |
| Learning Curve | Steep | **Gentle** |
| External Dependencies | Yes | **No** |
| Handles Common Cases | Yes | **Yes** |
| Handles Edge Cases | Better | Adequate |
| Debugging Ease | Low | **High** |
| Implementation Speed | Slow | **Fast** |
| Maintainability | Medium | **High** |

---

## 4. Recommendation

**Recommended Approach: Custom Line-by-Line Parser with Regex (Option B)**

### Rationale
1. **Aligns with design values**: Simplicity is explicitly valued over completeness
2. **Sufficient for requirements**: Common patterns (PIC, FILLER, OCCURS, REDEFINES) are well-structured and regex-parseable
3. **Low risk**: Easy to implement, test, and debug
4. **Graceful degradation**: Simple to add warning logs for unrecognized patterns
5. **No dependencies**: Reduces maintenance burden and compatibility concerns

### When to Reconsider
Consider migrating to a formal parser if:
- Requirements expand to cover full COBOL syntax
- Multi-line continuations become common
- Need to parse PROCEDURE DIVISION as well

---

## 5. Proposed Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        COBOL Source File                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Line Preprocessor                          │
│  - Strip columns 1-6 (sequence) and 73-80 (identification)      │
│  - Handle column 7 indicator (* comment, - continuation)        │
│  - Join continuation lines                                      │
│  - Extract DATA DIVISION section                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Definition Parser                     │
│  - Parse level number (1 or 2 digits)                           │
│  - Parse data name (or FILLER)                                  │
│  - Parse PIC clause                                             │
│  - Parse OCCURS clause                                          │
│  - Parse REDEFINES clause                                       │
│  - Parse USAGE clause                                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Structure Builder                          │
│  - Build hierarchy from level numbers (stack-based)             │
│  - Calculate field offsets and sizes                            │
│  - Handle OCCURS (arrays)                                       │
│  - Handle REDEFINES (overlays)                                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Warning Handler                           │
│  - Collect warnings during parsing                              │
│  - Write warnings to file (as per requirements)                 │
│  - Track line numbers for error reporting                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CobolDataStructure                          │
│  - Root object representing the parsed structure                │
│  - Method: parse_data(raw_bytes) → populated structure          │
│  - Method: get_field(path) → field value                        │
│  - Property: total_size → structure size in bytes               │
└─────────────────────────────────────────────────────────────────┘
```

### API Entry Point

```python
def parse_cobol_file(
    filepath: str | Path,
    warning_file: str | Path | None = None
) -> CobolDataStructure:
    """Main entry point: parse a COBOL file and return the structure."""
    ...

def parse_cobol_string(
    source: str,
    name: str = "RECORD",
    warning_file: str | Path | None = None
) -> CobolDataStructure:
    """Parse COBOL source from a string."""
    ...
```

### Core Classes

```python
@dataclass
class CobolField:
    """Represents a single COBOL field."""
    name: str
    level: int
    pic: str | None              # Original PIC string
    pic_type: str | None         # Parsed type: 'X', '9', 'A', etc.
    size: int
    offset: int                  # Absolute offset from record start
    occurs: int | None           # Array count (None if not array)
    redefines: str | None        # Name of redefined field
    usage: str | None            # COMP, COMP-3, DISPLAY, etc.
    children: list["CobolField"]
    parent: "CobolField | None"  # Parent field reference
    is_filler: bool
    is_signed: bool              # Has S prefix in PIC
    decimal_positions: int       # Digits after V (0 if no V)

@dataclass
class Warning:
    """Structured warning information."""
    message: str
    line_number: int | None
    field_name: str | None
    severity: str  # 'warning' or 'error'

@dataclass
class CobolDataStructure:
    """Root structure parsed from COBOL DATA DIVISION."""
    name: str
    root_field: CobolField
    total_size: int
    warnings: list[Warning]
    source_file: str | None
    field_index: dict[str, CobolField]  # Fast lookup by name

    def parse_data(self, raw_data: bytes | str) -> "ParsedRecord":
        """Parse raw data into field values."""
        ...

    def write_warnings(self, filepath: str | Path) -> None:
        """Write collected warnings to file."""
        ...

@dataclass
class ParsedRecord:
    """A record populated with actual data values."""
    structure: CobolDataStructure
    raw_data: bytes

    def get_field(self, path: str) -> str | list:
        """Get value by field path, e.g., 'CUSTOMER.ADDRESS.CITY'."""
        ...

    def get_field_by_index(self, path: str, index: int) -> str:
        """Get array element, e.g., get_field_by_index('ITEMS', 0)."""
        ...

    def to_dict(self) -> dict:
        """Return all field values as nested dictionary."""
        ...
```

### Regex Patterns for Parsing

All patterns use `re.IGNORECASE` for case-insensitive matching.

```python
import re

FLAGS = re.IGNORECASE

# Level number (1-2 digits) and name
LEVEL_PATTERN = re.compile(
    r'^\s*(\d{1,2})\s+([A-Z][A-Z0-9-]*|FILLER)',
    FLAGS
)

# PIC clause - handles editing characters and decimal points
PIC_PATTERN = re.compile(
    r'PIC(?:TURE)?(?:\s+IS)?\s*([AXVS9ZP*$+\-,./()0-9B]+)',
    FLAGS
)

# OCCURS clause
OCCURS_PATTERN = re.compile(
    r'OCCURS\s+(\d+)(?:\s+TIMES?)?',
    FLAGS
)

# REDEFINES clause
REDEFINES_PATTERN = re.compile(
    r'REDEFINES\s+([A-Z][A-Z0-9-]*)',
    FLAGS
)

# USAGE clause
USAGE_PATTERN = re.compile(
    r'(?:USAGE\s+)?(?:IS\s+)?(COMP(?:UTATIONAL)?(?:-[1-5])?|DISPLAY|PACKED-DECIMAL|BINARY)',
    FLAGS
)

# Detection patterns for warnings
COPY_PATTERN = re.compile(r'\bCOPY\s+([A-Z][A-Z0-9-]*)', FLAGS)
DEPENDING_ON_PATTERN = re.compile(r'DEPENDING\s+ON\s+([A-Z][A-Z0-9-]*)', FLAGS)
SIGN_SEPARATE_PATTERN = re.compile(r'SIGN\s+(?:IS\s+)?(?:LEADING|TRAILING)\s+SEPARATE', FLAGS)
```

---

## 6. Size Calculation Rules

### Display Format (Default)
| PIC Pattern | Size (bytes) |
|-------------|--------------|
| `X(n)` | n |
| `9(n)` | n |
| `A(n)` | n |
| `S9(n)` | n (trailing overpunch sign) |
| `S9(n) SIGN SEPARATE` | n + 1 |
| `9(n)V9(m)` | n + m |

### COMP/COMP-4 (Binary) Size Table
| PIC Digits | Size (bytes) |
|------------|--------------|
| 1-4 | 2 |
| 5-9 | 4 |
| 10-18 | 8 |

### COMP-3 (Packed Decimal) Size Formula
```
Size = ceil((digits + 1) / 2)
```

| PIC Digits | Size (bytes) | Calculation |
|------------|--------------|-------------|
| 1 | 1 | ceil(2/2) = 1 |
| 2 | 2 | ceil(3/2) = 2 |
| 3 | 2 | ceil(4/2) = 2 |
| 4 | 3 | ceil(5/2) = 3 |
| 5 | 3 | ceil(6/2) = 3 |
| 7 | 4 | ceil(8/2) = 4 |
| 9 | 5 | ceil(10/2) = 5 |

### COMP-1 and COMP-2 (Floating Point)
| Type | Size | Notes |
|------|------|-------|
| COMP-1 | 4 bytes | No PIC clause allowed |
| COMP-2 | 8 bytes | No PIC clause allowed |

For COMP fields, store the expected byte size but return placeholder value when parsed.

---

## 7. Key Algorithms

### Line Preprocessing Algorithm

```python
def preprocess_lines(lines: list[str]) -> list[str]:
    """Preprocess COBOL source lines."""
    result = []
    current_line = ""

    for line in lines:
        # Handle short lines
        if len(line) < 7:
            continue

        indicator = line[6] if len(line) > 6 else ' '

        # Skip comments and debug lines
        if indicator in ('*', '/', 'D', 'd'):
            continue

        # Extract code area (columns 8-72)
        code = line[7:72] if len(line) > 72 else line[7:]
        code = code.rstrip()

        # Handle continuation
        if indicator == '-':
            current_line += code.lstrip()
        else:
            if current_line:
                result.append(current_line)
            current_line = code

    if current_line:
        result.append(current_line)

    return result
```

### Hierarchy Building Algorithm (Stack-Based)

```python
def build_hierarchy(fields: list[CobolField]) -> CobolField:
    """Build field hierarchy using level numbers."""
    if not fields:
        raise ValueError("No fields to build hierarchy from")

    root = fields[0]
    stack = [root]

    for field in fields[1:]:
        # Pop stack until we find parent (lower level number)
        while stack and stack[-1].level >= field.level:
            stack.pop()

        if stack:
            parent = stack[-1]
            parent.children.append(field)
            field.parent = parent

        stack.append(field)

    return root
```

### Group Item Size Calculation

```python
def calculate_sizes(field: CobolField) -> int:
    """Calculate sizes recursively. Group items = sum of children."""
    if field.children:
        # Group item: size is sum of children
        child_size = sum(calculate_sizes(child) for child in field.children)
        field.size = child_size * (field.occurs or 1)
    # Elementary items already have size from PIC parsing

    return field.size
```

---

## 8. Implementation Plan

### Phase 1: Core Parser
1. Line preprocessor (column handling, continuation, comments)
2. Regex-based field parser
3. Hierarchy builder using level numbers
4. Size calculator for common PIC patterns

### Phase 2: Structure Classes
1. `CobolField` dataclass with all attributes
2. `CobolDataStructure` with parse capability
3. `ParsedRecord` with field access
4. `Warning` dataclass and `WarningHandler`

### Phase 3: Special Handling
1. FILLER support (generate unique internal names)
2. OCCURS handling (arrays)
3. REDEFINES handling (overlays with same offset)
4. Warning system for unsupported patterns

### Phase 4: Testing and Documentation
1. Unit tests for parser components
2. Integration tests with sample COBOL files
3. Usage documentation and examples

---

## 9. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Multi-line definitions | Preprocessor joins continuation lines (column 7 = '-') |
| Unknown PIC patterns | Log warning, mark as "unknown", use size 0 |
| COMP size calculation | Use lookup table based on PIC digit count |
| Nested OCCURS | Track occurs at each level, multiply for total size |
| REDEFINES complexity | Same offset as redefined field; largest size wins for parent |
| Lowercase COBOL | All regex patterns use `re.IGNORECASE` |
| COPY statements | Detect and log warning; not expanded |
| DEPENDING ON | Detect and log warning; use max count |
| Level 66/88 | Detect and skip with warning |

---

## 10. Warning File Format

Warnings are written to a file in a simple, readable format:

```
# COBOL Parser Warnings
# Source: /path/to/source.cbl
# Generated: 2024-01-15 10:30:00

[WARNING] Line 45, field VARIABLE-ARRAY: DEPENDING ON clause not supported, using max count 100
[WARNING] Line 52, field COPY-SECTION: COPY statement not supported, skipping
[WARNING] Line 78, field UNKNOWN-TYPE: Unrecognized PIC pattern 'Q(10)', marking as unknown
[ERROR] Line 92: Could not parse line, skipping
```

---

## 11. Conclusion

The **custom line-by-line parser with regex** approach best fits the project requirements. It provides:

- **Simplicity**: Easy to implement, test, and maintain
- **Sufficiency**: Handles all required patterns (FILLER, OCCURS, REDEFINES)
- **Flexibility**: Easy to extend for new patterns
- **Robustness**: Simple warning mechanism for edge cases

This approach trades theoretical completeness for practical simplicity, which aligns with the stated design values.

---

## 12. Review Findings Addressed

This document incorporates feedback from technical review:

1. **COMP-3 formula corrected**: Changed from `(n+2)/2` to `ceil((n+1)/2)`
2. **COMP-1/COMP-2 sizes added**: 4 and 8 bytes respectively, no PIC clause
3. **Regex patterns fixed**: Added case-insensitivity, single-digit level support, proper PIC handling
4. **Warning file handler added**: New component in architecture
5. **Column conventions documented**: Full column handling in preprocessor
6. **Hierarchy algorithm provided**: Stack-based approach with pseudo-code
7. **CobolField attributes expanded**: Added `parent`, `is_signed`, `decimal_positions`, `pic_type`
8. **SIGN SEPARATE handling**: Added to size calculation rules
9. **Detection patterns added**: For COPY, DEPENDING ON, and other unsupported features

---

## References

- [COBOL PICTURE Clause](https://www.mainframestechhelp.com/tutorials/cobol/picture-clause.htm)
- [COBOL Data Types - TutorialsPoint](https://www.tutorialspoint.com/cobol/cobol_data_types.htm)
- [COBOL DATA DIVISION](https://www.mainframestechhelp.com/tutorials/cobol/data-division.htm)
- [COBOL COMP-3 Packed Decimal](https://www.mainframestechhelp.com/tutorials/cobol/comp-3.htm)
- [COBOL Level Numbers](https://www.mainframestechhelp.com/tutorials/cobol/level-numbers.htm)
