"""
Exception classes for the COBOL Anonymizer.

This module defines all custom exceptions used throughout the anonymizer,
organized in a hierarchy for easy handling.
"""

from typing import List, Optional


class AnonymizerError(Exception):
    """Base exception for all anonymizer errors."""

    pass


class ParseError(AnonymizerError):
    """Error parsing COBOL source code.

    Attributes:
        file: The file where the error occurred
        line: The line number where the error occurred
        message: Description of the error
    """

    def __init__(self, file: str, line: int, message: str):
        self.file = file
        self.line = line
        self.message = message
        super().__init__(f"{file}:{line}: {message}")


class MappingError(AnonymizerError):
    """Error in mapping generation or application.

    Raised when there's an issue with identifier mapping,
    such as collisions or invalid mappings.
    """

    pass


class ValidationError(AnonymizerError):
    """Base class for validation errors.

    Raised when output validation fails.
    """

    pass


class ColumnOverflowError(ValidationError):
    """Line exceeds column 72 in code area.

    COBOL fixed-format requires code to be within columns 8-72.
    This error is raised when anonymized code exceeds these bounds.

    Attributes:
        file: The file where the overflow occurred
        line: The line number
        actual_length: The actual length of the code area
        max_length: The maximum allowed length (65 for columns 8-72)
    """

    def __init__(
        self,
        file: str,
        line: int,
        actual_length: int,
        max_length: int = 65,
        message: Optional[str] = None,
    ):
        self.file = file
        self.line = line
        self.actual_length = actual_length
        self.max_length = max_length
        if message is None:
            message = (
                f"Code area exceeds column 72 ({actual_length} > {max_length} chars)"
            )
        super().__init__(f"{file}:{line}: {message}")


class IdentifierLengthError(ValidationError):
    """Generated identifier exceeds 30 characters.

    COBOL identifiers must be at most 30 characters long.

    Attributes:
        identifier: The identifier that's too long
        length: The actual length
        max_length: The maximum allowed length (30)
    """

    def __init__(self, identifier: str, length: Optional[int] = None):
        self.identifier = identifier
        self.length = length or len(identifier)
        self.max_length = 30
        super().__init__(
            f"Identifier '{identifier}' exceeds {self.max_length} characters "
            f"(length: {self.length})"
        )


class InvalidIdentifierError(ValidationError):
    """Generated identifier is invalid.

    COBOL identifiers must:
    - Start with a letter
    - Not start or end with a hyphen
    - Contain only letters, digits, and hyphens

    Attributes:
        identifier: The invalid identifier
        reason: Why it's invalid
    """

    def __init__(self, identifier: str, reason: str):
        self.identifier = identifier
        self.reason = reason
        super().__init__(f"Invalid identifier '{identifier}': {reason}")


class ConfigError(AnonymizerError):
    """Configuration error.

    Raised when there's an issue with the configuration,
    such as missing required options or invalid values.
    """

    pass


class CopyNotFoundError(AnonymizerError):
    """Referenced copybook not found.

    Raised when a COPY statement references a copybook
    that doesn't exist in the input directory.

    Attributes:
        copybook: The name of the missing copybook
        file: The file containing the COPY statement
        line: The line number of the COPY statement
    """

    def __init__(self, copybook: str, file: str, line: int):
        self.copybook = copybook
        self.file = file
        self.line = line
        super().__init__(f"{file}:{line}: Copybook '{copybook}' not found")


class CircularDependencyError(AnonymizerError):
    """Circular COPY dependency detected.

    Raised when copybooks form a circular dependency chain,
    which would cause infinite recursion.

    Attributes:
        cycle: List of copybook names forming the cycle
    """

    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        cycle_str = " -> ".join(cycle)
        super().__init__(f"Circular COPY dependency detected: {cycle_str}")


class ReservedWordCollisionError(MappingError):
    """Generated identifier collides with a COBOL reserved word.

    Attributes:
        identifier: The generated identifier
        reserved_word: The reserved word it collides with
    """

    def __init__(self, identifier: str, reserved_word: str):
        self.identifier = identifier
        self.reserved_word = reserved_word
        super().__init__(
            f"Generated identifier '{identifier}' collides with "
            f"reserved word '{reserved_word}'"
        )


class ExternalItemError(AnonymizerError):
    """Error related to EXTERNAL data items.

    EXTERNAL items are shared across programs and require
    special handling during anonymization.
    """

    pass
