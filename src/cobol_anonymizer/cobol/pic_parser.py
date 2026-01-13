"""
COBOL PIC Clause Parser - Detection and parsing of PICTURE clauses.

PIC clauses define the data format and must never be modified during
anonymization. This module detects PIC clauses and their positions
to protect them from modification.

PIC clause patterns:
- PIC X(n)       - Alphanumeric, n characters
- PIC 9(n)       - Numeric, n digits
- PIC S9(n)      - Signed numeric
- PIC S9(n)V9(m) - Decimal numeric
- PIC Z(n)9      - Edited numeric (leading zeros suppressed)
- PIC -(n)9      - Edited numeric (sign)
- PICTURE IS ... - Full keyword form
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class PICType(Enum):
    """Type of PIC clause data."""
    ALPHANUMERIC = "X"      # PIC X(n)
    NUMERIC = "9"           # PIC 9(n)
    ALPHABETIC = "A"        # PIC A(n)
    EDITED_NUMERIC = "Z"    # PIC Z(n), PIC -, etc.
    SIGN = "S"              # Signed
    DECIMAL = "V"           # Decimal point
    MIXED = "MIXED"         # Complex pattern


class UsageType(Enum):
    """COBOL USAGE clause types."""
    DISPLAY = "DISPLAY"         # Default, character representation
    COMP = "COMP"               # Binary (synonym COMPUTATIONAL)
    COMP_1 = "COMP-1"           # Single-precision floating point
    COMP_2 = "COMP-2"           # Double-precision floating point
    COMP_3 = "COMP-3"           # Packed decimal (synonym COMPUTATIONAL-3)
    COMP_4 = "COMP-4"           # Binary (synonym for COMP on many systems)
    COMP_5 = "COMP-5"           # Native binary
    BINARY = "BINARY"           # Binary integer
    PACKED_DECIMAL = "PACKED-DECIMAL"  # Same as COMP-3
    POINTER = "POINTER"         # Pointer
    INDEX = "INDEX"             # Index data item


@dataclass
class PICClause:
    """
    Represents a parsed PIC clause.

    Attributes:
        raw: The raw PIC clause text (e.g., "PIC X(30)")
        start_pos: Starting position in the line (0-indexed)
        end_pos: Ending position in the line (0-indexed, exclusive)
        pic_type: Primary type of the PIC
        pattern: The pattern portion (e.g., "X(30)", "S9(5)V99")
        length: Calculated storage length in characters/digits
    """
    raw: str
    start_pos: int
    end_pos: int
    pic_type: PICType
    pattern: str
    length: int


@dataclass
class UsageClause:
    """
    Represents a parsed USAGE clause.

    Attributes:
        raw: The raw USAGE clause text
        start_pos: Starting position in the line
        end_pos: Ending position in the line
        usage_type: The USAGE type
    """
    raw: str
    start_pos: int
    end_pos: int
    usage_type: UsageType


# Regex patterns for PIC clause detection
# Match PIC or PICTURE, optional IS, then the pattern
# The pattern includes letters, digits, parentheses, and punctuation
PIC_PATTERN = re.compile(
    r'\b(PIC(?:TURE)?)\s+(?:IS\s+)?'
    r'([SsVvXxAa9ZzBbPp0/,\-\+\*\(\)0-9]+)(?:\.)?',
    re.IGNORECASE
)

# Pattern to extract repetition count like X(30) or 9(5)
REPETITION_PATTERN = re.compile(r'([XxAa9Zz])\((\d+)\)')

# Pattern to match individual PIC characters and their counts
PIC_CHAR_PATTERN = re.compile(r'([XxAa9SsVvZzBbPp\-\+\.\*])(?:\((\d+)\))?')

# USAGE clause patterns
# Use stricter matching to avoid matching INDEX within identifiers like WS-INDEX
USAGE_PATTERN = re.compile(
    r'(?:^|[\s\.])(?:USAGE\s+(?:IS\s+)?)?'
    r'(COMP(?:UTATIONAL)?(?:-[1-5])?|BINARY|PACKED-DECIMAL|DISPLAY|POINTER|INDEX)'
    r'(?=[\s\.\,]|$)',
    re.IGNORECASE
)


def find_pic_clauses(line: str) -> List[PICClause]:
    """
    Find all PIC clauses in a line.

    Args:
        line: The COBOL line to search

    Returns:
        List of PICClause objects found in the line
    """
    clauses = []

    for match in PIC_PATTERN.finditer(line):
        keyword = match.group(1)
        pattern = match.group(2)

        # Calculate the length
        length = calculate_pic_length(pattern)

        # Determine the primary type
        pic_type = determine_pic_type(pattern)

        clause = PICClause(
            raw=match.group(0),
            start_pos=match.start(),
            end_pos=match.end(),
            pic_type=pic_type,
            pattern=pattern,
            length=length,
        )
        clauses.append(clause)

    return clauses


def find_usage_clauses(line: str) -> List[UsageClause]:
    """
    Find all USAGE clauses in a line.

    Args:
        line: The COBOL line to search

    Returns:
        List of UsageClause objects found in the line
    """
    clauses = []

    for match in USAGE_PATTERN.finditer(line):
        usage_text = match.group(1).upper()

        # Map to UsageType
        if usage_text.startswith("COMP"):
            if usage_text in ("COMP", "COMPUTATIONAL"):
                usage_type = UsageType.COMP
            elif usage_text in ("COMP-1", "COMPUTATIONAL-1"):
                usage_type = UsageType.COMP_1
            elif usage_text in ("COMP-2", "COMPUTATIONAL-2"):
                usage_type = UsageType.COMP_2
            elif usage_text in ("COMP-3", "COMPUTATIONAL-3"):
                usage_type = UsageType.COMP_3
            elif usage_text in ("COMP-4", "COMPUTATIONAL-4"):
                usage_type = UsageType.COMP_4
            elif usage_text in ("COMP-5", "COMPUTATIONAL-5"):
                usage_type = UsageType.COMP_5
            else:
                usage_type = UsageType.COMP
        elif usage_text == "BINARY":
            usage_type = UsageType.BINARY
        elif usage_text == "PACKED-DECIMAL":
            usage_type = UsageType.PACKED_DECIMAL
        elif usage_text == "DISPLAY":
            usage_type = UsageType.DISPLAY
        elif usage_text == "POINTER":
            usage_type = UsageType.POINTER
        elif usage_text == "INDEX":
            usage_type = UsageType.INDEX
        else:
            usage_type = UsageType.DISPLAY

        clause = UsageClause(
            raw=match.group(0),
            start_pos=match.start(),
            end_pos=match.end(),
            usage_type=usage_type,
        )
        clauses.append(clause)

    return clauses


def calculate_pic_length(pattern: str) -> int:
    """
    Calculate the display length of a PIC pattern.

    Args:
        pattern: The PIC pattern string (e.g., "X(30)", "S9(5)V99")

    Returns:
        The number of display positions
    """
    length = 0
    upper_pattern = pattern.upper()

    # Find all characters with optional repetition counts
    for match in PIC_CHAR_PATTERN.finditer(upper_pattern):
        char = match.group(1).upper()
        count_str = match.group(2)
        count = int(count_str) if count_str else 1

        # Characters that take display positions
        if char in ('X', 'A', '9', 'Z', 'B', '-', '+', '.', '*', '/'):
            length += count
        elif char == 'S':
            # Sign - separate sign takes position, embedded doesn't
            # For simplicity, assume embedded (no position)
            pass
        elif char == 'V':
            # Assumed decimal - no display position
            pass
        elif char == 'P':
            # Scaling position - no display position
            pass

    return length


def determine_pic_type(pattern: str) -> PICType:
    """
    Determine the primary type of a PIC pattern.

    Args:
        pattern: The PIC pattern string

    Returns:
        The primary PICType
    """
    upper_pattern = pattern.upper()

    # Check for various patterns
    has_x = 'X' in upper_pattern
    has_a = 'A' in upper_pattern
    has_9 = '9' in upper_pattern
    has_s = 'S' in upper_pattern
    has_v = 'V' in upper_pattern
    has_z = 'Z' in upper_pattern
    has_edit = any(c in upper_pattern for c in ('Z', 'B', '-', '+', '*', '/'))

    # Determine type
    if has_edit:
        return PICType.EDITED_NUMERIC
    elif has_x and not has_9:
        return PICType.ALPHANUMERIC
    elif has_a and not has_9 and not has_x:
        return PICType.ALPHABETIC
    elif has_s and has_9:
        return PICType.SIGN
    elif has_v:
        return PICType.DECIMAL
    elif has_9:
        return PICType.NUMERIC
    else:
        return PICType.MIXED


def is_in_pic_clause(line: str, position: int) -> bool:
    """
    Check if a position in the line is within a PIC clause.

    Args:
        line: The COBOL line
        position: The position to check (0-indexed)

    Returns:
        True if the position is within a PIC clause
    """
    clauses = find_pic_clauses(line)
    for clause in clauses:
        if clause.start_pos <= position < clause.end_pos:
            return True
    return False


def is_in_usage_clause(line: str, position: int) -> bool:
    """
    Check if a position in the line is within a USAGE clause.

    Args:
        line: The COBOL line
        position: The position to check (0-indexed)

    Returns:
        True if the position is within a USAGE clause
    """
    clauses = find_usage_clauses(line)
    for clause in clauses:
        if clause.start_pos <= position < clause.end_pos:
            return True
    return False


def get_protected_ranges(line: str) -> List[Tuple[int, int]]:
    """
    Get all ranges in the line that should not be modified.

    This includes PIC clauses and USAGE clauses.

    Args:
        line: The COBOL line

    Returns:
        List of (start, end) tuples representing protected ranges
    """
    ranges = []

    # Add PIC clause ranges
    for clause in find_pic_clauses(line):
        ranges.append((clause.start_pos, clause.end_pos))

    # Add USAGE clause ranges
    for clause in find_usage_clauses(line):
        ranges.append((clause.start_pos, clause.end_pos))

    # Sort by start position
    ranges.sort(key=lambda x: x[0])

    return ranges


def is_protected_position(line: str, position: int) -> bool:
    """
    Check if a position should not be modified.

    Args:
        line: The COBOL line
        position: The position to check

    Returns:
        True if the position is protected
    """
    return is_in_pic_clause(line, position) or is_in_usage_clause(line, position)


def extract_pic_from_line(line: str) -> Optional[str]:
    """
    Extract the PIC pattern from a line if present.

    Args:
        line: The COBOL line

    Returns:
        The PIC pattern string, or None if no PIC clause found
    """
    clauses = find_pic_clauses(line)
    if clauses:
        return clauses[0].pattern
    return None


def has_value_clause(line: str) -> bool:
    """
    Check if the line contains a VALUE clause.

    VALUE clauses should be preserved during anonymization
    (the keyword, not necessarily the value).

    Args:
        line: The COBOL line

    Returns:
        True if a VALUE clause is present
    """
    return bool(re.search(r'\bVALUE\s+(?:IS\s+)?', line, re.IGNORECASE))


def has_redefines_clause(line: str) -> bool:
    """
    Check if the line contains a REDEFINES clause.

    Args:
        line: The COBOL line

    Returns:
        True if a REDEFINES clause is present
    """
    return bool(re.search(r'\bREDEFINES\s+', line, re.IGNORECASE))


def has_occurs_clause(line: str) -> bool:
    """
    Check if the line contains an OCCURS clause.

    Args:
        line: The COBOL line

    Returns:
        True if an OCCURS clause is present
    """
    return bool(re.search(r'\bOCCURS\s+', line, re.IGNORECASE))


def has_external_clause(line: str) -> bool:
    """
    Check if the line contains an EXTERNAL clause.

    EXTERNAL items should NOT be anonymized as they are
    shared between programs.

    Args:
        line: The COBOL line

    Returns:
        True if an EXTERNAL clause is present
    """
    return bool(re.search(r'\bEXTERNAL\b', line, re.IGNORECASE))


def has_global_clause(line: str) -> bool:
    """
    Check if the line contains a GLOBAL clause.

    Args:
        line: The COBOL line

    Returns:
        True if a GLOBAL clause is present
    """
    return bool(re.search(r'\bGLOBAL\b', line, re.IGNORECASE))
