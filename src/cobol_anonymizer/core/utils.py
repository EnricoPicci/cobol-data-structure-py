"""
Utility functions for the COBOL Anonymizer.

This module provides helper functions for:
- COBOL identifier validation
- Column position calculations
- String manipulation with COBOL rules
- Case-insensitive comparisons
"""

import re

from cobol_anonymizer.exceptions import (
    IdentifierLengthError,
    InvalidIdentifierError,
)

# COBOL identifier constraints
MAX_IDENTIFIER_LENGTH = 30
MIN_IDENTIFIER_LENGTH = 1

# Valid COBOL identifier pattern
# Must start with letter, can contain letters, digits, and hyphens
# Cannot start or end with hyphen
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9-]*[A-Za-z0-9]$|^[A-Za-z]$")


def validate_identifier(name: str, raise_on_error: bool = True) -> tuple[bool, str]:
    """Validate that a name is a valid COBOL identifier.

    COBOL identifiers must:
    - Be 1-30 characters long
    - Start with a letter
    - Contain only letters, digits, and hyphens
    - Not start with a hyphen
    - Not end with a hyphen

    Args:
        name: The identifier to validate
        raise_on_error: If True, raise exception on invalid; otherwise return tuple

    Returns:
        Tuple of (is_valid, error_message)

    Raises:
        IdentifierLengthError: If name exceeds 30 characters
        InvalidIdentifierError: If name violates other rules
    """
    # Check length
    if len(name) > MAX_IDENTIFIER_LENGTH:
        error = f"exceeds {MAX_IDENTIFIER_LENGTH} characters (length: {len(name)})"
        if raise_on_error:
            raise IdentifierLengthError(name, len(name))
        return False, error

    if len(name) < MIN_IDENTIFIER_LENGTH:
        error = "identifier is empty"
        if raise_on_error:
            raise InvalidIdentifierError(name, error)
        return False, error

    # Check first character
    if not name[0].isalpha():
        error = "must start with a letter"
        if raise_on_error:
            raise InvalidIdentifierError(name, error)
        return False, error

    # Check for leading hyphen (redundant with above, but explicit)
    if name[0] == "-":
        error = "cannot start with hyphen"
        if raise_on_error:
            raise InvalidIdentifierError(name, error)
        return False, error

    # Check for trailing hyphen
    if name[-1] == "-":
        error = "cannot end with hyphen"
        if raise_on_error:
            raise InvalidIdentifierError(name, error)
        return False, error

    # Check for valid characters
    if not IDENTIFIER_PATTERN.match(name):
        # Find the invalid character
        for i, char in enumerate(name):
            if not (char.isalnum() or char == "-"):
                error = f"contains invalid character '{char}' at position {i}"
                if raise_on_error:
                    raise InvalidIdentifierError(name, error)
                return False, error
        # Generic error if pattern didn't match but chars seem ok
        error = "invalid identifier format"
        if raise_on_error:
            raise InvalidIdentifierError(name, error)
        return False, error

    return True, ""


def normalize_identifier(name: str) -> str:
    """Normalize an identifier to uppercase for comparison.

    COBOL is case-insensitive, so identifiers should be compared
    in uppercase form.

    Args:
        name: The identifier to normalize

    Returns:
        Uppercase version of the identifier
    """
    return name.upper()


def identifiers_equal(name1: str, name2: str) -> bool:
    """Check if two identifiers are equal (case-insensitive).

    Args:
        name1: First identifier
        name2: Second identifier

    Returns:
        True if identifiers are equal (ignoring case)
    """
    return normalize_identifier(name1) == normalize_identifier(name2)


def pad_to_length(text: str, length: int, pad_char: str = " ") -> str:
    """Pad text to a specific length.

    Args:
        text: Text to pad
        length: Target length
        pad_char: Character to use for padding (default: space)

    Returns:
        Padded text
    """
    if len(text) >= length:
        return text
    return text + pad_char * (length - len(text))


def truncate_to_length(text: str, length: int) -> str:
    """Truncate text to a specific length.

    Args:
        text: Text to truncate
        length: Maximum length

    Returns:
        Truncated text
    """
    if len(text) <= length:
        return text
    return text[:length]


def calculate_column_position(area: str, offset: int) -> int:
    """Calculate the absolute column position from area and offset.

    COBOL columns:
    - Sequence area: 1-6
    - Indicator: 7
    - Area A: 8-11
    - Area B: 12-72
    - Identification: 73-80

    Args:
        area: One of 'sequence', 'indicator', 'A', 'B', 'identification'
        offset: 0-based offset within the area

    Returns:
        1-based absolute column number
    """
    area_starts = {
        "sequence": 1,
        "indicator": 7,
        "A": 8,
        "B": 12,
        "identification": 73,
    }
    return area_starts.get(area, 1) + offset


def is_level_number(text: str) -> bool:
    """Check if text is a valid COBOL level number.

    Valid level numbers: 01-49, 66, 77, 88

    Args:
        text: Text to check

    Returns:
        True if text is a valid level number
    """
    text = text.strip()
    if not text.isdigit():
        return False

    num = int(text)
    return (1 <= num <= 49) or num in (66, 77, 88)


def get_level_number(text: str) -> int:
    """Parse a level number from text.

    Args:
        text: Text containing a level number

    Returns:
        The level number as an integer

    Raises:
        ValueError: If text is not a valid level number
    """
    text = text.strip()
    if not is_level_number(text):
        raise ValueError(f"'{text}' is not a valid COBOL level number")
    return int(text)


def is_filler(name: str) -> bool:
    """Check if a name is FILLER.

    FILLER is a special COBOL keyword that should not be anonymized.

    Args:
        name: Name to check

    Returns:
        True if name is FILLER (case-insensitive)
    """
    return normalize_identifier(name) == "FILLER"


def format_file_location(file: str, line: int) -> str:
    """Format a file location string.

    Args:
        file: File name or path
        line: Line number

    Returns:
        Formatted string like "file.cob:123"
    """
    return f"{file}:{line}"
