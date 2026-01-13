"""Core data models for COBOL data structure representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass
class Warning:
    """Structured warning information from parsing."""

    message: str
    line_number: int | None = None
    field_name: str | None = None
    severity: str = "warning"  # 'warning' or 'error'

    def __str__(self) -> str:
        """Format warning as string."""
        parts = [f"[{self.severity.upper()}]"]
        if self.line_number is not None:
            parts.append(f"Line {self.line_number}")
        if self.field_name:
            parts.append(f"field {self.field_name}")
        if len(parts) > 1:
            parts[-1] = parts[-1] + ":"
        parts.append(self.message)
        return " ".join(parts)


@dataclass
class CobolField:
    """Represents a single COBOL field in the data structure."""

    name: str
    level: int
    pic: str | None = None
    pic_type: str | None = None  # Parsed type: 'X', '9', 'A', etc.
    size: int = 0
    offset: int = 0  # Absolute offset from record start
    occurs: int | None = None  # Array count (None if not array)
    redefines: str | None = None  # Name of redefined field
    usage: str | None = None  # COMP, COMP-3, DISPLAY, etc.
    children: list[CobolField] = field(default_factory=list)
    parent: CobolField | None = field(default=None, repr=False)
    is_filler: bool = False
    is_signed: bool = False  # Has S prefix in PIC
    decimal_positions: int = 0  # Digits after V (0 if no V)

    def is_group(self) -> bool:
        """Return True if this is a group item (has children)."""
        return len(self.children) > 0

    def is_elementary(self) -> bool:
        """Return True if this is an elementary item (no children)."""
        return len(self.children) == 0

    def get_path(self) -> str:
        """Return the full path from root to this field."""
        parts = []
        current: CobolField | None = self
        while current is not None:
            parts.append(current.name)
            current = current.parent
        return ".".join(reversed(parts))

    def find_child(self, name: str) -> CobolField | None:
        """Find a direct child by name (case-insensitive)."""
        name_upper = name.upper()
        for child in self.children:
            if child.name.upper() == name_upper:
                return child
        return None

    def iter_fields(self) -> Iterator[CobolField]:
        """Iterate over this field and all descendants."""
        yield self
        for child in self.children:
            yield from child.iter_fields()

    def total_size(self) -> int:
        """Return total size including OCCURS multiplier."""
        base_size = self.size
        if self.occurs is not None:
            return base_size * self.occurs
        return base_size


@dataclass
class ParsedRecord:
    """A record populated with actual data values."""

    structure: CobolDataStructure
    raw_data: bytes

    def get_field(self, path: str) -> str | list[str]:
        """Get value by field path, e.g., 'CUSTOMER.ADDRESS.CITY'.

        For OCCURS fields, returns a list of values.
        """
        field = self._resolve_path(path)
        if field is None:
            raise KeyError(f"Field not found: {path}")
        return self._extract_field_value(field)

    def get_field_by_index(self, path: str, index: int) -> str:
        """Get array element value by path and index.

        Args:
            path: Field path to an OCCURS field
            index: Zero-based index into the array

        Returns:
            The value at the specified index
        """
        field = self._resolve_path(path)
        if field is None:
            raise KeyError(f"Field not found: {path}")
        if field.occurs is None:
            raise ValueError(f"Field {path} is not an array (no OCCURS)")
        if index < 0 or index >= field.occurs:
            raise IndexError(
                f"Index {index} out of range for field {path} "
                f"(OCCURS {field.occurs})"
            )

        element_size = field.size
        start = field.offset + (index * element_size)
        end = start + element_size
        return self._decode_value(field, start, end)

    def to_dict(self) -> dict[str, object]:
        """Return all field values as nested dictionary."""
        return self._field_to_dict(self.structure.root_field)

    def _resolve_path(self, path: str) -> CobolField | None:
        """Resolve a dotted path to a field."""
        parts = path.split(".")
        current = self.structure.root_field

        # If path starts with root name, skip it
        if parts and parts[0].upper() == current.name.upper():
            parts = parts[1:]

        for part in parts:
            child = current.find_child(part)
            if child is None:
                return None
            current = child

        return current

    def _extract_field_value(self, field: CobolField) -> str | list[str]:
        """Extract value(s) for a field."""
        if field.is_group():
            # For group items, return concatenated children
            return self._decode_value(field, field.offset, field.offset + field.size)

        if field.occurs is not None:
            # Return list of values for OCCURS
            values = []
            element_size = field.size
            for i in range(field.occurs):
                start = field.offset + (i * element_size)
                end = start + element_size
                values.append(self._decode_value(field, start, end))
            return values

        return self._decode_value(field, field.offset, field.offset + field.size)

    def _decode_value(self, field: CobolField, start: int, end: int) -> str:
        """Decode raw bytes to string value."""
        # Handle COMP types with placeholder
        if field.usage and field.usage.upper().startswith("COMP"):
            return f"{field.usage} value"

        # Ensure we don't read past the data
        actual_end = min(end, len(self.raw_data))
        if start >= len(self.raw_data):
            return ""

        raw_bytes = self.raw_data[start:actual_end]

        # Decode as ASCII/Latin-1 (no EBCDIC per requirements)
        try:
            return raw_bytes.decode("latin-1")
        except (UnicodeDecodeError, AttributeError):
            return raw_bytes.decode("utf-8", errors="replace")

    def _field_to_dict(self, field: CobolField) -> dict[str, object]:
        """Convert a field and its children to a dictionary."""
        result: dict[str, object] = {}

        if field.is_group():
            for child in field.children:
                if child.is_filler:
                    continue
                if child.is_group():
                    result[child.name] = self._field_to_dict(child)
                else:
                    result[child.name] = self._extract_field_value(child)
        else:
            result[field.name] = self._extract_field_value(field)

        return result


@dataclass
class CobolDataStructure:
    """Root structure parsed from COBOL DATA DIVISION."""

    name: str
    root_field: CobolField
    total_size: int = 0
    warnings: list[Warning] = field(default_factory=list)
    source_file: str | None = None
    field_index: dict[str, CobolField] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Build field index after initialization."""
        if not self.field_index:
            self._build_field_index()

    def _build_field_index(self) -> None:
        """Build dictionary for fast field lookup by name."""
        self.field_index = {}
        for fld in self.root_field.iter_fields():
            if not fld.is_filler:
                # Store by uppercase name for case-insensitive lookup
                self.field_index[fld.name.upper()] = fld

    def get_field(self, name: str) -> CobolField | None:
        """Get a field by name (case-insensitive)."""
        return self.field_index.get(name.upper())

    def parse_data(self, raw_data: bytes | str) -> ParsedRecord:
        """Parse raw data into field values.

        Args:
            raw_data: Raw bytes or string from log/file

        Returns:
            ParsedRecord with extracted values
        """
        if isinstance(raw_data, str):
            raw_data = raw_data.encode("latin-1")
        return ParsedRecord(structure=self, raw_data=raw_data)

    def write_warnings(self, filepath: str | Path) -> None:
        """Write collected warnings to file."""
        filepath = Path(filepath)
        with filepath.open("w", encoding="utf-8") as f:
            f.write("# COBOL Parser Warnings\n")
            if self.source_file:
                f.write(f"# Source: {self.source_file}\n")
            f.write("\n")

            for warning in self.warnings:
                f.write(f"{warning}\n")

    def has_warnings(self) -> bool:
        """Return True if there are any warnings."""
        return len(self.warnings) > 0

    def has_errors(self) -> bool:
        """Return True if there are any errors."""
        return any(w.severity == "error" for w in self.warnings)
