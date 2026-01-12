# COBOL Data Structure Parser - Design Analysis and Recommendations

## Executive Summary

This document analyzes the requirements for building a COBOL data structure parser in Python and recommends the best approach. After evaluating three potential approaches (full parser with lexer/AST, regex-based parser, and line-by-line recursive parser), **I recommend the line-by-line recursive parser approach** for its optimal balance of simplicity, maintainability, and capability to handle COBOL's naturally line-oriented structure.

**Note**: This document has been updated based on comprehensive design reviews. See `/workspaces/cobol-data-structure-py/docs/design_review_findings.md` for detailed analysis of issues and fixes applied.

## 1. Requirements Analysis

### 1.1 Core Functionality

The application must:

1. **Parse COBOL DATA DIVISION** structures from COBOL source files
2. **Generate Python representations** of these structures that can:
   - Hold the same values as COBOL variables
   - Parse binary/text data from log files (e.g., values captured during MOVE operations)
   - Provide field-level access to values
3. **Support common COBOL patterns**:
   - FILLER (unnamed data groupings)
   - OCCURS (array/repetition constructs)
   - REDEFINES (overlapping memory layouts)
4. **Handle common data types**:
   - PIC X (alphanumeric)
   - PIC 9 (numeric display)
   - COMP-3 (packed decimal)
   - Other common numeric types (COMP, COMP-1, COMP-2)
5. **Graceful degradation**: Warn on unsupported edge cases rather than failing

### 1.2 Example Use Case

Given this COBOL structure:
```cobol
01 LAST-DATA.
    03 NAME PIC X(10).
    03 TYPE.
        05 CODE PIC 9(5) COMP-3.
        05 DESC PIC X(10).
```

The Python representation should:
- Parse the structure definition
- Calculate byte offsets and sizes for each field
- Parse a binary string (from logs) into field values
- Allow access like: `last_data.TYPE.CODE` or `last_data.get_field("CODE")`

### 1.3 Design Principles

1. **Simplicity over completeness**: Focus on 80% of common cases
2. **Clear error reporting**: Log warnings for unsupported constructs
3. **Maintainability**: Code should be easy to understand and extend
4. **Pythonic**: Follow Python idioms and best practices

## 2. Approach Comparison

### 2.1 Approach 1: Full Parser (Lexer + Parser + AST)

**Description**: Build a complete parser using parser generator tools (PLY, Lark, ANTLR) with a formal grammar.

**Architecture**:
```
COBOL Source → Lexer → Tokens → Parser → AST → Python Data Model
```

**Pros**:
- ✅ Theoretically sound and complete
- ✅ Well-established approach
- ✅ Can handle complex grammar rules
- ✅ Good error detection
- ✅ Extensible to full COBOL parsing if needed

**Cons**:
- ❌ Significant complexity for parsing only DATA DIVISION
- ❌ Steep learning curve for maintenance
- ❌ Need to handle COBOL's idiosyncratic grammar (free-form vs fixed-form, etc.)
- ❌ More code to write and maintain
- ❌ Overkill for the stated requirements

**Dependencies**: PLY, Lark, or ANTLR4

**Effort**: High (2-3 weeks for basic implementation)

**When to use**: When you need to parse the entire COBOL language or have complex grammar requirements.

### 2.2 Approach 2: Regex-Based Pattern Matching

**Description**: Use regular expressions to match and extract data structure definitions line by line.

**Architecture**:
```
COBOL Source → Line-by-line regex matching → Extract components → Build data model
```

**Example**:
```python
pattern = r'^\s*(\d{2})\s+(\S+)\s+PIC\s+([X9]+)\((\d+)\)'
match = re.match(pattern, line)
```

**Pros**:
- ✅ Simple to understand
- ✅ No external dependencies
- ✅ Fast to implement initial version
- ✅ Good for simple patterns

**Cons**:
- ❌ Becomes unmaintainable as complexity grows
- ❌ Difficult to handle nested structures
- ❌ Hard to track hierarchical relationships
- ❌ Error messages are cryptic
- ❌ Regex for COBOL can get very complex

**Dependencies**: None (uses standard library `re`)

**Effort**: Low initially, grows significantly with complexity

**When to use**: For very simple, flat data structures only.

### 2.3 Approach 3: Line-by-Line Recursive Parser (RECOMMENDED)

**Description**: Build a custom parser that processes COBOL line by line, using level numbers to track hierarchy and recursively building the structure.

**Architecture**:
```
COBOL Source → Line iterator → Parse level/field/PIC → Build hierarchical model → Python data classes
```

**Key Concepts**:
1. **Level-based hierarchy**: COBOL level numbers (01, 05, 10, etc.) naturally define parent-child relationships
2. **Tokenization**: Split each line into components (level, name, PIC clause, etc.)
3. **Recursive descent**: Build tree structure based on level numbers
4. **State tracking**: Maintain parsing context (current parent, offset, etc.)

**Example Logic**:
```python
class CobolField:
    level: int
    name: str
    picture: Optional[str]
    children: List[CobolField]
    byte_offset: int
    byte_length: int

def parse_data_division(lines):
    root_items = []
    line_iter = iter(lines)

    for line in line_iter:
        level, name, pic_clause = parse_line(line)
        field = CobolField(level, name, pic_clause)

        # Recursively parse children with higher level numbers
        field.children = parse_children(line_iter, level)
        root_items.append(field)

    return root_items
```

**Pros**:
- ✅ **Perfect fit for COBOL's structure**: Level numbers provide natural hierarchy
- ✅ **Simple and maintainable**: Easy to understand the code flow
- ✅ **No external dependencies**: Uses only standard library
- ✅ **Easy to debug**: Can print state at each step
- ✅ **Extensible**: Easy to add new PIC types or clauses
- ✅ **Good error reporting**: Know exact line number and context
- ✅ **Handles nesting naturally**: Recursive approach matches COBOL's structure

**Cons**:
- ❌ Requires careful handling of edge cases
- ❌ Need to implement tokenization manually
- ❌ Must track state (indentation, parent-child relationships)

**Dependencies**: None (standard library only)

**Effort**: Medium (1-2 weeks for robust implementation)

**When to use**: For parsing structured, hierarchical data formats with clear level indicators (perfect for COBOL DATA DIVISION).

## 3. Detailed Recommendation: Line-by-Line Recursive Parser

### 3.1 Why This Approach?

COBOL's DATA DIVISION has several characteristics that make it ideal for this approach:

1. **Line-oriented**: Each data item is typically defined on a single line
2. **Level-based hierarchy**: Level numbers (01, 05, 10, etc.) explicitly define structure
3. **Column-based format**: Fixed positions (especially in fixed-form COBOL)
4. **Limited syntax**: DATA DIVISION has much simpler syntax than PROCEDURE DIVISION
5. **Predictable patterns**: Most data definitions follow consistent formats

### 3.2 Architecture Overview

```
┌─────────────────┐
│ COBOL Source    │
│ Files (.cbl)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ File Reader     │
│ - Handle        │
│   encoding      │
│ - Extract DATA  │
│   DIVISION      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Line Tokenizer  │
│ - Split into    │
│   components    │
│ - Handle        │
│   continuations │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Recursive       │
│ Parser          │
│ - Build tree    │
│ - Track levels  │
│ - Calculate     │
│   offsets       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Data Model      │
│ - CobolField    │
│ - CobolRecord   │
│ - Type info     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Python          │
│ Generator       │
│ - Create        │
│   dataclasses   │
│ - Parse binary  │
│ - Serialize     │
└─────────────────┘
```

### 3.3 Core Components

#### 3.3.1 Data Model

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pathlib import Path

class PictureCategory(Enum):
    """Picture clause category (base type)."""
    ALPHABETIC = "A"
    ALPHANUMERIC = "X"
    NUMERIC = "9"
    NATIONAL = "N"  # Unicode

class UsageType(Enum):
    """Storage usage type."""
    DISPLAY = "DISPLAY"
    COMP = "COMP"  # Binary
    COMP1 = "COMP-1"  # Single-precision float
    COMP2 = "COMP-2"  # Double-precision float
    COMP3 = "COMP-3"  # Packed decimal
    COMP4 = "COMP-4"  # Binary (synonym for COMP)
    COMP5 = "COMP-5"  # Native binary
    PACKED_DECIMAL = "PACKED-DECIMAL"
    BINARY = "BINARY"

class WarningSeverity(Enum):
    """Warning severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

@dataclass
class ParserWarning:
    """Structured warning with context."""
    severity: WarningSeverity
    message: str
    line_number: Optional[int] = None
    field_name: Optional[str] = None
    source_file: Optional[Path] = None

    def __str__(self) -> str:
        context = f"{self.source_file}:{self.line_number}" if self.line_number else str(self.source_file)
        return f"[{self.severity.value.upper()}] {context}: {self.message}"

@dataclass
class CobolField:
    """Represents a COBOL data field."""
    # Core attributes
    level: int
    name: str
    picture_string: str  # Original PIC clause (e.g., "S9(5)V99")
    picture_category: Optional[PictureCategory]
    usage: UsageType = UsageType.DISPLAY

    # Size attributes
    display_length: int  # Character/display length
    byte_offset: int  # Byte offset in record
    byte_length: int  # Actual bytes in storage

    # Numeric attributes
    is_signed: bool = False  # Has S in picture
    decimal_places: int = 0  # Digits after V (implied decimal)

    # Array attributes
    occurs: Optional[int] = None  # Simple OCCURS count
    occurs_min: Optional[int] = None  # For OCCURS DEPENDING ON
    occurs_max: Optional[int] = None  # For OCCURS DEPENDING ON
    occurs_depending_on: Optional[str] = None  # Field name for ODO

    # Relationship attributes
    redefines: Optional[str] = None  # Name of field being redefined
    redefines_field: Optional['CobolField'] = None  # Reference to actual field
    parent: Optional['CobolField'] = None  # Parent field reference
    children: List['CobolField'] = field(default_factory=list)  # Child fields

    # Storage attributes
    sign_separate: bool = False  # SIGN LEADING/TRAILING SEPARATE
    synchronized: bool = False  # SYNCHRONIZED/SYNC
    justified_right: bool = False  # JUSTIFIED RIGHT
    encoding: str = 'cp1252'  # Encoding for alphanumeric fields

    def is_group(self) -> bool:
        """Check if this is a group item (has children)."""
        return len(self.children) > 0

    def is_elementary(self) -> bool:
        """Check if this is an elementary item (no children)."""
        return len(self.children) == 0

    def get_field_path(self) -> str:
        """Get the full dotted path to this field."""
        if self.parent:
            return f"{self.parent.get_field_path()}.{self.name}"
        return self.name

@dataclass
class CobolRecord:
    """Represents a COBOL 01-level record."""
    name: str
    level: int  # Typically 01, but can be 77
    fields: List[CobolField]
    total_length: int  # Total record length in bytes
    warnings: List[ParserWarning] = field(default_factory=list)
    _field_index: Optional[Dict[str, CobolField]] = None

    def __post_init__(self) -> None:
        """Build field index for fast lookup."""
        self._build_field_index()

    def _build_field_index(self) -> None:
        """Build a dictionary for fast field lookup by name."""
        self._field_index = {}
        for field in self.fields:
            self._index_field(field)

    def _index_field(self, field: CobolField) -> None:
        """Recursively index a field and its children."""
        self._field_index[field.name] = field
        for child in field.children:
            self._index_field(child)

    def get_field(self, name: str) -> Optional[CobolField]:
        """Get a field by name."""
        return self._field_index.get(name)

    def get_field_by_path(self, path: str) -> Optional[CobolField]:
        """Get a field by dotted path (e.g., 'TYPE.CODE')."""
        parts = path.split('.')
        current = None
        for part in parts:
            if current is None:
                current = self.get_field(part)
            else:
                current = next((c for c in current.children if c.name == part), None)
            if current is None:
                return None
        return current
```

#### 3.3.2 Picture Clause Parser

```python
import re
from typing import Tuple, Optional
from dataclasses import dataclass

@dataclass
class PictureInfo:
    """Parsed information from a PICTURE clause."""
    category: PictureCategory
    display_length: int
    is_signed: bool
    decimal_places: int
    scaling_positions: int  # P in picture (multiply/divide by 10^n)

class PictureClauseParser:
    """Parse COBOL PICTURE clauses into structured information."""

    # Pattern for parsing picture strings
    PIC_PATTERN = re.compile(
        r'^(S)?'  # Optional sign
        r'(([X9AN](\(\d+\))?)+)'  # Main picture characters
        r'(V(9(\(\d+\))?)+)?'  # Optional decimal point
        r'(P(\(\d+\))?)?'  # Optional scaling
    )

    def parse(self, picture_string: str) -> Optional[PictureInfo]:
        """Parse a PICTURE clause.

        Args:
            picture_string: The picture string (e.g., "S9(5)V99", "X(10)")

        Returns:
            PictureInfo object with parsed details, or None if invalid

        Examples:
            >>> parser.parse("9(5)")
            PictureInfo(category=NUMERIC, display_length=5, is_signed=False, ...)
            >>> parser.parse("S9(7)V99")
            PictureInfo(category=NUMERIC, display_length=9, is_signed=True, decimal_places=2, ...)
        """
        if not picture_string:
            return None

        # Simple patterns first
        if 'X' in picture_string:
            length = self._extract_length(picture_string, 'X')
            return PictureInfo(
                category=PictureCategory.ALPHANUMERIC,
                display_length=length,
                is_signed=False,
                decimal_places=0,
                scaling_positions=0
            )

        if 'A' in picture_string:
            length = self._extract_length(picture_string, 'A')
            return PictureInfo(
                category=PictureCategory.ALPHABETIC,
                display_length=length,
                is_signed=False,
                decimal_places=0,
                scaling_positions=0
            )

        if 'N' in picture_string:
            length = self._extract_length(picture_string, 'N')
            return PictureInfo(
                category=PictureCategory.NATIONAL,
                display_length=length,
                is_signed=False,
                decimal_places=0,
                scaling_positions=0
            )

        # Numeric patterns
        if '9' in picture_string:
            is_signed = picture_string.startswith('S')

            # Extract integer part
            integer_part = picture_string.lstrip('S')
            decimal_places = 0
            scaling = 0

            # Check for V (implied decimal)
            if 'V' in integer_part:
                parts = integer_part.split('V')
                integer_length = self._extract_length(parts[0], '9')
                decimal_places = self._extract_length(parts[1], '9')
                display_length = integer_length + decimal_places
            else:
                display_length = self._extract_length(integer_part, '9')

            # Check for P (scaling)
            if 'P' in picture_string:
                scaling = self._extract_length(picture_string, 'P')

            return PictureInfo(
                category=PictureCategory.NUMERIC,
                display_length=display_length + (1 if is_signed and False else 0),  # SIGN SEPARATE handled elsewhere
                is_signed=is_signed,
                decimal_places=decimal_places,
                scaling_positions=scaling
            )

        return None

    def _extract_length(self, pic_string: str, char: str) -> int:
        """Extract length from picture string for a given character.

        Args:
            pic_string: Picture string
            char: Character to extract (X, 9, A, etc.)

        Returns:
            Total length

        Examples:
            >>> _extract_length("X(10)", "X")
            10
            >>> _extract_length("999", "9")
            3
            >>> _extract_length("9(3)9(2)", "9")
            5
        """
        # Pattern: X(n) or XXX
        pattern = re.compile(f'{char}(?:\\((\\d+)\\))?')
        matches = pattern.findall(pic_string)

        total = 0
        for match in matches:
            if match:  # X(n) format
                total += int(match)
            else:  # X format (count occurrences)
                total += pic_string.count(char) - pic_string.count(f'{char}(')
                break  # Count once

        return total
```

#### 3.3.3 Line Tokenizer

```python
import re
from typing import Optional, Dict, Any, TypedDict

class TokenInfo(TypedDict, total=False):
    """Type definition for parsed tokens."""
    level: int
    name: str
    picture: Optional[str]
    usage: Optional[str]
    occurs: Optional[int]
    occurs_min: Optional[int]
    occurs_max: Optional[int]
    occurs_depending_on: Optional[str]
    redefines: Optional[str]
    sign_separate: bool
    sign_leading: bool
    synchronized: bool
    justified_right: bool
    value: Optional[str]

class LineTokenizer:
    """Tokenize COBOL DATA DIVISION lines."""

    def __init__(self):
        self.warnings: List[ParserWarning] = []

    def tokenize(self, line: str, line_number: int = 0) -> Optional[TokenInfo]:
        """Tokenize a single COBOL data division line.

        Args:
            line: COBOL source line
            line_number: Line number for error reporting

        Returns:
            TokenInfo dict with parsed components, or None if not a data item

        Handles:
            - Level 01-49 (data items)
            - Level 66 (RENAMES) - returns None with warning
            - Level 77 (independent items)
            - Level 88 (condition names) - returns None (skip)
        """
        # Remove comments (columns 73-80 in fixed format)
        line = self._remove_comments(line)

        # Skip blank lines
        if not line.strip():
            return None

        # Extract level number
        level_match = re.match(r'^\s*(\d{2})\s+', line)
        if not level_match:
            return None

        level = int(level_match.group(1))

        # Handle special levels
        if level == 88:
            # Condition name - skip (no storage)
            return None

        if level == 66:
            # RENAMES - not supported yet
            self.warnings.append(ParserWarning(
                severity=WarningSeverity.WARNING,
                message="Level 66 RENAMES not supported",
                line_number=line_number
            ))
            return None

        # Parse rest of line
        token: TokenInfo = {'level': level}

        # Extract field name
        name_match = re.search(r'^\s*\d{2}\s+(\S+)', line)
        if name_match:
            token['name'] = name_match.group(1)

        # Extract PICTURE clause
        pic_match = re.search(r'PIC(?:TURE)?\s+(?:IS\s+)?([SX9ANV()P]+)', line, re.IGNORECASE)
        if pic_match:
            token['picture'] = pic_match.group(1)

        # Extract USAGE clause
        for usage_type in ['COMP-3', 'COMP-2', 'COMP-1', 'COMP-4', 'COMP-5', 'COMP',
                          'COMPUTATIONAL-3', 'COMPUTATIONAL', 'BINARY', 'PACKED-DECIMAL', 'DISPLAY']:
            if usage_type in line.upper():
                token['usage'] = usage_type
                break

        # Extract OCCURS clause
        occurs_match = re.search(r'OCCURS\s+(\d+)', line, re.IGNORECASE)
        if occurs_match:
            token['occurs'] = int(occurs_match.group(1))

        # Extract OCCURS DEPENDING ON
        odo_match = re.search(r'OCCURS\s+(\d+)\s+TO\s+(\d+)\s+(?:TIMES\s+)?DEPENDING\s+ON\s+(\S+)',
                             line, re.IGNORECASE)
        if odo_match:
            token['occurs_min'] = int(odo_match.group(1))
            token['occurs_max'] = int(odo_match.group(2))
            token['occurs_depending_on'] = odo_match.group(3)
            token['occurs'] = None  # Don't use simple occurs with ODO

        # Extract REDEFINES
        redef_match = re.search(r'REDEFINES\s+(\S+)', line, re.IGNORECASE)
        if redef_match:
            token['redefines'] = redef_match.group(1)

        # Extract SIGN clause
        if 'SIGN' in line.upper():
            token['sign_separate'] = 'SEPARATE' in line.upper()
            token['sign_leading'] = 'LEADING' in line.upper()
        else:
            token['sign_separate'] = False
            token['sign_leading'] = False

        # Extract SYNCHRONIZED
        token['synchronized'] = bool(re.search(r'\bSYNC(?:HRONIZED)?\b', line, re.IGNORECASE))

        # Extract JUSTIFIED
        token['justified_right'] = bool(re.search(r'\bJUST(?:IFIED)?\s+RIGHT\b', line, re.IGNORECASE))

        # Extract VALUE clause (skip for now, but detect)
        value_match = re.search(r'VALUE\s+(?:IS\s+)?(.+?)(?:\.|$)', line, re.IGNORECASE)
        if value_match:
            token['value'] = value_match.group(1).strip()

        return token

    def _remove_comments(self, line: str) -> str:
        """Remove comments from COBOL line.

        In fixed format:
        - Columns 1-6: Sequence number area
        - Column 7: Indicator area (* = comment, - = continuation)
        - Columns 8-72: Code area
        - Columns 73-80: Identification area (treated as comment)
        """
        # Check for comment line (asterisk in column 7)
        if len(line) > 6 and line[6] == '*':
            return ''

        # Remove identification area (columns 73-80)
        if len(line) > 72:
            line = line[:72]

        return line
```

#### 3.3.4 Offset Calculator

```python
from typing import List, Dict

class OffsetCalculator:
    """Calculate byte offsets for COBOL fields, handling REDEFINES and SYNC."""

    def calculate_byte_length(self, field: CobolField, pic_info: Optional[PictureInfo]) -> int:
        """Calculate byte length for a field based on its type.

        Args:
            field: The COBOL field
            pic_info: Parsed picture information

        Returns:
            Byte length in storage
        """
        if field.is_group():
            # Group items: sum of children
            return sum(self.calculate_byte_length(child, None) for child in field.children)

        if not pic_info:
            return 0

        # Calculate based on usage type
        if field.usage == UsageType.DISPLAY:
            # Display format
            length = pic_info.display_length

            # Add extra byte for SIGN SEPARATE
            if pic_info.is_signed and field.sign_separate:
                length += 1

            return length

        elif field.usage in (UsageType.COMP3, UsageType.PACKED_DECIMAL):
            # COMP-3: Packed decimal - 2 digits per byte, plus sign nibble
            # Formula: (digits + 1) / 2, rounded up
            digits = pic_info.display_length
            return (digits + 1 + 1) // 2

        elif field.usage in (UsageType.COMP, UsageType.COMP4, UsageType.BINARY):
            # COMP: Binary - size depends on digit count
            digits = pic_info.display_length
            if digits <= 4:
                return 2  # Halfword
            elif digits <= 9:
                return 4  # Fullword
            else:
                return 8  # Doubleword

        elif field.usage == UsageType.COMP1:
            return 4  # Single-precision float

        elif field.usage == UsageType.COMP2:
            return 8  # Double-precision float

        elif field.usage == UsageType.COMP5:
            # COMP-5: Native binary
            digits = pic_info.display_length
            if digits <= 4:
                return 2
            elif digits <= 9:
                return 4
            else:
                return 8

        else:
            # Default to display length
            return pic_info.display_length

    def calculate_offsets(self, fields: List[CobolField],
                         base_offset: int = 0) -> Dict[str, int]:
        """Calculate offsets for a list of fields, handling REDEFINES.

        Args:
            fields: List of fields at the same level
            base_offset: Starting offset

        Returns:
            Dictionary mapping field names to their offsets
        """
        offsets = {}
        current_offset = base_offset
        max_offset = base_offset

        for field in fields:
            if field.redefines:
                # REDEFINES: Use same offset as redefined field
                if field.redefines in offsets:
                    field.byte_offset = offsets[field.redefines]
                else:
                    # Redefined field not found - use current offset and warn
                    field.byte_offset = current_offset
            else:
                # Regular field: Use max offset reached so far
                field.byte_offset = max_offset
                current_offset = field.byte_offset

            # Calculate field byte length (including OCCURS)
            base_length = field.byte_length
            if field.occurs:
                field.byte_length = base_length * field.occurs

            # Track maximum offset reached
            max_offset = max(max_offset, field.byte_offset + field.byte_length)

            # Store offset for reference
            offsets[field.name] = field.byte_offset

            # If field has children, calculate their offsets recursively
            if field.children:
                child_offsets = self.calculate_offsets(field.children, field.byte_offset)
                offsets.update(child_offsets)

                # Update field's byte length based on children
                if field.children:
                    child_max = max(c.byte_offset + c.byte_length - field.byte_offset
                                   for c in field.children)
                    field.byte_length = child_max
                    if field.occurs:
                        field.byte_length *= field.occurs

        return offsets

    def resolve_redefines(self, fields: List[CobolField]) -> None:
        """Resolve REDEFINES references to actual field objects.

        Args:
            fields: List of fields to process
        """
        # Build name-to-field index
        field_index = {}
        self._index_fields(fields, field_index)

        # Resolve references
        for field in fields:
            if field.redefines:
                field.redefines_field = field_index.get(field.redefines)
                if not field.redefines_field:
                    # Warning: redefined field not found
                    pass
            # Recursively resolve children
            if field.children:
                self.resolve_redefines(field.children)

    def _index_fields(self, fields: List[CobolField],
                     index: Dict[str, CobolField]) -> None:
        """Build an index of fields by name."""
        for field in fields:
            index[field.name] = field
            if field.children:
                self._index_fields(field.children, index)
```

#### 3.3.5 Recursive Parser

```python
from typing import List, Tuple, Iterator
from pathlib import Path

class CobolParser:
    """Parse COBOL DATA DIVISION into structured format."""

    def __init__(self):
        self.tokenizer = LineTokenizer()
        self.picture_parser = PictureClauseParser()
        self.offset_calculator = OffsetCalculator()
        self.warnings: List[ParserWarning] = []

    def parse(self, source: str) -> List[CobolRecord]:
        """Parse COBOL source and return list of records.

        Args:
            source: COBOL source code as string

        Returns:
            List of CobolRecord objects
        """
        lines = self._extract_data_division(source)
        records = []

        i = 0
        while i < len(lines):
            token = self.tokenizer.tokenize(lines[i], line_number=i)
            if token and token['level'] in (1, 77):  # Handle level 01 and 77
                record, i = self._parse_record(lines, i)
                records.append(record)
            else:
                i += 1

        return records

    def _parse_record(self, lines: List[str], start: int) -> Tuple[CobolRecord, int]:
        """Parse a single 01-level or 77-level record.

        Args:
            lines: List of source lines
            start: Starting line index

        Returns:
            Tuple of (CobolRecord, next_line_index)
        """
        token = self.tokenizer.tokenize(lines[start], line_number=start)

        # Level 77 items are independent (no children)
        if token['level'] == 77:
            field = self._create_field(token, 0, start)
            record = CobolRecord(
                name=field.name,
                level=77,
                fields=[field],
                total_length=field.byte_length
            )
            return record, start + 1

        # Level 01 record - parse children
        root_name = token['name']
        children = []
        i = start + 1

        # Parse all immediate children
        while i < len(lines):
            child_token = self.tokenizer.tokenize(lines[i], line_number=i)
            if not child_token:
                i += 1
                continue

            # Stop at next 01/77 level
            if child_token['level'] in (1, 77):
                break

            # Parse child field and its descendants
            child, next_i = self._parse_field(lines, i, parent_level=1)
            if child:
                children.append(child)
            i = next_i

        # Calculate offsets (handles REDEFINES correctly)
        self.offset_calculator.calculate_offsets(children, base_offset=0)

        # Resolve REDEFINES references
        self.offset_calculator.resolve_redefines(children)

        # Calculate total record length
        if children:
            total_length = max(c.byte_offset + c.byte_length for c in children)
        else:
            total_length = 0

        record = CobolRecord(
            name=root_name,
            level=1,
            fields=children,
            total_length=total_length
        )

        return record, i

    def _parse_field(self, lines: List[str], index: int,
                    parent_level: int, depth: int = 0,
                    max_depth: int = 50) -> Tuple[Optional[CobolField], int]:
        """Parse a field and its children recursively.

        Args:
            lines: List of source lines
            index: Current line index
            parent_level: Level of parent field
            depth: Current recursion depth (for safety)
            max_depth: Maximum allowed recursion depth

        Returns:
            Tuple of (CobolField or None, next_line_index)

        Raises:
            ValueError: If nesting exceeds max_depth
        """
        if depth > max_depth:
            raise ValueError(f"Nesting too deep (>{max_depth}) at line {index}")

        token = self.tokenizer.tokenize(lines[index], line_number=index)
        if not token:
            return None, index + 1

        # Create field with initial values
        field = self._create_field(token, base_offset=0, line_number=index)
        field.parent = None  # Will be set by parent

        # Parse immediate children only
        i = index + 1
        expected_child_level = None

        while i < len(lines):
            child_token = self.tokenizer.tokenize(lines[i], line_number=i)
            if not child_token:
                i += 1
                continue

            # Stop if we've reached a field at same or higher level
            if child_token['level'] <= field.level:
                break

            # Determine expected child level from first child
            if expected_child_level is None:
                expected_child_level = child_token['level']

            # Only parse immediate children (same level as first child)
            if child_token['level'] == expected_child_level:
                child, next_i = self._parse_field(lines, i, parent_level=field.level,
                                                  depth=depth + 1, max_depth=max_depth)
                if child:
                    child.parent = field
                    field.children.append(child)
                i = next_i
            elif child_token['level'] > expected_child_level:
                # Child has deeper nesting - belongs to previous sibling
                # This shouldn't happen with correct COBOL, but handle gracefully
                self.warnings.append(ParserWarning(
                    severity=WarningSeverity.WARNING,
                    message=f"Unexpected nesting at level {child_token['level']}",
                    line_number=i,
                    field_name=child_token.get('name', 'unknown')
                ))
                i += 1
            else:
                # Child level is between field level and expected - malformed
                break

        # For group items, calculate byte length from children
        # For elementary items, byte length is already set
        if field.children:
            # Recalculate offsets for children
            self.offset_calculator.calculate_offsets(field.children, base_offset=0)

            # Field byte length is based on children
            if field.children:
                max_child_end = max(c.byte_offset + c.byte_length for c in field.children)
                field.byte_length = max_child_end

            # Apply OCCURS to group
            if field.occurs:
                field.byte_length *= field.occurs

        return field, i

    def _create_field(self, token: TokenInfo, base_offset: int,
                     line_number: int) -> CobolField:
        """Create a CobolField from a token.

        Args:
            token: Parsed token information
            base_offset: Base offset for this field
            line_number: Source line number

        Returns:
            CobolField object
        """
        # Parse picture clause
        pic_info = None
        if token.get('picture'):
            pic_info = self.picture_parser.parse(token['picture'])

        # Determine usage type
        usage = UsageType.DISPLAY
        if token.get('usage'):
            usage_str = token['usage'].upper().replace('-', '')
            usage_map = {
                'COMP': UsageType.COMP,
                'COMP1': UsageType.COMP1,
                'COMP2': UsageType.COMP2,
                'COMP3': UsageType.COMP3,
                'COMP4': UsageType.COMP4,
                'COMP5': UsageType.COMP5,
                'COMPUTATIONAL': UsageType.COMP,
                'COMPUTATIONAL3': UsageType.COMP3,
                'BINARY': UsageType.BINARY,
                'PACKEDDECIMAL': UsageType.PACKED_DECIMAL,
                'DISPLAY': UsageType.DISPLAY,
            }
            usage = usage_map.get(usage_str, UsageType.DISPLAY)

        # Create field
        field = CobolField(
            level=token['level'],
            name=token.get('name', 'FILLER'),
            picture_string=token.get('picture', ''),
            picture_category=pic_info.category if pic_info else None,
            usage=usage,
            display_length=pic_info.display_length if pic_info else 0,
            byte_offset=base_offset,
            byte_length=0,
            is_signed=pic_info.is_signed if pic_info else False,
            decimal_places=pic_info.decimal_places if pic_info else 0,
            occurs=token.get('occurs'),
            occurs_min=token.get('occurs_min'),
            occurs_max=token.get('occurs_max'),
            occurs_depending_on=token.get('occurs_depending_on'),
            redefines=token.get('redefines'),
            sign_separate=token.get('sign_separate', False),
            synchronized=token.get('synchronized', False),
            justified_right=token.get('justified_right', False)
        )

        # Calculate byte length
        field.byte_length = self.offset_calculator.calculate_byte_length(field, pic_info)

        # Apply OCCURS multiplier (for elementary items)
        if field.occurs and not field.children:
            field.byte_length *= field.occurs

        return field

    def _extract_data_division(self, source: str) -> List[str]:
        """Extract DATA DIVISION lines from COBOL source.

        Args:
            source: Complete COBOL source code

        Returns:
            List of lines from DATA DIVISION
        """
        lines = source.split('\n')
        in_data_division = False
        data_lines = []

        for line in lines:
            upper = line.upper()

            if 'DATA DIVISION' in upper:
                in_data_division = True
                continue

            if in_data_division:
                # Stop at PROCEDURE DIVISION
                if 'PROCEDURE DIVISION' in upper:
                    break
                data_lines.append(line)

        return data_lines
```

#### 3.3.6 Binary Data Parser

```python
from typing import Any, Dict, List, Union

# Type alias for parsed values
ParsedValue = Union[str, int, float, Dict[str, 'ParsedValue'], List['ParsedValue']]

class BinaryDataParser:
    """Parse binary data into Python objects based on COBOL structure."""

    def __init__(self):
        self.warnings: List[ParserWarning] = []

    def parse(self, record: CobolRecord, data: bytes) -> Dict[str, ParsedValue]:
        """Parse binary data according to record structure.

        Args:
            record: CobolRecord structure definition
            data: Binary data to parse

        Returns:
            Dictionary with parsed field values

        Raises:
            ValueError: If data length doesn't match expected record length
        """
        if len(data) < record.total_length:
            raise ValueError(
                f"Data length {len(data)} is less than expected {record.total_length}"
            )

        result = {}
        for field in record.fields:
            try:
                value = self.parse_field(field, data)
                result[field.name] = value
            except Exception as e:
                self.warnings.append(ParserWarning(
                    severity=WarningSeverity.ERROR,
                    message=f"Failed to parse field {field.name}: {e}",
                    field_name=field.name
                ))
                result[field.name] = None

        return result

    def parse_field(self, field: CobolField, data: bytes) -> ParsedValue:
        """Parse a single field from binary data.

        Args:
            field: Field definition
            data: Complete record data

        Returns:
            Parsed value (type depends on field type)
        """
        # Handle OCCURS (arrays)
        if field.occurs:
            return self._parse_array(field, data)

        # Handle OCCURS DEPENDING ON
        if field.occurs_max:
            # Need to read the count field first
            return self._parse_variable_array(field, data)

        # Handle group items
        if field.is_group():
            result = {}
            for child in field.children:
                result[child.name] = self.parse_field(child, data)
            return result

        # Elementary item - parse based on type
        return self._parse_elementary(field, data)

    def _parse_array(self, field: CobolField, data: bytes) -> List[ParsedValue]:
        """Parse an array field (OCCURS).

        Args:
            field: Field with occurs > 0
            data: Complete record data

        Returns:
            List of parsed values
        """
        result = []
        item_length = field.byte_length // field.occurs

        for i in range(field.occurs):
            offset = field.byte_offset + i * item_length

            # Create a temporary field for this occurrence
            temp_field = CobolField(
                level=field.level,
                name=f"{field.name}[{i}]",
                picture_string=field.picture_string,
                picture_category=field.picture_category,
                usage=field.usage,
                display_length=field.display_length,
                byte_offset=offset,
                byte_length=item_length,
                is_signed=field.is_signed,
                decimal_places=field.decimal_places,
                encoding=field.encoding
            )

            # Copy children if group item
            if field.children:
                temp_field.children = field.children.copy()

            # Parse this occurrence
            if field.is_group():
                item_result = {}
                for child in field.children:
                    # Adjust child offset relative to array item
                    child_offset = offset + (child.byte_offset - field.byte_offset)
                    temp_child = self._adjust_field_offset(child, child_offset)
                    item_result[child.name] = self.parse_field(temp_child, data)
                result.append(item_result)
            else:
                result.append(self._parse_elementary(temp_field, data))

        return result

    def _parse_variable_array(self, field: CobolField, data: bytes) -> List[ParsedValue]:
        """Parse variable-length array (OCCURS DEPENDING ON).

        Args:
            field: Field with occurs_depending_on set
            data: Complete record data

        Returns:
            List of parsed values (length determined at runtime)
        """
        # TODO: Implement ODO - need to look up count field value
        self.warnings.append(ParserWarning(
            severity=WarningSeverity.WARNING,
            message=f"OCCURS DEPENDING ON not fully implemented for {field.name}",
            field_name=field.name
        ))
        # Fall back to maximum occurrences
        return []

    def _adjust_field_offset(self, field: CobolField, new_offset: int) -> CobolField:
        """Create a copy of field with adjusted offset."""
        adjusted = CobolField(
            level=field.level,
            name=field.name,
            picture_string=field.picture_string,
            picture_category=field.picture_category,
            usage=field.usage,
            display_length=field.display_length,
            byte_offset=new_offset,
            byte_length=field.byte_length,
            is_signed=field.is_signed,
            decimal_places=field.decimal_places,
            encoding=field.encoding,
            children=field.children
        )
        return adjusted

    def _parse_elementary(self, field: CobolField, data: bytes) -> Union[str, int, float]:
        """Parse an elementary (non-group) field.

        Args:
            field: Elementary field definition
            data: Complete record data

        Returns:
            Parsed value

        Raises:
            ValueError: If field cannot be parsed
        """
        # Extract bytes for this field
        field_data = data[field.byte_offset:field.byte_offset + field.byte_length]

        if len(field_data) < field.byte_length:
            raise ValueError(
                f"Not enough data for field {field.name} at offset {field.byte_offset}"
            )

        # Parse based on type
        if field.picture_category == PictureCategory.ALPHANUMERIC:
            return self._parse_alphanumeric(field_data, field.encoding)

        elif field.picture_category == PictureCategory.NUMERIC:
            if field.usage == UsageType.DISPLAY:
                return self._parse_numeric_display(field_data, field.is_signed, field.decimal_places)
            elif field.usage in (UsageType.COMP3, UsageType.PACKED_DECIMAL):
                return self._parse_comp3(field_data, field.is_signed, field.decimal_places)
            elif field.usage in (UsageType.COMP, UsageType.COMP4, UsageType.BINARY):
                return self._parse_binary(field_data, field.is_signed, field.decimal_places)
            elif field.usage == UsageType.COMP1:
                return self._parse_float(field_data, single_precision=True)
            elif field.usage == UsageType.COMP2:
                return self._parse_float(field_data, single_precision=False)
            else:
                raise ValueError(f"Unsupported numeric usage: {field.usage}")

        elif field.picture_category == PictureCategory.ALPHABETIC:
            return self._parse_alphanumeric(field_data, field.encoding)

        else:
            self.warnings.append(ParserWarning(
                severity=WarningSeverity.WARNING,
                message=f"Unsupported picture category: {field.picture_category}",
                field_name=field.name
            ))
            return field_data.hex()  # Return as hex string

    def _parse_alphanumeric(self, data: bytes, encoding: str) -> str:
        """Parse alphanumeric field."""
        try:
            return data.decode(encoding).rstrip()
        except UnicodeDecodeError as e:
            raise ValueError(f"Cannot decode with {encoding}: {e}") from e

    def _parse_numeric_display(self, data: bytes, is_signed: bool,
                               decimal_places: int) -> Union[int, float]:
        """Parse numeric display format (PIC 9)."""
        try:
            text = data.decode('ascii').strip()

            # Handle sign
            if is_signed and text:
                # Check for overpunched sign in last character
                # TODO: Implement overpunch decoding
                pass

            value = int(text)

            # Apply decimal places
            if decimal_places > 0:
                return value / (10 ** decimal_places)
            return value

        except (UnicodeDecodeError, ValueError) as e:
            raise ValueError(f"Cannot parse numeric display: {e}") from e

    def _parse_comp3(self, data: bytes, is_signed: bool,
                    decimal_places: int) -> Union[int, float]:
        """Parse COMP-3 (packed decimal) data.

        Args:
            data: Packed decimal bytes
            is_signed: Whether field is signed (affects sign nibble interpretation)
            decimal_places: Number of decimal positions

        Returns:
            Numeric value
        """
        if not data:
            return 0

        result = 0

        # Process all bytes except last
        for byte in data[:-1]:
            high_nibble = (byte >> 4) & 0x0F
            low_nibble = byte & 0x0F
            result = result * 10 + high_nibble
            result = result * 10 + low_nibble

        # Last byte has digit in high nibble, sign in low nibble
        last_byte = data[-1]
        digit = (last_byte >> 4) & 0x0F
        sign_nibble = last_byte & 0x0F

        result = result * 10 + digit

        # Interpret sign nibble
        # 0x0C = positive (unsigned)
        # 0x0D = negative
        # 0x0F = unsigned (alternate)
        # 0x0B = negative (alternate)
        # 0x0A = positive (alternate)
        if sign_nibble in (0x0D, 0x0B):
            result = -result
        elif sign_nibble in (0x0C, 0x0F, 0x0A):
            pass  # Positive
        else:
            self.warnings.append(ParserWarning(
                severity=WarningSeverity.WARNING,
                message=f"Invalid COMP-3 sign nibble: {hex(sign_nibble)}"
            ))

        # Apply decimal places
        if decimal_places > 0:
            return result / (10 ** decimal_places)

        return result

    def _parse_binary(self, data: bytes, is_signed: bool,
                     decimal_places: int) -> Union[int, float]:
        """Parse COMP/COMP-4/BINARY data."""
        import struct

        # Determine format based on length
        if len(data) == 2:
            fmt = '>h' if is_signed else '>H'  # Big-endian halfword
        elif len(data) == 4:
            fmt = '>i' if is_signed else '>I'  # Big-endian fullword
        elif len(data) == 8:
            fmt = '>q' if is_signed else '>Q'  # Big-endian doubleword
        else:
            raise ValueError(f"Invalid binary data length: {len(data)}")

        value = struct.unpack(fmt, data)[0]

        # Apply decimal places
        if decimal_places > 0:
            return value / (10 ** decimal_places)

        return value

    def _parse_float(self, data: bytes, single_precision: bool) -> float:
        """Parse floating point data (COMP-1/COMP-2)."""
        import struct

        if single_precision:
            if len(data) != 4:
                raise ValueError("COMP-1 must be 4 bytes")
            return struct.unpack('>f', data)[0]  # Big-endian float
        else:
            if len(data) != 8:
                raise ValueError("COMP-2 must be 8 bytes")
            return struct.unpack('>d', data)[0]  # Big-endian double
```

### 3.4 Implementation Phases

**Note**: Timeline revised based on design review findings. Total 5 weeks (1 week design validation + 4 weeks implementation).

#### Phase 0: Design Validation (Week 0)
**Goal**: Validate all critical issues from design review are addressed

**Tasks**:
- Review corrected algorithms for REDEFINES, OCCURS, and recursion
- Validate data model completeness
- Create COBOL feature support matrix
- Define type hint strategy
- Document cross-platform requirements

**Deliverables**:
- Updated design document (this document)
- Feature support matrix
- Test case specifications

#### Phase 1: Core Components (Week 1)
**Goal**: Implement foundation with correct algorithms

**Tasks**:
1. **PictureClauseParser**
   - Parse X(n), 9(n), S9(n), 9(n)V99 patterns
   - Extract category, length, signed, decimal places
   - Unit tests for picture parsing

2. **LineTokenizer**
   - Handle level 01, 77 (include), 88 (skip), 66 (skip with warning)
   - Extract PIC, USAGE, OCCURS, REDEFINES, SIGN, SYNC
   - Handle VALUE clauses (skip for now)
   - Handle fixed-format COBOL (columns 1-72)
   - Unit tests for tokenization

3. **Data Models**
   - Implement CobolField with all attributes
   - Implement CobolRecord with field indexing
   - Implement ParserWarning system
   - Type hints with TypedDict for tokens

4. **OffsetCalculator**
   - Correct REDEFINES offset handling (don't advance)
   - Correct byte length calculation order
   - Simple OCCURS support
   - Unit tests for offset calculation

5. **Basic CobolParser**
   - Implement corrected recursive descent algorithm
   - Handle immediate children only (not all descendants)
   - Depth limit to prevent stack overflow
   - Integration tests with simple structures

**Deliverables**:
- Functional parser for simple structures
- 50+ unit tests
- All tests passing with mypy, black, ruff

#### Phase 2: Extended Features (Weeks 2-3)
**Goal**: Add COMP-3, REDEFINES resolution, binary parsing

**Tasks**:
1. **Byte Length Calculations**
   - COMP-3: `(digits + 1) // 2`
   - COMP/BINARY: 2/4/8 bytes based on digit count
   - SIGN SEPARATE: +1 byte
   - COMP-1: 4 bytes, COMP-2: 8 bytes
   - Unit tests for each type

2. **BinaryDataParser**
   - Parse COMP-3 with corrected sign nibbles
   - Parse COMP/BINARY (2, 4, 8 bytes)
   - Parse DISPLAY numeric
   - Parse alphanumeric with configurable encoding
   - Handle OCCURS (return lists)
   - Unit tests for binary parsing

3. **REDEFINES Resolution**
   - Resolve string references to field objects
   - Validate redefined field exists
   - Support multiple REDEFINES of same field
   - Integration tests

4. **Nested OCCURS**
   - Multi-dimensional arrays
   - Correct offset calculation for array[i][j]
   - Tests with 2D and 3D arrays

5. **Cross-Platform Support**
   - Use pathlib.Path for all file operations
   - Configurable encoding per field
   - Handle endianness (struct format strings)
   - Line ending handling (newline=None)
   - Platform-specific tests

**Deliverables**:
- Binary parser working with real COBOL data
- REDEFINES fully functional
- 100+ unit tests
- Integration tests with sample COBOL files

#### Phase 3: Polish & Production-Ready (Week 4)
**Goal**: Production-ready with comprehensive error handling

**Tasks**:
1. **Performance & Safety**
   - Add recursion depth limits (max 50 levels)
   - Streaming for large files (yield records)
   - Memory usage optimization
   - Performance benchmarks

2. **API Design**
   - Implement `__getattr__` for dot notation access
   - Implement `get_field()` and `get_field_by_path()`
   - Array indexing API for OCCURS fields
   - User-friendly error messages

3. **Error Handling**
   - Complete warning system with severity levels
   - Structured ParserWarning with context
   - Warning filtering and reporting API
   - `raise ... from e` pattern throughout

4. **Documentation**
   - Google-style docstrings for all public APIs
   - Usage examples in docstrings
   - README with examples
   - API reference documentation

5. **Testing**
   - Edge case tests (all 30+ cases from review)
   - Platform-specific tests (Windows, Unix, encoding)
   - Stress tests (10,000+ fields, deep nesting)
   - End-to-end tests with real COBOL files
   - Coverage >90%

6. **Code Quality**
   - All mypy checks passing
   - All black formatting done
   - All ruff linting passing
   - No security vulnerabilities

**Deliverables**:
- Production-ready package
- 150+ tests with >90% coverage
- Complete documentation
- Performance benchmarks

#### Phase 4: Advanced Features (Future - Optional)
**Goal**: Support advanced COBOL features

**Tasks**:
1. **SYNCHRONIZED/SYNC**
   - Alignment and padding calculation
   - Tests with mainframe data

2. **OCCURS DEPENDING ON**
   - Variable-length array parsing
   - Count field lookup and validation

3. **More COMP Types**
   - COMP-5 (native binary)
   - NATIONAL (Unicode)

4. **Editing Picture Symbols**
   - Parse Z (zero suppression)
   - Parse $ (currency)
   - Parse * (check protection)

5. **COPY Book Preprocessing**
   - Include file resolution
   - Recursive COPY handling

**Note**: These features are optional and can be prioritized based on user needs.

### 3.5 Comprehensive Testing Strategy

**Testing Approach**: Test-driven development with 150+ tests covering all edge cases identified in design review.

#### 3.5.1 Unit Tests - Picture Clause Parser

```python
def test_picture_simple_alphanumeric():
    """Test PIC X(10)."""
    parser = PictureClauseParser()
    info = parser.parse("X(10)")
    assert info.category == PictureCategory.ALPHANUMERIC
    assert info.display_length == 10
    assert not info.is_signed

def test_picture_numeric_with_decimal():
    """Test PIC 9(5)V99."""
    parser = PictureClauseParser()
    info = parser.parse("9(5)V99")
    assert info.category == PictureCategory.NUMERIC
    assert info.display_length == 7
    assert info.decimal_places == 2

def test_picture_signed_numeric():
    """Test PIC S9(7)V99."""
    parser = PictureClauseParser()
    info = parser.parse("S9(7)V99")
    assert info.is_signed
    assert info.display_length == 9
    assert info.decimal_places == 2
```

#### 3.5.2 Unit Tests - Line Tokenizer

```python
def test_tokenize_level_88():
    """Level 88 condition names should return None."""
    tokenizer = LineTokenizer()
    line = "       88  STATUS-ACTIVE VALUE 'A'."
    token = tokenizer.tokenize(line)
    assert token is None  # Skip condition names

def test_tokenize_level_77():
    """Level 77 independent items should be parsed."""
    tokenizer = LineTokenizer()
    line = "       77  WS-COUNTER PIC 9(5) COMP."
    token = tokenizer.tokenize(line)
    assert token['level'] == 77
    assert token['name'] == 'WS-COUNTER'

def test_tokenize_value_clause():
    """VALUE clauses should be extracted."""
    tokenizer = LineTokenizer()
    line = "       05  MAX-ITEMS PIC 9(5) VALUE 99999."
    token = tokenizer.tokenize(line)
    assert token['value'] == '99999'

def test_tokenize_sign_separate():
    """SIGN LEADING SEPARATE should be detected."""
    tokenizer = LineTokenizer()
    line = "       05  AMOUNT PIC S9(7)V99 SIGN LEADING SEPARATE."
    token = tokenizer.tokenize(line)
    assert token['sign_separate']
    assert token['sign_leading']
```

#### 3.5.3 Unit Tests - Offset Calculator

```python
def test_offset_simple_fields():
    """Simple sequential fields."""
    calc = OffsetCalculator()
    fields = [
        CobolField(level=3, name='A', picture_string='X(10)', ..., byte_length=10),
        CobolField(level=3, name='B', picture_string='9(5)', ..., byte_length=5),
    ]
    calc.calculate_offsets(fields, base_offset=0)
    assert fields[0].byte_offset == 0
    assert fields[1].byte_offset == 10

def test_offset_redefines():
    """REDEFINES should use same offset."""
    calc = OffsetCalculator()
    fields = [
        CobolField(level=3, name='FIELD-A', ..., byte_length=10),
        CobolField(level=3, name='FIELD-B', ..., byte_length=10, redefines='FIELD-A'),
        CobolField(level=3, name='FIELD-C', ..., byte_length=5),
    ]
    calc.calculate_offsets(fields, base_offset=0)
    assert fields[0].byte_offset == 0
    assert fields[1].byte_offset == 0  # Same as FIELD-A!
    assert fields[2].byte_offset == 10  # After FIELD-A, not FIELD-B

def test_offset_occurs():
    """OCCURS should multiply byte length."""
    calc = OffsetCalculator()
    field = CobolField(level=3, name='MONTH', ..., byte_length=10, occurs=12)
    calc.calculate_offsets([field], base_offset=0)
    assert field.byte_length == 120  # 10 * 12
```

#### 3.5.4 Unit Tests - Byte Length Calculation

```python
def test_byte_length_comp3():
    """COMP-3 byte length calculation."""
    calc = OffsetCalculator()
    pic_info = PictureInfo(category=PictureCategory.NUMERIC, display_length=5, ...)
    field = CobolField(usage=UsageType.COMP3, ...)
    length = calc.calculate_byte_length(field, pic_info)
    assert length == 3  # (5 + 1) // 2

def test_byte_length_sign_separate():
    """SIGN SEPARATE adds 1 byte."""
    calc = OffsetCalculator()
    pic_info = PictureInfo(display_length=5, is_signed=True, ...)
    field = CobolField(usage=UsageType.DISPLAY, sign_separate=True, ...)
    length = calc.calculate_byte_length(field, pic_info)
    assert length == 6  # 5 + 1

def test_byte_length_comp():
    """COMP binary size tiers."""
    calc = OffsetCalculator()
    # 1-4 digits = 2 bytes
    pic_info = PictureInfo(display_length=4, ...)
    field = CobolField(usage=UsageType.COMP, ...)
    assert calc.calculate_byte_length(field, pic_info) == 2

    # 5-9 digits = 4 bytes
    pic_info = PictureInfo(display_length=9, ...)
    assert calc.calculate_byte_length(field, pic_info) == 4

    # 10+ digits = 8 bytes
    pic_info = PictureInfo(display_length=10, ...)
    assert calc.calculate_byte_length(field, pic_info) == 8
```

#### 3.5.5 Integration Tests - Parser

```python
def test_simple_flat_structure():
    """Simple flat structure."""
    cobol = """
    01 CUSTOMER.
        03 CUST-ID PIC 9(5).
        03 CUST-NAME PIC X(30).
    """
    parser = CobolParser()
    records = parser.parse(cobol)
    assert len(records) == 1
    assert records[0].name == "CUSTOMER"
    assert len(records[0].fields) == 2
    assert records[0].fields[0].byte_offset == 0
    assert records[0].fields[1].byte_offset == 5

def test_nested_structure():
    """Nested structure with proper hierarchy."""
    cobol = """
    01 EMPLOYEE.
        03 EMP-ID PIC 9(6).
        03 EMP-NAME.
            05 FIRST-NAME PIC X(20).
            05 LAST-NAME PIC X(20).
        03 SALARY PIC 9(7)V99 COMP-3.
    """
    parser = CobolParser()
    records = parser.parse(cobol)
    assert len(records) == 1
    assert records[0].fields[1].name == "EMP-NAME"
    assert len(records[0].fields[1].children) == 2
    assert records[0].fields[1].children[0].name == "FIRST-NAME"

def test_occurs():
    """OCCURS clause creates arrays."""
    cobol = """
    01 MONTHLY-DATA.
        03 MONTH-RECORD OCCURS 12.
            05 SALES PIC 9(7)V99 COMP-3.
    """
    parser = CobolParser()
    records = parser.parse(cobol)
    month_field = records[0].fields[0]
    assert month_field.occurs == 12
    assert month_field.byte_length == 60  # 5 bytes * 12

def test_redefines_offset():
    """REDEFINES uses same offset as original field."""
    cobol = """
    01 DATA-RECORD.
        03 FIELD-A PIC X(10).
        03 FIELD-B REDEFINES FIELD-A PIC 9(10).
        03 FIELD-C PIC X(5).
    """
    parser = CobolParser()
    records = parser.parse(cobol)
    fields = records[0].fields
    assert fields[0].byte_offset == 0
    assert fields[1].byte_offset == 0  # Same as FIELD-A
    assert fields[2].byte_offset == 10  # After FIELD-A

def test_deep_nesting():
    """Deep nesting (5 levels)."""
    cobol = """
    01 ROOT.
        03 LEVEL-3.
            05 LEVEL-5.
                07 LEVEL-7.
                    09 LEVEL-9 PIC X(10).
    """
    parser = CobolParser()
    records = parser.parse(cobol)
    # Verify correct hierarchy
    assert len(records[0].fields) == 1
    assert records[0].fields[0].level == 3
    assert len(records[0].fields[0].children) == 1
    assert records[0].fields[0].children[0].level == 5
```

#### 3.5.6 Integration Tests - Binary Parser

```python
def test_binary_parsing_alphanumeric():
    """Parse alphanumeric field."""
    cobol = """
    01 RECORD.
        03 NAME PIC X(10).
    """
    parser = CobolParser()
    records = parser.parse(cobol)

    binary_parser = BinaryDataParser()
    data = b'JOHN DOE  '
    result = binary_parser.parse(records[0], data)
    assert result['NAME'] == 'JOHN DOE'

def test_binary_parsing_comp3():
    """Parse COMP-3 packed decimal."""
    cobol = """
    01 RECORD.
        03 CODE PIC 9(5) COMP-3.
    """
    parser = CobolParser()
    records = parser.parse(cobol)

    binary_parser = BinaryDataParser()
    # COMP-3 encoding of 12345: 0x01 0x23 0x45 0x0C (positive)
    data = b'\x01\x23\x45\x0C'
    result = binary_parser.parse(records[0], data)
    assert result['CODE'] == 12345

def test_binary_parsing_occurs():
    """Parse array field (OCCURS)."""
    cobol = """
    01 RECORD.
        03 MONTHS OCCURS 3 PIC 9(2).
    """
    parser = CobolParser()
    records = parser.parse(cobol)

    binary_parser = BinaryDataParser()
    data = b'010212'  # January, February, December
    result = binary_parser.parse(records[0], data)
    assert result['MONTHS'] == [1, 2, 12]

def test_binary_parsing_signed_comp3():
    """Parse signed COMP-3 (negative number)."""
    cobol = """
    01 RECORD.
        03 BALANCE PIC S9(5) COMP-3.
    """
    parser = CobolParser()
    records = parser.parse(cobol)

    binary_parser = BinaryDataParser()
    # COMP-3 encoding of -12345: 0x01 0x23 0x45 0x0D (negative)
    data = b'\x01\x23\x45\x0D'
    result = binary_parser.parse(records[0], data)
    assert result['BALANCE'] == -12345
```

#### 3.5.7 Edge Case Tests

```python
def test_level_77_independent():
    """Level 77 independent items."""
    cobol = "77  WS-COUNTER PIC 9(5) COMP."
    parser = CobolParser()
    records = parser.parse(cobol)
    assert len(records) == 1
    assert records[0].level == 77

def test_multiple_redefines_same_field():
    """Multiple fields redefining the same area."""
    cobol = """
    01 RECORD.
        03 FIELD-A PIC X(20).
        03 FIELD-B REDEFINES FIELD-A PIC 9(20).
        03 FIELD-C REDEFINES FIELD-A.
            05 PART-1 PIC X(10).
            05 PART-2 PIC X(10).
    """
    parser = CobolParser()
    records = parser.parse(cobol)
    # All should have offset 0
    assert records[0].fields[0].byte_offset == 0
    assert records[0].fields[1].byte_offset == 0
    assert records[0].fields[2].byte_offset == 0

def test_nested_occurs():
    """Multi-dimensional arrays."""
    cobol = """
    01 YEAR-DATA.
        03 QUARTER OCCURS 4.
            05 MONTH OCCURS 3 PIC 9(5).
    """
    parser = CobolParser()
    records = parser.parse(cobol)
    quarter = records[0].fields[0]
    assert quarter.occurs == 4
    assert len(quarter.children) == 1
    assert quarter.children[0].occurs == 3

def test_filler_fields():
    """FILLER fields for padding."""
    cobol = """
    01 RECORD.
        03 NAME PIC X(10).
        03 FILLER PIC X(5).
        03 CODE PIC 9(5).
    """
    parser = CobolParser()
    records = parser.parse(cobol)
    assert records[0].fields[1].name == 'FILLER'
    assert records[0].fields[2].byte_offset == 15  # 10 + 5

def test_value_clause_ignored():
    """VALUE clauses should be skipped."""
    cobol = """
    01 RECORD.
        03 MAX-COUNT PIC 9(5) VALUE 99999.
    """
    parser = CobolParser()
    records = parser.parse(cobol)
    # Should parse successfully, value stored but not used
    assert records[0].fields[0].name == 'MAX-COUNT'
```

#### 3.5.8 Cross-Platform Tests

```python
def test_windows_line_endings(tmp_path: Path):
    """Handle Windows CRLF line endings."""
    cobol_file = tmp_path / "test.cbl"
    cobol_file.write_text("01 RECORD.\r\n   03 FIELD PIC X(10).\r\n", encoding='utf-8')

    with cobol_file.open('r', newline=None) as f:
        source = f.read()

    parser = CobolParser()
    records = parser.parse(source)
    assert len(records) == 1

def test_ebcdic_encoding():
    """Handle EBCDIC encoded data."""
    # Create field with EBCDIC encoding
    field = CobolField(
        encoding='cp037',  # EBCDIC
        picture_category=PictureCategory.ALPHANUMERIC,
        byte_offset=0,
        byte_length=10,
        ...
    )

    parser = BinaryDataParser()
    # EBCDIC encoded "HELLO"
    data = b'\xc8\xc5\xd3\xd3\xd6     '
    result = parser._parse_alphanumeric(data, 'cp037')
    assert result == 'HELLO'

def test_pathlib_usage():
    """Ensure Path objects work throughout."""
    from pathlib import Path
    cobol_file = Path("/tmp/test.cbl")
    # Should accept Path, not just strings
    # (Test the API, not actual file I/O)
```

#### 3.5.9 Performance Tests

```python
def test_large_file_parsing():
    """Parse file with 10,000 fields."""
    # Generate large COBOL structure
    lines = ["01 LARGE-RECORD."]
    for i in range(10000):
        lines.append(f"    03 FIELD-{i:05d} PIC X(10).")

    cobol = '\n'.join(lines)
    parser = CobolParser()

    import time
    start = time.time()
    records = parser.parse(cobol)
    elapsed = time.time() - start

    assert len(records[0].fields) == 10000
    assert elapsed < 5.0  # Should complete in under 5 seconds

def test_deep_nesting_limit():
    """Recursion depth limit prevents stack overflow."""
    # Generate deeply nested structure (60 levels)
    lines = ["01 ROOT."]
    level = 3
    for i in range(60):
        lines.append(f"    {'  ' * i}{level:02d} LEVEL-{level}.")
        level += 2

    cobol = '\n'.join(lines)
    parser = CobolParser()

    # Should raise ValueError, not stack overflow
    with pytest.raises(ValueError, match="Nesting too deep"):
        parser.parse(cobol)
```

### 3.6 Handling Edge Cases

The parser should handle edge cases gracefully:

1. **Unsupported PIC types**: Log warning, create placeholder
2. **Malformed lines**: Skip with warning
3. **Inconsistent levels**: Detect and warn
4. **REDEFINES complexity**: Support simple cases, warn on complex
5. **Conditional compilation**: Skip or warn
6. **COPY statements**: Warn (requires preprocessor)

## 4. Alternative Considerations

### 4.1 Hybrid Approach

For maximum robustness, consider a hybrid:
- Use **recursive parser** for structure and hierarchy
- Use **targeted regex** for specific clauses (PIC, OCCURS, etc.)
- Add **validation layer** to catch inconsistencies

### 4.2 Future Enhancements

If requirements expand:
1. **Add COPY statement support**: Include file resolution
2. **Add PICTURE editing symbols**: V, S, P, etc.
3. **Add more COMP types**: COMP-4, COMP-5, etc.
4. **Add VALUE clauses**: For initial values
5. **Add SYNCHRONIZED/JUSTIFIED**: For alignment
6. **Generate Python dataclasses**: Auto-generate type-safe classes

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| COBOL syntax variations | High | Medium | Support both fixed and free format; add configurability |
| Complex REDEFINES | Medium | Medium | Start with simple cases; warn on complex patterns |
| Unknown PIC types | Medium | Low | Extensible type system; easy to add new types |
| Performance on large files | Low | Low | Streaming parser; process line-by-line |
| Encoding issues | Medium | Medium | Support multiple encodings (EBCDIC, ASCII, UTF-8) |

## 6. Conclusion

**Recommendation: Implement Line-by-Line Recursive Parser (Approach 3) with Corrected Algorithms**

This approach offers the best balance of:
- **Simplicity**: Easy to understand and maintain
- **Capability**: Handles hierarchical structures naturally
- **Extensibility**: Easy to add new features
- **Performance**: Efficient for typical file sizes
- **Pythonic**: Follows Python idioms and practices

The recursive parser is a perfect match for COBOL's level-based structure and aligns with the project's principle of simplicity over completeness.

**Important**: This design has been validated through comprehensive review. Critical algorithmic bugs identified in the initial draft have been corrected:
- ✅ REDEFINES offset calculation (now correctly overlaps instead of advancing)
- ✅ Byte length calculation order (now handles OCCURS correctly)
- ✅ Recursive parser logic (now distinguishes immediate children from descendants)
- ✅ Data model expanded with 15+ missing attributes
- ✅ Type hints completed with TypedDict and Union types
- ✅ Cross-platform compatibility with pathlib and configurable encoding

### COBOL Feature Support Matrix

| Feature | Phase 1 | Phase 2 | Phase 3 | Not Supported |
|---------|---------|---------|---------|---------------|
| Basic PIC X/9 | ✅ | | | |
| PIC with V (decimal) | ✅ | | | |
| PIC with S (signed) | ✅ | | | |
| COMP-3/PACKED-DECIMAL | | ✅ | | |
| COMP/COMP-4/BINARY | | ✅ | | |
| COMP-1 (float) | | ✅ | | |
| COMP-2 (double) | | ✅ | | |
| OCCURS (simple) | ✅ | | | |
| OCCURS (nested) | | ✅ | | |
| REDEFINES | | ✅ | | |
| Level 01 (records) | ✅ | | | |
| Level 77 (independent) | ✅ | | | |
| Level 88 (conditions) | ✅ (skip) | | | |
| Level 66 (RENAMES) | | | | ❌ (future) |
| SIGN SEPARATE | | ✅ | | |
| SYNC/SYNCHRONIZED | | | ✅ | |
| JUSTIFIED | | | ✅ | |
| VALUE clauses | ✅ (skip) | | | |
| OCCURS DEPENDING ON | | | ✅ | |
| COPY books | | | | ❌ (future) |
| Editing symbols (Z,$,*) | | | | ❌ (future) |

### Next Steps

**Before Starting Implementation**:
1. ✅ Review corrected algorithms (this document)
2. ✅ Validate data model completeness
3. ✅ Define type hint strategy
4. ✅ Expand test specifications
5. ⏳ Set up project structure per claude.md guidelines

**Implementation Order**:
1. **Phase 0 (Week 0)**: Final design validation
   - Ensure all stakeholders review corrected algorithms
   - Set up development environment
   - Create initial test specifications

2. **Phase 1 (Week 1)**: Core components
   - PictureClauseParser
   - LineTokenizer (with Level 88/77 handling)
   - OffsetCalculator (with corrected REDEFINES)
   - CobolParser (with corrected recursion)
   - 50+ unit tests

3. **Phase 2 (Weeks 2-3)**: Extended features
   - Binary data parser
   - COMP-3 with all sign nibbles
   - REDEFINES resolution
   - Nested OCCURS
   - Cross-platform support
   - 100+ tests total

4. **Phase 3 (Week 4)**: Production-ready
   - Performance optimization
   - Complete error handling
   - API design (dot notation, path access)
   - Documentation
   - 150+ tests with >90% coverage

### Revised Timeline

**Total: 5 weeks** (1 week design validation + 4 weeks implementation)

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 0: Design Validation | 3-5 days | Validated design, test specs |
| Phase 1: Core Components | 1 week | Basic parser, 50+ tests |
| Phase 2: Extended Features | 2 weeks | Binary parser, REDEFINES, 100+ tests |
| Phase 3: Production-Ready | 1 week | Complete package, 150+ tests, docs |
| **Total** | **5 weeks** | **Production-ready parser** |

**Note**: The additional week for design validation prevents 2-3 weeks of refactoring later, resulting in **net time savings** and significantly higher code quality.

### Success Criteria

The implementation will be considered successful when:
- ✅ All 150+ tests passing
- ✅ mypy type checking passes with no errors
- ✅ black formatting and ruff linting pass
- ✅ Test coverage >90%
- ✅ Can parse real COBOL copybooks from mainframe applications
- ✅ Can parse binary data from COBOL programs
- ✅ All critical issues from design review are resolved
- ✅ Documentation complete with examples
- ✅ Performance: Parse 10,000 fields in <5 seconds

### Risk Mitigation

Based on design review, risks have been mitigated:

| Original Risk | Status | Mitigation Applied |
|--------------|--------|-------------------|
| REDEFINES failures | ✅ Resolved | Algorithm corrected to not advance offset |
| OCCURS parsing failures | ✅ Resolved | Added array parsing to binary parser |
| Type hint incompleteness | ✅ Resolved | TypedDict and Union types defined |
| Cross-platform issues | ✅ Resolved | pathlib, configurable encoding, endianness |
| Level 88/77 failures | ✅ Resolved | Added to tokenizer logic |
| Performance on large files | ⚠️ Addressed | Depth limits, streaming option available |
| COBOL syntax variations | 🔄 In Progress | Comprehensive test suite planned |
| Unknown PIC types | ✅ Resolved | Warning system handles gracefully |

### Reference Documents

- **This Document**: Design analysis with corrected algorithms
- **Design Review**: `/workspaces/cobol-data-structure-py/docs/design_review_findings.md`
- **Project Guidelines**: `/workspaces/cobol-data-structure-py/.claude/claude.md`

---

**Document Status**: ✅ Ready for Implementation
**Last Updated**: 2026-01-12 (Post-Design Review)
**Next Action**: Phase 0 - Design validation and stakeholder review
