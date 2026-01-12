"""Regex patterns for COBOL syntax parsing.

This module defines all regex patterns used to extract COBOL
DATA DIVISION elements from source code.
"""

import re

# Level number: 01-49, 66, 77, 88
# Matches the level number at the start of a field definition
LEVEL_PATTERN = re.compile(r"^\s*(\d{2})\s+")

# Field name (allows hyphens, must start with letter)
# Captures the field name after the level number
NAME_PATTERN = re.compile(r"^\s*\d{2}\s+([A-Za-z][A-Za-z0-9\-]*)", re.IGNORECASE)

# FILLER keyword detection
# Must match FILLER followed by whitespace or PIC, not FILLER-SOMETHING
FILLER_PATTERN = re.compile(r"^\s*\d{2}\s+FILLER(?:\s|$)", re.IGNORECASE)

# PIC clause - captures the picture string
# Matches: PIC X(10), PIC IS 9(5), PICTURE S9(3)V99
PIC_PATTERN = re.compile(
    r"\bPIC(?:TURE)?\s+(?:IS\s+)?([SXV90-9()\-+Z*A]+)",
    re.IGNORECASE,
)

# PIC component patterns for parsing the picture string
# X or X(n) - alphanumeric
PIC_ALPHA = re.compile(r"X(?:\((\d+)\))?", re.IGNORECASE)

# 9 or 9(n) - numeric
PIC_NUMERIC = re.compile(r"9(?:\((\d+)\))?", re.IGNORECASE)

# Leading S - signed
PIC_SIGNED = re.compile(r"^S", re.IGNORECASE)

# V - implicit decimal point
PIC_DECIMAL = re.compile(r"V", re.IGNORECASE)

# Z or Z(n) - zero suppression (display only)
PIC_ZERO_SUPPRESS = re.compile(r"Z(?:\((\d+)\))?", re.IGNORECASE)

# COMP usage clause
# Matches: COMP, COMP-1, COMP-2, COMP-3, COMPUTATIONAL, COMPUTATIONAL-3
COMP_PATTERN = re.compile(
    r"\b(COMP-3|COMP-1|COMP-2|COMP|COMPUTATIONAL-3|COMPUTATIONAL-1|COMPUTATIONAL-2|COMPUTATIONAL)\b",
    re.IGNORECASE,
)

# USAGE clause (more general)
USAGE_PATTERN = re.compile(
    r"\bUSAGE\s+(?:IS\s+)?(DISPLAY|COMP-3|COMP-1|COMP-2|COMP|COMPUTATIONAL-3|"
    r"COMPUTATIONAL-1|COMPUTATIONAL-2|COMPUTATIONAL|BINARY|PACKED-DECIMAL)\b",
    re.IGNORECASE,
)

# OCCURS clause
# Matches: OCCURS 10, OCCURS 10 TIMES
OCCURS_PATTERN = re.compile(r"\bOCCURS\s+(\d+)\s*(?:TIMES)?\b", re.IGNORECASE)

# OCCURS DEPENDING ON clause (for variable-length arrays)
OCCURS_DEPENDING_PATTERN = re.compile(
    r"\bOCCURS\s+\d+\s+TO\s+(\d+)\s*(?:TIMES)?\s+DEPENDING\s+ON\s+([A-Za-z][A-Za-z0-9\-]*)",
    re.IGNORECASE,
)

# REDEFINES clause
REDEFINES_PATTERN = re.compile(
    r"\bREDEFINES\s+([A-Za-z][A-Za-z0-9\-]*)",
    re.IGNORECASE,
)

# VALUE clause (to skip/ignore)
VALUE_PATTERN = re.compile(r"\bVALUE\s+(?:IS\s+)?", re.IGNORECASE)

# INDEXED BY clause (to skip)
INDEXED_BY_PATTERN = re.compile(
    r"\bINDEXED\s+BY\s+([A-Za-z][A-Za-z0-9\-]*)",
    re.IGNORECASE,
)

# Statement terminator (period at end)
PERIOD_PATTERN = re.compile(r"\.\s*$")

# Comment line detection (column 7 asterisk)
# For fixed-format COBOL, column 7 is the indicator area
COMMENT_PATTERN = re.compile(r"^.{6}\*")

# Inline comment (*> to end of line)
INLINE_COMMENT_PATTERN = re.compile(r"\*>.*$")

# Sequence number detection (6 digits at start)
SEQUENCE_PATTERN = re.compile(r"^(\d{6})")

# Continuation line (column 7 hyphen in fixed format)
CONTINUATION_PATTERN = re.compile(r"^.{6}-")


def normalize_usage(usage: str) -> str:
    """Normalize USAGE clause value to standard form.

    Args:
        usage: Raw usage string from source

    Returns:
        Normalized usage string (DISPLAY, COMP, COMP-3, etc.)
    """
    usage_upper = usage.upper().strip()

    # Map COMPUTATIONAL variants to COMP variants
    mappings = {
        "COMPUTATIONAL": "COMP",
        "COMPUTATIONAL-1": "COMP-1",
        "COMPUTATIONAL-2": "COMP-2",
        "COMPUTATIONAL-3": "COMP-3",
        "BINARY": "COMP",
        "PACKED-DECIMAL": "COMP-3",
    }

    return mappings.get(usage_upper, usage_upper)


def count_pic_chars(pic_string: str, char: str) -> int:
    """Count the number of characters in a PIC clause.

    Handles both repeated characters (XXX) and parenthesized counts (X(3)).

    Args:
        pic_string: The PIC string to parse (e.g., "X(10)" or "999")
        char: The character to count (e.g., "X" or "9")

    Returns:
        Total count of the character
    """
    total = 0
    pattern = re.compile(rf"{char}(?:\((\d+)\))?", re.IGNORECASE)

    for match in pattern.finditer(pic_string):
        count_str = match.group(1)
        if count_str:
            total += int(count_str)
        else:
            total += 1

    return total


def parse_pic_length(pic_string: str) -> tuple[int, int]:
    """Parse a PIC string and return display and decimal lengths.

    Args:
        pic_string: The PIC string to parse (e.g., "S9(5)V99")

    Returns:
        Tuple of (total_length, decimal_positions)
    """
    # Check if signed (sign takes 1 position for explicit sign)
    is_signed = bool(PIC_SIGNED.match(pic_string))

    # Remove sign indicator for digit counting
    pic_clean = re.sub(r"^S", "", pic_string, flags=re.IGNORECASE)

    # Count alphanumeric characters
    alpha_count = count_pic_chars(pic_clean, "X")
    alpha_count += count_pic_chars(pic_clean, "A")

    # Count numeric characters
    numeric_count = count_pic_chars(pic_clean, "9")
    numeric_count += count_pic_chars(pic_clean, "Z")

    # Calculate decimal positions (digits after V)
    decimal_positions = 0
    if "V" in pic_clean.upper():
        # Split at V and count 9s after it
        parts = pic_clean.upper().split("V", 1)
        if len(parts) > 1:
            decimal_positions = count_pic_chars(parts[1], "9")

    total_length = alpha_count + numeric_count

    # Add 1 for explicit sign position if signed
    if is_signed and numeric_count > 0:
        total_length += 1

    return total_length, decimal_positions
