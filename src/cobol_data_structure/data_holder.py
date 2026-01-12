"""Runtime data container for COBOL record data.

This module provides the DataHolder class which can be filled
with data from raw bytes/strings and provides convenient access
to field values.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .converters import convert_value
from .models import CobolDataError, CobolField, CobolRecord, FieldType
from .warnings_log import WarningsLog


class DataHolder:
    """Runtime container for COBOL record data.

    Provides multiple access patterns for field values:
    - Attribute access: holder.customer_name (converts underscores to hyphens)
    - Dict access: holder["CUSTOMER-NAME"]
    - Case-insensitive access for both patterns

    Attributes:
        record: The CobolRecord structure definition
        warnings: WarningsLog for collecting extraction warnings
    """

    def __init__(
        self,
        record: CobolRecord,
        warnings_log: WarningsLog | None = None,
    ) -> None:
        """Initialize the data holder.

        Args:
            record: The CobolRecord structure definition
            warnings_log: Optional WarningsLog instance
        """
        self._record = record
        self._warnings = warnings_log or WarningsLog()
        self._data: dict[str, Any] = {}
        self._raw_data: bytes = b""
        self._strict = False

    def fill_from_bytes(
        self,
        data: bytes,
        strict: bool = False,
    ) -> DataHolder:
        """Fill fields from raw byte data.

        Args:
            data: Raw bytes containing the record data
            strict: If True, raise exceptions on conversion errors

        Returns:
            Self for method chaining
        """
        self._raw_data = data
        self._strict = strict
        self._data = {}

        if not self._record.root:
            return self

        # Validate data length
        expected_length = self._record.total_length
        actual_length = len(data)

        if actual_length < expected_length:
            msg = f"Data too short: expected {expected_length} bytes, got {actual_length}"
            if strict:
                raise CobolDataError(msg)
            self._warnings.add(msg)
            # Pad with spaces
            data = data + b" " * (expected_length - actual_length)
        elif actual_length > expected_length:
            self._warnings.add(
                f"Data longer than expected ({actual_length} > {expected_length}), truncating"
            )
            data = data[:expected_length]

        # Extract field values from root's children directly into _data
        if self._record.root:
            for child in self._record.root.children:
                self._extract_field(child, data)

        return self

    def fill_from_string(
        self,
        data: str,
        encoding: str = "ascii",
        strict: bool = False,
    ) -> DataHolder:
        """Fill fields from a string.

        Args:
            data: String containing the record data
            encoding: Encoding to use when converting to bytes
            strict: If True, raise exceptions on conversion errors

        Returns:
            Self for method chaining
        """
        return self.fill_from_bytes(data.encode(encoding), strict)

    def _extract_field(
        self,
        field: CobolField,
        data: bytes,
    ) -> Any:
        """Extract a field value from the data.

        Args:
            field: The field definition
            data: Full record data

        Returns:
            Extracted value (may be nested dict or list)
        """
        # Skip FILLER fields in output
        if field.is_filler:
            return None

        start = field.offset
        length = field.storage_length

        # Handle OCCURS (arrays)
        if field.occurs_count and field.occurs_count > 1:
            values = []
            item_length = length
            for i in range(field.occurs_count):
                item_start = start + (i * item_length)
                item_data = data[item_start : item_start + item_length]

                if field.children:
                    # Group with OCCURS - create nested structure for each
                    item_value = self._extract_group(field, data, item_start)
                else:
                    # Elementary field with OCCURS
                    item_value = self._convert_field_value(field, item_data)

                values.append(item_value)

            self._data[field.name] = values
            return values

        # Handle group fields (has children)
        if field.children:
            group_value = self._extract_group(field, data, start)
            self._data[field.name] = group_value
            return group_value

        # Elementary field
        raw_bytes = data[start : start + length]
        value = self._convert_field_value(field, raw_bytes)
        self._data[field.name] = value
        return value

    def _extract_group(
        self,
        field: CobolField,
        data: bytes,
        base_offset: int,
    ) -> dict[str, Any]:
        """Extract a group field's children.

        Args:
            field: The group field definition
            data: Full record data
            base_offset: Base offset for this group instance

        Returns:
            Dict of child field values
        """
        result: dict[str, Any] = {}

        for child in field.children:
            if child.is_filler:
                continue

            child_start = base_offset + (child.offset - field.offset)
            child_length = child.storage_length

            if child.occurs_count and child.occurs_count > 1:
                # Child with OCCURS
                values = []
                for i in range(child.occurs_count):
                    item_start = child_start + (i * child_length)

                    if child.children:
                        item_value = self._extract_group(child, data, item_start)
                    else:
                        item_data = data[item_start : item_start + child_length]
                        item_value = self._convert_field_value(child, item_data)

                    values.append(item_value)
                result[child.name] = values

            elif child.children:
                # Nested group
                result[child.name] = self._extract_group(child, data, child_start)

            else:
                # Elementary child
                child_data = data[child_start : child_start + child_length]
                result[child.name] = self._convert_field_value(child, child_data)

        return result

    def _convert_field_value(self, field: CobolField, raw_bytes: bytes) -> Any:
        """Convert raw bytes to Python value.

        Args:
            field: The field definition
            raw_bytes: Raw bytes for this field

        Returns:
            Converted Python value
        """
        try:
            result = convert_value(field, raw_bytes, self._strict)
            # Log warning if numeric conversion returned None (invalid data)
            if result is None and field.pic and field.pic.field_type in (
                FieldType.NUMERIC,
                FieldType.SIGNED_NUMERIC,
            ):
                text = raw_bytes.decode("ascii", errors="replace")
                self._warnings.add(
                    f"Invalid numeric value for {field.name}: {text!r}",
                    field.line_number,
                )
            return result
        except (ValueError, TypeError) as e:
            self._warnings.add(f"Conversion error for {field.name}: {e}", field.line_number)
            return None

    def __getattr__(self, name: str) -> Any:
        """Attribute access: holder.customer_name.

        Converts Python-style names (with underscores) to COBOL-style
        names (with hyphens) and performs case-insensitive lookup.

        Args:
            name: Attribute name

        Returns:
            Field value

        Raises:
            AttributeError: If field not found
        """
        # Avoid recursion for private attributes
        if name.startswith("_"):
            raise AttributeError(name)

        # Convert underscores to hyphens for COBOL naming
        cobol_name = name.upper().replace("_", "-")

        try:
            return self._get_field(cobol_name)
        except KeyError:
            raise AttributeError(f"No field named '{name}' (tried '{cobol_name}')") from None

    def __getitem__(self, key: str) -> Any:
        """Dict access: holder["CUSTOMER-NAME"].

        Args:
            key: Field name

        Returns:
            Field value

        Raises:
            KeyError: If field not found
        """
        return self._get_field(key.upper())

    def _get_field(self, name: str) -> Any:
        """Case-insensitive field lookup.

        Args:
            name: Field name (uppercase)

        Returns:
            Field value

        Raises:
            KeyError: If field not found
        """
        # Try exact match first
        if name in self._data:
            return self._data[name]

        # Try case-insensitive
        name_upper = name.upper()
        for key in self._data:
            if key.upper() == name_upper:
                return self._data[key]

        raise KeyError(f"Field not found: {name}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get field value with default.

        Args:
            key: Field name
            default: Default value if field not found

        Returns:
            Field value or default
        """
        try:
            return self._get_field(key.upper())
        except KeyError:
            return default

    def to_dict(self) -> dict[str, Any]:
        """Return all field values as a dictionary.

        Returns:
            Dict of field names to values
        """
        return dict(self._data)

    def keys(self) -> list[str]:
        """Get all field names.

        Returns:
            List of field names
        """
        return list(self._data.keys())

    def values(self) -> list[Any]:
        """Get all field values.

        Returns:
            List of field values
        """
        return list(self._data.values())

    def items(self) -> list[tuple[str, Any]]:
        """Get all field name-value pairs.

        Returns:
            List of (name, value) tuples
        """
        return list(self._data.items())

    def __contains__(self, key: str) -> bool:
        """Check if field exists.

        Args:
            key: Field name

        Returns:
            True if field exists
        """
        try:
            self._get_field(key.upper())
            return True
        except KeyError:
            return False

    def __iter__(self) -> Iterator[str]:
        """Iterate over field names.

        Returns:
            Iterator of field names
        """
        return iter(self._data)

    def __len__(self) -> int:
        """Get number of fields.

        Returns:
            Number of fields
        """
        return len(self._data)

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            String representation
        """
        return f"DataHolder({self._record.name}, {len(self._data)} fields)"

    @property
    def record(self) -> CobolRecord:
        """Get the record definition."""
        return self._record

    @property
    def warnings(self) -> WarningsLog:
        """Get the warnings log."""
        return self._warnings

    @property
    def raw_data(self) -> bytes:
        """Get the raw data used to fill the holder."""
        return self._raw_data


class NestedDataHolder:
    """Wrapper for nested group data with attribute access.

    Provides the same access patterns as DataHolder for nested
    group fields.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize with nested data dict.

        Args:
            data: Dict of field values
        """
        self._data = data

    def __getattr__(self, name: str) -> Any:
        """Attribute access with underscore-to-hyphen conversion."""
        if name.startswith("_"):
            raise AttributeError(name)

        cobol_name = name.upper().replace("_", "-")

        if cobol_name in self._data:
            value = self._data[cobol_name]
            if isinstance(value, dict):
                return NestedDataHolder(value)
            return value

        # Case-insensitive fallback
        for key in self._data:
            if key.upper() == cobol_name:
                value = self._data[key]
                if isinstance(value, dict):
                    return NestedDataHolder(value)
                return value

        raise AttributeError(f"No field named '{name}'")

    def __getitem__(self, key: str) -> Any:
        """Dict access."""
        key_upper = key.upper()
        if key_upper in self._data:
            return self._data[key_upper]

        for k in self._data:
            if k.upper() == key_upper:
                return self._data[k]

        raise KeyError(key)

    def to_dict(self) -> dict[str, Any]:
        """Return as dict."""
        return dict(self._data)

    def __repr__(self) -> str:
        return f"NestedDataHolder({list(self._data.keys())})"
