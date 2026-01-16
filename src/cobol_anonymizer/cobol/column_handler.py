"""
COBOL Column Handler - Fixed-format and free-format line parsing and reconstruction.

COBOL fixed-column format:
- Columns 1-6:  Sequence number area
- Column 7:     Indicator area (*, /, D, -, or space)
- Columns 8-11: Area A (for division/section headers, 01/77 levels, paragraph names)
- Columns 12-72: Area B (code continuation)
- Columns 73-80: Identification area (often contains change tags)

COBOL free-format (COBOL 2002+):
- No fixed column structure
- Comments start with *>
- Code can start at any column
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from cobol_anonymizer.exceptions import ColumnOverflowError


class COBOLFormat(Enum):
    """COBOL source format types."""

    FIXED = "fixed"  # Traditional 80-column fixed format
    FREE = "free"  # Free-format (COBOL 2002+)
    AUTO = "auto"  # Auto-detect


class IndicatorType(Enum):
    """COBOL column 7 indicator types."""

    BLANK = " "  # Normal code line
    COMMENT = "*"  # Comment line
    PAGE = "/"  # Page eject (treated as comment)
    DEBUG = "D"  # Debug line
    CONTINUATION = "-"  # Continuation of previous line


# Known change tags found in sequence area (columns 1-6)
# These are markers added by developers to track changes
CHANGE_TAGS: set[str] = {
    "BENIQ",
    "CDR",
    "DM2724",
    "REPLAT",
    "CHG",
    "FIX",
    "MOD",
}

# Column position constants
SEQUENCE_START = 0  # Column 1 (0-indexed)
SEQUENCE_END = 6  # Column 6 (exclusive)
INDICATOR_COL = 6  # Column 7 (0-indexed)
AREA_A_START = 7  # Column 8 (0-indexed)
AREA_A_END = 11  # Column 11 (exclusive)
AREA_B_START = 11  # Column 12 (0-indexed)
CODE_END = 72  # Column 72 (exclusive)
ID_AREA_START = 72  # Column 73 (0-indexed)
MAX_LINE_LENGTH = 80  # Maximum line length


@dataclass
class COBOLLine:
    """
    Represents a parsed COBOL source line with all column areas.

    Attributes:
        raw: The original line content (without line ending)
        line_number: 1-based line number in source file
        sequence: Columns 1-6, sequence number area
        indicator: Column 7, indicator character
        area_a: Columns 8-11, division/section/paragraph area
        area_b: Columns 12-72, code area
        identification: Columns 73-80, identification area
        original_length: Length of original line (for preservation)
        line_ending: Original line ending (\n, \r\n, or \r)
        has_change_tag: Whether sequence area contains a known change tag
        change_tag: The detected change tag, if any
        source_format: The format of the source (FIXED or FREE)
    """

    raw: str
    line_number: int
    sequence: str
    indicator: str
    area_a: str
    area_b: str
    identification: str
    original_length: int
    line_ending: str
    has_change_tag: bool
    change_tag: Optional[str] = None
    source_format: COBOLFormat = COBOLFormat.FIXED

    @property
    def is_comment(self) -> bool:
        """Check if this is a comment line."""
        return self.indicator in ("*", "/")

    @property
    def is_continuation(self) -> bool:
        """Check if this is a continuation line."""
        return self.indicator == "-"

    @property
    def is_debug(self) -> bool:
        """Check if this is a debug line."""
        return self.indicator.upper() == "D"

    @property
    def is_blank(self) -> bool:
        """Check if this is a blank line (no code content)."""
        return (self.area_a + self.area_b).strip() == ""

    @property
    def code_area(self) -> str:
        """Get combined code area (columns 8-72)."""
        return self.area_a + self.area_b

    @property
    def code_area_stripped(self) -> str:
        """Get trimmed code content."""
        return self.code_area.rstrip()

    def get_indicator_type(self) -> IndicatorType:
        """Get the indicator type enum."""
        if self.indicator == "*":
            return IndicatorType.COMMENT
        elif self.indicator == "/":
            return IndicatorType.PAGE
        elif self.indicator.upper() == "D":
            return IndicatorType.DEBUG
        elif self.indicator == "-":
            return IndicatorType.CONTINUATION
        else:
            return IndicatorType.BLANK


def detect_change_tag(sequence: str) -> Optional[str]:
    """
    Detect if the sequence area contains a known change tag.

    Args:
        sequence: The 6-character sequence area (columns 1-6)

    Returns:
        The change tag if found, None otherwise
    """
    seq_upper = sequence.upper().strip()
    for tag in CHANGE_TAGS:
        if tag in seq_upper:
            return tag
    return None


# Blank sequence area for cleaning
BLANK_SEQUENCE = " " * 6


def has_sequence_content(sequence: str) -> bool:
    """
    Check if the sequence area has content that should be cleaned.

    This includes:
    - Sequence numbers (all digits)
    - Identification tags (any non-blank content)

    Args:
        sequence: The 6-character sequence area (columns 1-6)

    Returns:
        True if the sequence area has content that should be cleaned
    """
    return sequence.strip() != ""


def clean_sequence(sequence: str) -> str:
    """
    Return a cleaned (blank) sequence area.

    Args:
        sequence: The original 6-character sequence area

    Returns:
        A 6-character string of spaces
    """
    return BLANK_SEQUENCE


def parse_line(line: str, line_number: int = 1, line_ending: str = "\n") -> COBOLLine:
    """
    Parse a COBOL source line into its column components.

    Handles lines of any length, padding short lines with spaces
    and preserving content from long lines.

    Args:
        line: The source line content (without line ending)
        line_number: 1-based line number in source file
        line_ending: The line ending character(s) from the file

    Returns:
        COBOLLine dataclass with all parsed fields
    """
    original_length = len(line)

    # Handle tabs by converting to spaces (COBOL typically uses spaces)
    # This preserves original length tracking
    processed_line = line.replace("\t", "    ")

    # Pad short lines to at least 80 characters for consistent parsing
    padded = processed_line.ljust(80)

    # Extract column areas
    sequence = padded[0:6]  # Columns 1-6
    indicator = padded[6:7]  # Column 7
    area_a = padded[7:11]  # Columns 8-11
    area_b = padded[11:72]  # Columns 12-72
    identification = padded[72:80]  # Columns 73-80

    # Detect change tags
    change_tag = detect_change_tag(sequence)
    has_change_tag = change_tag is not None

    return COBOLLine(
        raw=line,
        line_number=line_number,
        sequence=sequence,
        indicator=indicator,
        area_a=area_a,
        area_b=area_b,
        identification=identification,
        original_length=original_length,
        line_ending=line_ending,
        has_change_tag=has_change_tag,
        change_tag=change_tag,
    )


def reconstruct_line(cobol_line: COBOLLine, preserve_length: bool = True) -> str:
    """
    Reconstruct a COBOL line from its components.

    Args:
        cobol_line: The parsed COBOL line
        preserve_length: If True, preserve the original line length

    Returns:
        The reconstructed line (without line ending)
    """
    # Combine all areas
    full_line = (
        cobol_line.sequence
        + cobol_line.indicator
        + cobol_line.area_a
        + cobol_line.area_b
        + cobol_line.identification
    )

    if preserve_length:
        # Preserve original length exactly
        if cobol_line.original_length < len(full_line):
            # Truncate to original length (rare case)
            return full_line[: cobol_line.original_length]
        elif cobol_line.original_length > len(full_line):
            # Pad to original length
            return full_line.ljust(cobol_line.original_length)
        else:
            return full_line
    else:
        # Return full 80-character line, trimmed of trailing spaces
        return full_line.rstrip()


def reconstruct_line_with_ending(cobol_line: COBOLLine, preserve_length: bool = True) -> str:
    """
    Reconstruct a COBOL line with its original line ending.

    Args:
        cobol_line: The parsed COBOL line
        preserve_length: If True, preserve the original line length

    Returns:
        The reconstructed line with line ending
    """
    line = reconstruct_line(cobol_line, preserve_length)
    return line + cobol_line.line_ending


def validate_code_area(
    cobol_line: COBOLLine,
    file_name: str = "<unknown>",
    new_code_content: Optional[str] = None,
) -> None:
    """
    Validate that the code area does not exceed column 72.

    The code area (columns 8-72) has a maximum of 65 characters.
    This validation ensures that any modifications don't overflow.

    Args:
        cobol_line: The COBOL line to validate
        file_name: The source file name for error reporting
        new_code_content: Optional new content to validate (for checking
                          modifications before they're applied)

    Raises:
        ColumnOverflowError: If code exceeds column 72
    """
    max_length = 65  # Columns 8-72 = 65 characters

    if new_code_content is not None:
        # Validate proposed new content
        content_stripped = new_code_content.rstrip()
        actual_length = len(content_stripped)
    else:
        # Validate existing content from original raw line
        # Check the raw line content in columns 8-72
        raw = cobol_line.raw
        if len(raw) > 7:
            # Get columns 8-72 (indices 7-72)
            code_part = raw[7:72] if len(raw) >= 72 else raw[7:]
            content_stripped = code_part.rstrip()
            actual_length = len(content_stripped)
        else:
            actual_length = 0

    if actual_length > max_length:
        raise ColumnOverflowError(
            file=file_name,
            line=cobol_line.line_number,
            actual_length=actual_length,
            max_length=max_length,
        )


def extract_line_ending(raw_line: str) -> tuple[str, str]:
    """
    Extract line content and line ending separately.

    Args:
        raw_line: The raw line as read from file

    Returns:
        Tuple of (content without ending, line ending)
    """
    if raw_line.endswith("\r\n"):
        return raw_line[:-2], "\r\n"
    elif raw_line.endswith("\n"):
        return raw_line[:-1], "\n"
    elif raw_line.endswith("\r"):
        return raw_line[:-1], "\r"
    else:
        # No line ending (last line of file)
        return raw_line, ""


def parse_file_line(raw_line: str, line_number: int = 1) -> COBOLLine:
    """
    Parse a raw line from a file, handling line endings.

    This is a convenience function that combines extract_line_ending
    and parse_line.

    Args:
        raw_line: The raw line as read from file
        line_number: 1-based line number in source file

    Returns:
        COBOLLine dataclass with all parsed fields
    """
    content, ending = extract_line_ending(raw_line)
    return parse_line(content, line_number, ending)


def get_code_start_column(cobol_line: COBOLLine) -> int:
    """
    Get the column where code content begins (after leading spaces).

    Args:
        cobol_line: The parsed COBOL line

    Returns:
        1-based column number where code starts (8-72)
    """
    code = cobol_line.code_area
    stripped = code.lstrip()
    leading_spaces = len(code) - len(stripped)
    # Column 8 is index 0 in code_area
    return 8 + leading_spaces


def is_area_a_content(cobol_line: COBOLLine) -> bool:
    """
    Check if line has content in Area A (columns 8-11).

    This indicates division headers, section names, paragraph names,
    or level 01/77 entries which start in Area A.

    Args:
        cobol_line: The parsed COBOL line

    Returns:
        True if there is non-space content in Area A
    """
    return cobol_line.area_a.strip() != ""


def detect_cobol_format(lines: list[str]) -> COBOLFormat:
    """
    Detect whether a file uses fixed-format or free-format COBOL.

    Detection heuristics:
    - Free-format: Uses *> comments, lines < 72 chars without sequence numbers
    - Fixed-format: Column 7 has indicators (*, /, D, -), columns 1-6 have numbers

    Args:
        lines: List of source lines from the file

    Returns:
        COBOLFormat.FIXED or COBOLFormat.FREE
    """
    free_format_indicators = 0
    fixed_format_indicators = 0

    for line in lines[:50]:  # Check first 50 lines
        if not line.strip():
            continue

        # Free-format indicator: *> comments
        if "*>" in line:
            free_format_indicators += 2

        # Free-format indicator: Short lines with code starting at column 1
        # that don't look like fixed-format
        if len(line.rstrip()) < 72:
            # Check if it looks like code starts at column 1
            stripped = line.lstrip()
            if stripped and not stripped[0].isdigit():
                # Code starting with non-digit at column 1 suggests free format
                # unless it's a proper indicator in column 7
                if len(line) < 7 or line[6] not in ("*", "/", "D", "d", "-", " "):
                    free_format_indicators += 1

        # Fixed-format indicators
        if len(line) >= 7:
            # Check column 7 for valid indicator
            indicator = line[6] if len(line) > 6 else " "
            if indicator in ("*", "/", "D", "d", "-"):
                # Traditional comment or continuation - likely fixed format
                if indicator in ("*", "/") and "*>" not in line[:10]:
                    fixed_format_indicators += 2

            # Check columns 1-6 for sequence numbers
            seq_area = line[:6] if len(line) >= 6 else line
            if seq_area.strip().isdigit() or seq_area.strip() == "":
                # Looks like valid sequence area
                fixed_format_indicators += 1

        # Check for lines that are exactly 80 characters
        if len(line.rstrip()) == 80 or len(line.rstrip()) > 72:
            fixed_format_indicators += 1

    # Decision: more free-format indicators means free format
    if free_format_indicators > fixed_format_indicators:
        return COBOLFormat.FREE
    else:
        return COBOLFormat.FIXED


def parse_line_free_format(line: str, line_number: int = 1, line_ending: str = "\n") -> COBOLLine:
    """
    Parse a COBOL source line in free format.

    In free format, there's no fixed column structure. Code can start
    at any column. Comments are indicated by *> instead of * in column 7.

    Args:
        line: The source line content (without line ending)
        line_number: 1-based line number in source file
        line_ending: The line ending character(s) from the file

    Returns:
        COBOLLine dataclass with parsed fields adapted for free format
    """
    original_length = len(line)

    # Check for free-format comment (*>)
    stripped = line.lstrip()
    is_comment = stripped.startswith("*>") or stripped.startswith("*")

    # For free format, we store the entire line as the code_area
    # sequence and indicator are virtual (not in the actual line)
    sequence = ""  # Empty - not present in free format
    indicator = "*" if is_comment else " "  # Virtual indicator

    # The entire line content goes into the code area (area_a + area_b)
    # For free format, area_a and area_b together hold the full line
    content = line
    # Pad to at least 65 chars (the code_area size in fixed format)
    padded_content = content.ljust(65)
    area_a = padded_content[:4]
    area_b = padded_content[4:65]

    identification = ""  # Not present in free format

    return COBOLLine(
        raw=line,
        line_number=line_number,
        sequence=sequence,
        indicator=indicator,
        area_a=area_a,
        area_b=area_b,
        identification=identification,
        original_length=original_length,
        line_ending=line_ending,
        has_change_tag=False,
        change_tag=None,
        source_format=COBOLFormat.FREE,
    )


def parse_line_auto(
    line: str,
    line_number: int = 1,
    line_ending: str = "\n",
    detected_format: Optional[COBOLFormat] = None,
) -> COBOLLine:
    """
    Parse a COBOL source line, auto-detecting or using specified format.

    Args:
        line: The source line content (without line ending)
        line_number: 1-based line number in source file
        line_ending: The line ending character(s) from the file
        detected_format: Pre-detected format, or None for auto-detect per line

    Returns:
        COBOLLine dataclass with all parsed fields
    """
    if detected_format == COBOLFormat.FREE:
        return parse_line_free_format(line, line_number, line_ending)
    elif detected_format == COBOLFormat.FIXED:
        return parse_line(line, line_number, line_ending)
    else:
        # Auto-detect per line (less reliable, use detected_format when possible)
        # Quick heuristic: if line has *> or is short without proper structure
        if "*>" in line or (len(line.rstrip()) < 72 and len(line) > 0 and line[0].isalpha()):
            return parse_line_free_format(line, line_number, line_ending)
        return parse_line(line, line_number, line_ending)


def parse_file_line_auto(
    raw_line: str,
    line_number: int = 1,
    detected_format: Optional[COBOLFormat] = None,
) -> COBOLLine:
    """
    Parse a raw line from a file, handling line endings, with format detection.

    Args:
        raw_line: The raw line as read from file
        line_number: 1-based line number in source file
        detected_format: Pre-detected format, or None for auto-detect

    Returns:
        COBOLLine dataclass with all parsed fields
    """
    content, ending = extract_line_ending(raw_line)
    return parse_line_auto(content, line_number, ending, detected_format)
