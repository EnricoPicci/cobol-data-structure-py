"""Tests for DataHolder module."""

import pytest

from cobol_data_structure import (
    CobolDataError,
    DataHolder,
    parse_string,
)


class TestDataHolderBasic:
    """Basic tests for DataHolder."""

    def test_fill_from_string(self, simple_record) -> None:
        """Test filling from string data."""
        # CUSTOMER-ID (8) + CUSTOMER-NAME (30) + BALANCE (9) = 47 bytes
        data = "12345678John Doe                      000123456"

        holder = DataHolder(simple_record)
        holder.fill_from_string(data)

        assert holder["CUSTOMER-ID"] == 12345678
        assert holder["CUSTOMER-NAME"].strip() == "John Doe"

    def test_fill_from_bytes(self, simple_record) -> None:
        """Test filling from bytes data."""
        data = b"12345678John Doe                      000123456"

        holder = DataHolder(simple_record)
        holder.fill_from_bytes(data)

        assert holder["CUSTOMER-ID"] == 12345678

    def test_attribute_access(self, simple_record) -> None:
        """Test attribute-style access with underscore conversion."""
        data = "12345678John Doe                      000123456"

        holder = DataHolder(simple_record)
        holder.fill_from_string(data)

        # Underscores converted to hyphens
        assert holder.customer_id == 12345678
        assert holder.customer_name.strip() == "John Doe"

    def test_dict_access(self, simple_record) -> None:
        """Test dict-style access."""
        data = "12345678John Doe                      000123456"

        holder = DataHolder(simple_record)
        holder.fill_from_string(data)

        assert holder["CUSTOMER-ID"] == 12345678
        assert holder["customer-id"] == 12345678  # Case insensitive

    def test_get_with_default(self, simple_record) -> None:
        """Test get method with default value."""
        holder = DataHolder(simple_record)
        holder.fill_from_string("12345678" + " " * 39)

        assert holder.get("CUSTOMER-ID") == 12345678
        assert holder.get("NONEXISTENT", "default") == "default"

    def test_contains(self, simple_record) -> None:
        """Test __contains__ method."""
        holder = DataHolder(simple_record)
        holder.fill_from_string("12345678" + " " * 39)

        assert "CUSTOMER-ID" in holder
        assert "NONEXISTENT" not in holder

    def test_to_dict(self, simple_record) -> None:
        """Test converting to dictionary."""
        data = "12345678John Doe                      000123456"

        holder = DataHolder(simple_record)
        holder.fill_from_string(data)

        result = holder.to_dict()
        assert isinstance(result, dict)
        assert "CUSTOMER-ID" in result
        assert "CUSTOMER-NAME" in result


class TestDataHolderNested:
    """Tests for nested record data extraction."""

    def test_nested_field_extraction(self, nested_record) -> None:
        """Test extracting nested fields."""
        # EMP-ID (6) + FIRST-NAME (15) + LAST-NAME (20) +
        # STREET (30) + CITY (20) + ZIP (5) = 96 bytes
        data = (
            "123456"  # EMP-ID
            "John           "  # FIRST-NAME
            "Doe                 "  # LAST-NAME
            "123 Main Street               "  # STREET
            "New York            "  # CITY
            "10001"  # ZIP
        )

        holder = DataHolder(nested_record)
        holder.fill_from_string(data)

        assert holder["EMP-ID"] == 123456

    def test_nested_group_as_dict(self, nested_record) -> None:
        """Test nested groups are returned as dicts."""
        data = (
            "123456"
            "John           "
            "Doe                 "
            "123 Main Street               "
            "New York            "
            "10001"
        )

        holder = DataHolder(nested_record)
        holder.fill_from_string(data)

        emp_name = holder["EMP-NAME"]
        assert isinstance(emp_name, dict)
        assert "FIRST-NAME" in emp_name
        assert emp_name["FIRST-NAME"].strip() == "John"


class TestDataHolderOccurs:
    """Tests for OCCURS array extraction."""

    def test_occurs_extraction(self, occurs_record) -> None:
        """Test extracting OCCURS arrays."""
        # ORDER-ID (8) + ITEM-COUNT (2) + 5 items * (10 + 3 + 7) = 110 bytes
        data = (
            "00000001"  # ORDER-ID
            "03"  # ITEM-COUNT
            "ITEM-001  0100000500"  # Item 1
            "ITEM-002  0050001000"  # Item 2
            "ITEM-003  0020002500"  # Item 3
            "          0000000000"  # Item 4 (empty)
            "          0000000000"  # Item 5 (empty)
        )

        holder = DataHolder(occurs_record)
        holder.fill_from_string(data)

        assert holder["ORDER-ID"] == 1
        assert holder["ITEM-COUNT"] == 3

        items = holder["ITEMS"]
        assert isinstance(items, list)
        assert len(items) == 5

    def test_occurs_item_access(self, occurs_record) -> None:
        """Test accessing individual OCCURS items."""
        data = (
            "00000001"
            "03"
            "ITEM-001  0100000500"
            "ITEM-002  0050001000"
            "ITEM-003  0020002500"
            "          0000000000"
            "          0000000000"
        )

        holder = DataHolder(occurs_record)
        holder.fill_from_string(data)

        items = holder["ITEMS"]
        assert items[0]["ITEM-CODE"].strip() == "ITEM-001"
        assert items[0]["ITEM-QTY"] == 10


class TestDataHolderNumericConversion:
    """Tests for numeric type conversion."""

    def test_unsigned_numeric(self) -> None:
        """Test unsigned numeric conversion."""
        cobol = """
01 RECORD.
    03 NUM-FIELD PIC 9(5).
"""
        record = parse_string(cobol)
        holder = DataHolder(record)
        holder.fill_from_string("00123")

        assert holder["NUM-FIELD"] == 123

    def test_signed_numeric_leading_sign(self) -> None:
        """Test signed numeric with leading sign."""
        cobol = """
01 RECORD.
    03 NUM-FIELD PIC S9(5).
"""
        record = parse_string(cobol)
        holder = DataHolder(record)

        # S9(5) = 1 sign + 5 digits = 6 chars
        holder.fill_from_string("-00123")
        assert holder["NUM-FIELD"] == -123

        holder.fill_from_string("+00456")
        assert holder["NUM-FIELD"] == 456

    def test_signed_numeric_trailing_sign(self) -> None:
        """Test signed numeric with trailing sign."""
        cobol = """
01 RECORD.
    03 NUM-FIELD PIC S9(5).
"""
        record = parse_string(cobol)
        holder = DataHolder(record)

        # S9(5) = 1 sign + 5 digits = 6 chars
        holder.fill_from_string("00123-")
        assert holder["NUM-FIELD"] == -123

    def test_decimal_conversion(self) -> None:
        """Test decimal field conversion."""
        from decimal import Decimal

        cobol = """
01 RECORD.
    03 AMOUNT PIC 9(5)V99.
"""
        record = parse_string(cobol)
        holder = DataHolder(record)

        holder.fill_from_string("0012345")  # 123.45
        assert holder["AMOUNT"] == Decimal("123.45")

    def test_alphanumeric_preserved(self) -> None:
        """Test alphanumeric fields preserve whitespace."""
        cobol = """
01 RECORD.
    03 NAME PIC X(10).
"""
        record = parse_string(cobol)
        holder = DataHolder(record)

        holder.fill_from_string("John      ")
        # Raw value includes trailing spaces
        assert holder["NAME"] == "John      "
        # User can strip
        assert holder["NAME"].strip() == "John"


class TestDataHolderEdgeCases:
    """Tests for edge cases in data extraction."""

    def test_short_data_warning(self, simple_record) -> None:
        """Test warning for data shorter than expected."""
        holder = DataHolder(simple_record)
        holder.fill_from_string("12345")  # Way too short

        assert holder.warnings.has_warnings()

    def test_short_data_strict_raises(self, simple_record) -> None:
        """Test strict mode raises for short data."""
        holder = DataHolder(simple_record)

        with pytest.raises(CobolDataError):
            holder.fill_from_bytes(b"12345", strict=True)

    def test_long_data_truncated(self, simple_record) -> None:
        """Test long data is truncated."""
        holder = DataHolder(simple_record)
        data = "12345678John Doe                      000123456" + "EXTRA DATA"

        holder.fill_from_string(data)
        assert holder.warnings.has_warnings()
        assert holder["CUSTOMER-ID"] == 12345678

    def test_empty_numeric_field(self) -> None:
        """Test empty numeric field returns 0."""
        cobol = """
01 RECORD.
    03 NUM-FIELD PIC 9(5).
"""
        record = parse_string(cobol)
        holder = DataHolder(record)

        holder.fill_from_string("     ")  # All spaces
        assert holder["NUM-FIELD"] == 0

    def test_invalid_numeric_returns_none(self) -> None:
        """Test invalid numeric data returns None."""
        cobol = """
01 RECORD.
    03 NUM-FIELD PIC 9(5).
"""
        record = parse_string(cobol)
        holder = DataHolder(record)

        holder.fill_from_string("ABCDE")
        assert holder["NUM-FIELD"] is None

    def test_comp_placeholder(self) -> None:
        """Test COMP fields return placeholder."""
        cobol = """
01 RECORD.
    03 COMP-FIELD PIC 9(5) COMP-3.
"""
        record = parse_string(cobol)
        holder = DataHolder(record)

        holder.fill_from_string("123")  # COMP-3 uses 3 bytes
        # Placeholder contains usage type
        result = str(holder["COMP-FIELD"])
        assert "COMP" in result and "value" in result


class TestDataHolderRedefines:
    """Tests for REDEFINES handling."""

    def test_redefines_same_data(self, redefines_record_cobol) -> None:
        """Test REDEFINES fields read same data."""
        record = parse_string(redefines_record_cobol)

        # RECORD-TYPE (1) + RECORD-DATA (50) = 51 bytes
        data = "A" + "1234567890" * 5

        holder = DataHolder(record)
        holder.fill_from_string(data)

        # Both fields should start at same offset
        assert holder["RECORD-TYPE"] == "A"
        # RECORD-DATA is alphanumeric
        assert holder["RECORD-DATA"].startswith("1234567890")


class TestDataHolderFiller:
    """Tests for FILLER field handling."""

    def test_filler_not_in_output(self, filler_record_cobol) -> None:
        """Test FILLER fields are not in output dict."""
        record = parse_string(filler_record_cobol)
        data = "HDR " + "XX" + "DATA      " + "XXXX" + "TRL "

        holder = DataHolder(record)
        holder.fill_from_string(data)

        result = holder.to_dict()
        # FILLER fields should not appear
        assert "FILLER-1" not in result
        assert "FILLER-2" not in result

        # Regular fields should appear
        assert "HEADER" in result
        assert "DATA-FIELD" in result


class TestDataHolderIteration:
    """Tests for DataHolder iteration."""

    def test_keys(self, simple_record) -> None:
        """Test getting field keys."""
        holder = DataHolder(simple_record)
        holder.fill_from_string("12345678" + " " * 39)

        keys = holder.keys()
        assert "CUSTOMER-ID" in keys

    def test_values(self, simple_record) -> None:
        """Test getting field values."""
        holder = DataHolder(simple_record)
        holder.fill_from_string("12345678" + " " * 39)

        values = holder.values()
        assert 12345678 in values

    def test_items(self, simple_record) -> None:
        """Test getting field items."""
        holder = DataHolder(simple_record)
        holder.fill_from_string("12345678" + " " * 39)

        items = holder.items()
        assert any(k == "CUSTOMER-ID" and v == 12345678 for k, v in items)

    def test_iteration(self, simple_record) -> None:
        """Test iterating over holder."""
        holder = DataHolder(simple_record)
        holder.fill_from_string("12345678" + " " * 39)

        field_names = list(holder)
        assert "CUSTOMER-ID" in field_names

    def test_len(self, simple_record) -> None:
        """Test len of holder."""
        holder = DataHolder(simple_record)
        holder.fill_from_string("12345678" + " " * 39)

        assert len(holder) > 0
