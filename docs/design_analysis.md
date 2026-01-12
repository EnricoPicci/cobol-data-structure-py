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
| Level numbers 01-49, 77 | Level 66 (RENAMES), 88 (conditions) |

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
| `S9(n)` | Signed numeric | n |
| `9(n)V9(m)` | Numeric with implied decimal | n + m |
| `S9(n)V9(m)` | Signed with implied decimal | n + m |

### COMP Types (Storage Formats)
| Type | Description | Our Handling |
|------|-------------|--------------|
| `COMP` / `COMP-4` | Binary | Placeholder: "COMP value" |
| `COMP-3` | Packed decimal | Placeholder: "COMP-3 value" |
| `COMP-1` | Single-precision float | Placeholder: "COMP-1 value" |
| `COMP-2` | Double-precision float | Placeholder: "COMP-2 value" |

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
│  - Remove comments (columns 1-6, column 7 = '*')                │
│  - Handle continuation lines                                    │
│  - Extract DATA DIVISION section                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Definition Parser                     │
│  - Parse level number                                           │
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
│  - Build hierarchy from level numbers                           │
│  - Calculate field offsets and sizes                            │
│  - Handle OCCURS (arrays)                                       │
│  - Handle REDEFINES (overlays)                                  │
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

### Core Classes

```python
@dataclass
class CobolField:
    """Represents a single COBOL field."""
    name: str
    level: int
    pic: str | None
    size: int
    offset: int
    occurs: int | None
    redefines: str | None
    usage: str | None
    children: list["CobolField"]
    is_filler: bool

@dataclass
class CobolDataStructure:
    """Root structure parsed from COBOL DATA DIVISION."""
    name: str
    root_field: CobolField
    total_size: int
    warnings: list[str]

    def parse_data(self, raw_data: bytes | str) -> "ParsedRecord":
        """Parse raw data into field values."""
        ...

@dataclass
class ParsedRecord:
    """A record populated with actual data values."""
    structure: CobolDataStructure
    raw_data: bytes

    def get_field(self, path: str) -> str | list:
        """Get value by field path, e.g., 'CUSTOMER.ADDRESS.CITY'."""
        ...
```

### Regex Patterns for Parsing

```python
# Level number and name
LEVEL_PATTERN = r'^\s*(\d{2})\s+([A-Z0-9-]+|FILLER)'

# PIC clause
PIC_PATTERN = r'PIC(?:TURE)?\s+([^\s.]+)'

# OCCURS clause
OCCURS_PATTERN = r'OCCURS\s+(\d+)\s+TIMES?'

# REDEFINES clause
REDEFINES_PATTERN = r'REDEFINES\s+([A-Z0-9-]+)'

# USAGE clause
USAGE_PATTERN = r'(?:USAGE\s+)?(?:IS\s+)?(COMP(?:-[1-5])?|COMPUTATIONAL(?:-[1-5])?|DISPLAY|PACKED-DECIMAL|BINARY)'
```

---

## 6. Size Calculation Rules

### Display Format (Default)
| PIC Pattern | Size (bytes) |
|-------------|--------------|
| `X(n)` | n |
| `9(n)` | n |
| `A(n)` | n |
| `S9(n)` | n (sign in zone) |
| `9(n)V9(m)` | n + m |

### COMP Types (Placeholder Handling)
Since COMP conversion is out of scope, we need to know sizes to calculate offsets:

| Type | PIC 9(1-4) | PIC 9(5-9) | PIC 9(10-18) |
|------|------------|------------|--------------|
| COMP/COMP-4 | 2 bytes | 4 bytes | 8 bytes |
| COMP-3 | (n+2)/2 | (n+2)/2 | (n+2)/2 |

For COMP fields, store the expected byte size but return placeholder value when parsed.

---

## 7. Implementation Plan

### Phase 1: Core Parser
1. Line preprocessor (comment removal, DATA DIVISION extraction)
2. Regex-based field parser
3. Hierarchy builder using level numbers
4. Size calculator for common PIC patterns

### Phase 2: Structure Classes
1. `CobolField` dataclass
2. `CobolDataStructure` with parse capability
3. `ParsedRecord` with field access

### Phase 3: Special Handling
1. FILLER support (anonymous fields)
2. OCCURS handling (arrays)
3. REDEFINES handling (overlays)
4. Warning system for unsupported patterns

### Phase 4: Testing and Documentation
1. Unit tests for parser components
2. Integration tests with sample COBOL files
3. Usage documentation and examples

---

## 8. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Multi-line definitions | Preprocessor joins continuation lines |
| Unknown PIC patterns | Log warning, mark as "unknown", estimate size |
| COMP size calculation | Use lookup table based on PIC digits |
| Nested OCCURS | Track occurs at each level, multiply for total |
| REDEFINES complexity | Same offset, largest size wins for parent |

---

## 9. Conclusion

The **custom line-by-line parser with regex** approach best fits the project requirements. It provides:

- **Simplicity**: Easy to implement, test, and maintain
- **Sufficiency**: Handles all required patterns (FILLER, OCCURS, REDEFINES)
- **Flexibility**: Easy to extend for new patterns
- **Robustness**: Simple warning mechanism for edge cases

This approach trades theoretical completeness for practical simplicity, which aligns with the stated design values.

---

## References

- [COBOL PICTURE Clause](https://www.mainframestechhelp.com/tutorials/cobol/picture-clause.htm)
- [COBOL Data Types - TutorialsPoint](https://www.tutorialspoint.com/cobol/cobol_data_types.htm)
- [COBOL DATA DIVISION](https://www.mainframestechhelp.com/tutorials/cobol/data-division.htm)
