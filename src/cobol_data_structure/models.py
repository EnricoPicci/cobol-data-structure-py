"""Data models for COBOL data structure representation.

This module defines the core data classes used to represent COBOL
DATA DIVISION structures in Python.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FieldType(Enum):
    """COBOL field types."""

    ALPHANUMERIC = "X"  # PIC X(n)
    NUMERIC = "9"  # PIC 9(n)
    SIGNED_NUMERIC = "S9"  # PIC S9(n)
    COMP = "COMP"  # Binary
    COMP_3 = "COMP-3"  # Packed decimal
    GROUP = "GROUP"  # Group item (no PIC)
    FILLER = "FILLER"  # Unnamed field
    UNKNOWN = "UNKNOWN"  # Unrecognized pattern


@dataclass
class PicClause:
    """Parsed PIC clause information.

    Attributes:
        raw: Original PIC string (e.g., "S9(5)V99")
        field_type: Type of field (ALPHANUMERIC, NUMERIC, etc.)
        display_length: Characters in display format
        storage_length: Bytes in storage (differs from display for COMP)
        decimal_positions: Digits after V (implicit decimal)
        is_signed: True if PIC starts with S
        usage: Usage clause (DISPLAY, COMP, COMP-3)
    """

    raw: str
    field_type: FieldType
    display_length: int
    storage_length: int
    decimal_positions: int = 0
    is_signed: bool = False
    usage: str = "DISPLAY"


@dataclass
class CobolField:
    """Represents a COBOL field definition.

    Attributes:
        name: Field name (e.g., "CUSTOMER-NAME")
        level: Level number (01-49)
        line_number: Source line for error reporting
        parent: Parent field reference
        children: Child fields for groups
        pic: PIC clause information (None for group items)
        occurs_count: OCCURS n TIMES value
        redefines_name: Name of field being redefined
        redefines_target: Resolved REDEFINES reference
        offset: Byte offset from record start
        storage_length: Bytes in storage
        is_filler: True if FILLER field
        warnings: Any parsing warnings
    """

    name: str
    level: int
    line_number: int = 0
    parent: CobolField | None = None
    children: list[CobolField] = field(default_factory=list)
    pic: PicClause | None = None
    occurs_count: int | None = None
    redefines_name: str | None = None
    redefines_target: CobolField | None = None
    offset: int = 0
    storage_length: int = 0
    is_filler: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def is_group(self) -> bool:
        """Check if this is a group field (has children, no PIC)."""
        return self.pic is None and len(self.children) > 0

    @property
    def is_elementary(self) -> bool:
        """Check if this is an elementary field (has PIC, no children)."""
        return self.pic is not None

    @property
    def total_length(self) -> int:
        """Calculate total length including OCCURS repetitions."""
        base_length = self.storage_length
        if self.occurs_count and self.occurs_count > 1:
            return base_length * self.occurs_count
        return base_length

    def get_child(self, name: str) -> CobolField | None:
        """Find a child field by name (case-insensitive).

        Args:
            name: Field name to search for

        Returns:
            The matching child field or None if not found
        """
        name_upper = name.upper()
        for child in self.children:
            if child.name.upper() == name_upper:
                return child
        return None

    def find_field(self, name: str) -> CobolField | None:
        """Recursively find a field by name in this field's hierarchy.

        Args:
            name: Field name to search for

        Returns:
            The matching field or None if not found
        """
        name_upper = name.upper()
        if self.name.upper() == name_upper:
            return self

        for child in self.children:
            found = child.find_field(name)
            if found:
                return found

        return None

    def __repr__(self) -> str:
        """Return a compact string representation."""
        pic_str = f" PIC {self.pic.raw}" if self.pic else ""
        occurs_str = f" OCCURS {self.occurs_count}" if self.occurs_count else ""
        redefines_str = f" REDEFINES {self.redefines_name}" if self.redefines_name else ""
        return f"CobolField({self.level:02d} {self.name}{pic_str}{occurs_str}{redefines_str})"


@dataclass
class CobolRecord:
    """Root container for a 01-level record definition.

    Attributes:
        name: Record name
        root: Root CobolField (the 01-level field)
        total_length: Total record length in bytes
        warnings: Any parsing warnings for the record
    """

    name: str
    root: CobolField | None = None
    total_length: int = 0
    warnings: list[str] = field(default_factory=list)

    def find_field(self, name: str) -> CobolField | None:
        """Find a field by name in this record.

        Args:
            name: Field name to search for

        Returns:
            The matching field or None if not found
        """
        if self.root:
            return self.root.find_field(name)
        return None

    def get_all_fields(self) -> list[CobolField]:
        """Get all fields in the record as a flat list.

        Returns:
            List of all CobolField objects in depth-first order
        """
        fields: list[CobolField] = []

        def collect(fld: CobolField) -> None:
            fields.append(fld)
            for child in fld.children:
                collect(child)

        if self.root:
            collect(self.root)

        return fields

    def __repr__(self) -> str:
        """Return a string representation."""
        return f"CobolRecord({self.name}, length={self.total_length})"


class CobolError(Exception):
    """Base exception for all COBOL parsing errors."""

    pass


class CobolParseError(CobolError):
    """Invalid COBOL syntax during parsing."""

    def __init__(self, message: str, line_number: int = 0, line_content: str = "") -> None:
        self.line_number = line_number
        self.line_content = line_content
        super().__init__(f"Line {line_number}: {message}" if line_number else message)


class CobolDataError(CobolError):
    """Data doesn't match expected structure."""

    pass


class CobolFieldError(CobolError):
    """Field not found or type mismatch."""

    pass
