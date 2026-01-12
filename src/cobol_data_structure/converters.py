"""Type conversion utilities for COBOL data extraction.

This module provides functions to convert raw bytes/strings
from COBOL data into Python types.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .models import CobolField, FieldType, PicClause


def convert_value(
    field: CobolField,
    raw_data: bytes,
    strict: bool = False,
) -> Any:
    """Convert raw bytes to the appropriate Python type.

    Args:
        field: The CobolField definition
        raw_data: Raw bytes from the data buffer
        strict: If True, raise exceptions on conversion errors

    Returns:
        Converted Python value (str, int, Decimal, etc.)
    """
    if field.pic is None:
        # Group field - shouldn't be called directly
        return None

    # Decode bytes to string (ASCII for Unix COBOL)
    try:
        text = raw_data.decode("ascii", errors="replace")
    except Exception:
        text = raw_data.decode("utf-8", errors="replace")

    return convert_string_value(field.pic, text, strict)


def convert_string_value(
    pic: PicClause,
    text: str,
    strict: bool = False,
) -> Any:
    """Convert a string value based on PIC clause.

    Args:
        pic: The PIC clause definition
        text: String value to convert
        strict: If True, raise exceptions on conversion errors

    Returns:
        Converted Python value
    """
    field_type = pic.field_type

    if field_type == FieldType.ALPHANUMERIC:
        return text  # Return as-is, user can .strip()

    if field_type in (FieldType.NUMERIC, FieldType.SIGNED_NUMERIC):
        return convert_numeric(text, pic, strict)

    if field_type in (FieldType.COMP, FieldType.COMP_3):
        return f"<{pic.usage} value>"  # Placeholder

    if field_type == FieldType.UNKNOWN:
        return text  # Return raw text

    if field_type == FieldType.FILLER:
        return None  # FILLER fields don't have values

    # Default: return as string
    return text


def convert_numeric(
    text: str,
    pic: PicClause,
    strict: bool = False,
) -> int | Decimal | None:
    """Convert a numeric string to int or Decimal.

    Args:
        text: String value to convert
        pic: The PIC clause definition
        strict: If True, raise exceptions on conversion errors

    Returns:
        int or Decimal, or None on error
    """
    # Handle empty or whitespace-only strings
    cleaned = text.strip()
    if not cleaned:
        return 0 if not pic.decimal_positions else Decimal("0")

    # Determine sign
    is_negative = False
    if cleaned.startswith("-") or cleaned.endswith("-"):
        is_negative = True
        cleaned = cleaned.replace("-", "")
    elif cleaned.startswith("+") or cleaned.endswith("+"):
        cleaned = cleaned.replace("+", "")

    # Remove any remaining non-digit characters except decimal point
    cleaned = cleaned.strip()

    # Validate numeric content
    if not cleaned.replace(".", "").isdigit():
        if strict:
            raise ValueError(f"Non-numeric value: {text!r}")
        return None

    try:
        if pic.decimal_positions > 0:
            # Has implicit decimal point
            # Insert decimal point at the correct position
            if "." in cleaned:
                # Already has explicit decimal
                result = Decimal(cleaned)
            else:
                # Insert implicit decimal
                if len(cleaned) <= pic.decimal_positions:
                    # All digits are decimal
                    cleaned = "0." + cleaned.zfill(pic.decimal_positions)
                else:
                    # Insert decimal point
                    int_part = cleaned[: -pic.decimal_positions]
                    dec_part = cleaned[-pic.decimal_positions :]
                    cleaned = f"{int_part}.{dec_part}"
                result = Decimal(cleaned)

            if is_negative:
                result = -result
            return result
        else:
            # Integer
            # Remove leading zeros
            cleaned = cleaned.lstrip("0") or "0"
            int_result = int(cleaned)
            if is_negative:
                int_result = -int_result
            return int_result

    except (ValueError, ArithmeticError):
        if strict:
            raise ValueError(f"Cannot convert to numeric: {text!r}") from None
        return None


def calculate_comp_length(pic: PicClause) -> int:
    """Calculate storage length for COMP fields.

    Args:
        pic: The PIC clause definition

    Returns:
        Storage length in bytes
    """
    digits = pic.display_length

    if pic.usage in ("COMP", "BINARY"):
        # Binary: length depends on digit count
        if digits <= 2:
            return 1
        elif digits <= 4:
            return 2
        elif digits <= 6:
            return 3
        elif digits <= 9:
            return 4
        else:
            return 8
    elif pic.usage == "COMP-3":
        # Packed decimal: ceil((digits + 1) / 2)
        return (digits + 2) // 2
    else:
        # DISPLAY or unknown: same as display length
        return digits
