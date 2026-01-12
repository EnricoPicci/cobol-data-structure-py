"""Integration tests for the complete COBOL parsing workflow."""

import pytest

from cobol_data_structure import (
    CobolParser,
    DataHolder,
    parse_string,
)


class TestEndToEndSimple:
    """End-to-end tests with simple records."""

    def test_parse_and_extract_customer(self) -> None:
        """Test complete workflow with customer record."""
        from decimal import Decimal

        cobol = """
01 CUSTOMER-RECORD.
    03 CUSTOMER-ID PIC 9(8).
    03 CUSTOMER-NAME PIC X(30).
    03 BALANCE PIC S9(7)V99.
"""
        # Parse the COBOL definition
        record = parse_string(cobol)
        assert record is not None
        assert record.name == "CUSTOMER-RECORD"

        # Create data holder
        holder = DataHolder(record)

        # Fill with sample data
        # ID: 12345678 (8 chars)
        # NAME: "John Doe" + padding (30 chars)
        # BALANCE: S9(7)V99 = sign(1) + 7 digits + 2 decimals = 10 chars
        data = "12345678John Doe                      -000012345"
        holder.fill_from_string(data)

        # Verify extraction
        assert holder.customer_id == 12345678
        assert holder.customer_name.strip() == "John Doe"
        assert holder.balance == Decimal("-123.45")

    def test_parse_and_extract_with_groups(self) -> None:
        """Test workflow with nested groups."""
        cobol = """
01 PERSON-RECORD.
    03 PERSON-ID PIC 9(6).
    03 PERSON-NAME.
        05 FIRST-NAME PIC X(15).
        05 LAST-NAME PIC X(20).
    03 BIRTH-DATE.
        05 BIRTH-YEAR PIC 9(4).
        05 BIRTH-MONTH PIC 9(2).
        05 BIRTH-DAY PIC 9(2).
"""
        record = parse_string(cobol)
        holder = DataHolder(record)

        # Total: 6 + 15 + 20 + 4 + 2 + 2 = 49 bytes
        data = (
            "000001"  # PERSON-ID
            "Alice          "  # FIRST-NAME
            "Smith               "  # LAST-NAME
            "1990"  # BIRTH-YEAR
            "05"  # BIRTH-MONTH
            "15"  # BIRTH-DAY
        )
        holder.fill_from_string(data)

        assert holder.person_id == 1
        assert holder["PERSON-NAME"]["FIRST-NAME"].strip() == "Alice"
        assert holder["BIRTH-DATE"]["BIRTH-YEAR"] == 1990


class TestEndToEndOccurs:
    """End-to-end tests with OCCURS arrays."""

    def test_parse_and_extract_order(self) -> None:
        """Test workflow with OCCURS clause."""
        cobol = """
01 ORDER-RECORD.
    03 ORDER-NUMBER PIC 9(8).
    03 LINE-COUNT PIC 9(2).
    03 ORDER-LINES OCCURS 3 TIMES.
        05 PRODUCT-CODE PIC X(10).
        05 QUANTITY PIC 9(4).
        05 UNIT-PRICE PIC 9(6)V99.
"""
        record = parse_string(cobol)
        holder = DataHolder(record)

        # Total: 8 + 2 + 3*(10 + 4 + 8) = 76 bytes
        data = (
            "00000001"  # ORDER-NUMBER
            "02"  # LINE-COUNT
            "PROD-A    "  # Line 1 PRODUCT-CODE
            "0010"  # Line 1 QUANTITY
            "00002500"  # Line 1 UNIT-PRICE (25.00)
            "PROD-B    "  # Line 2 PRODUCT-CODE
            "0005"  # Line 2 QUANTITY
            "00005000"  # Line 2 UNIT-PRICE (50.00)
            "          "  # Line 3 PRODUCT-CODE (empty)
            "0000"  # Line 3 QUANTITY
            "00000000"  # Line 3 UNIT-PRICE
        )
        holder.fill_from_string(data)

        assert holder.order_number == 1
        assert holder.line_count == 2

        lines = holder["ORDER-LINES"]
        assert len(lines) == 3
        assert lines[0]["PRODUCT-CODE"].strip() == "PROD-A"
        assert lines[0]["QUANTITY"] == 10
        assert lines[0]["UNIT-PRICE"] == pytest.approx(25.00)
        assert lines[1]["PRODUCT-CODE"].strip() == "PROD-B"


class TestEndToEndRedefines:
    """End-to-end tests with REDEFINES."""

    def test_parse_and_extract_with_redefines(self) -> None:
        """Test workflow with REDEFINES clause."""
        cobol = """
01 TRANSACTION-RECORD.
    03 TRANS-TYPE PIC X.
    03 TRANS-DATA PIC X(20).
    03 TRANS-NUMERIC REDEFINES TRANS-DATA.
        05 AMOUNT PIC 9(10).
        05 FILLER PIC X(10).
"""
        record = parse_string(cobol)
        holder = DataHolder(record)

        # Numeric transaction
        data = "N" + "0000001000" + "          "
        holder.fill_from_string(data)

        assert holder.trans_type == "N"
        # Can read same data two ways
        assert holder["TRANS-DATA"].startswith("0000001000")
        assert holder["TRANS-NUMERIC"]["AMOUNT"] == 1000


class TestEndToEndComplex:
    """End-to-end tests with complex records."""

    def test_complex_nested_occurs(self) -> None:
        """Test complex record with nested OCCURS."""
        cobol = """
01 INVOICE-RECORD.
    03 INVOICE-HEADER.
        05 INVOICE-NUM PIC 9(8).
        05 INVOICE-DATE PIC 9(8).
    03 LINE-ITEMS OCCURS 2 TIMES.
        05 ITEM-SKU PIC X(8).
        05 ITEM-DESC PIC X(20).
        05 ITEM-QTY PIC 9(4).
    03 INVOICE-TOTAL PIC 9(8)V99.
"""
        record = parse_string(cobol)

        # Verify structure
        assert record.total_length == (
            8 + 8  # Header
            + 2 * (8 + 20 + 4)  # 2 line items
            + 10  # Total
        )  # = 90 bytes

        holder = DataHolder(record)
        data = (
            "00000001"  # INVOICE-NUM
            "20240115"  # INVOICE-DATE
            "SKU00001"  # Item 1 SKU
            "Widget A            "  # Item 1 DESC
            "0010"  # Item 1 QTY
            "SKU00002"  # Item 2 SKU
            "Widget B            "  # Item 2 DESC
            "0005"  # Item 2 QTY
            "0000150000"  # TOTAL (1500.00)
        )
        holder.fill_from_string(data)

        assert holder["INVOICE-HEADER"]["INVOICE-NUM"] == 1
        assert holder["INVOICE-HEADER"]["INVOICE-DATE"] == 20240115

        items = holder["LINE-ITEMS"]
        assert items[0]["ITEM-SKU"].strip() == "SKU00001"
        assert items[0]["ITEM-QTY"] == 10
        assert items[1]["ITEM-SKU"].strip() == "SKU00002"

        assert holder.invoice_total == pytest.approx(1500.00)


class TestEndToEndMultipleRecords:
    """Tests for parsing multiple records."""

    def test_parse_multiple_records(self) -> None:
        """Test parsing source with multiple 01-level records."""
        cobol = """
01 RECORD-A.
    03 FIELD-A1 PIC X(10).
    03 FIELD-A2 PIC 9(5).

01 RECORD-B.
    03 FIELD-B1 PIC X(20).
"""
        parser = CobolParser()
        records = parser.parse_string(cobol)

        assert len(records) == 2
        assert records[0].name == "RECORD-A"
        assert records[1].name == "RECORD-B"


class TestEndToEndErrorHandling:
    """Tests for error handling in complete workflow."""

    def test_lenient_mode_continues(self) -> None:
        """Test lenient mode continues on errors."""
        cobol = """
01 RECORD.
    03 NUM-FIELD PIC 9(5).
    03 TEXT-FIELD PIC X(10).
"""
        record = parse_string(cobol)
        holder = DataHolder(record)

        # Invalid numeric data
        holder.fill_from_string("ABCDEHello     ")

        # Should have warning but continue
        assert holder.warnings.has_warnings()
        # Numeric field is None due to conversion error
        assert holder["NUM-FIELD"] is None
        # Text field still works
        assert holder["TEXT-FIELD"].strip() == "Hello"

    def test_strict_mode_raises(self) -> None:
        """Test strict mode raises on data errors."""
        cobol = """
01 RECORD.
    03 FIELD PIC X(10).
"""
        record = parse_string(cobol)
        holder = DataHolder(record)

        # Data too short
        from cobol_data_structure import CobolDataError

        with pytest.raises(CobolDataError):
            holder.fill_from_bytes(b"short", strict=True)


class TestEndToEndRealWorld:
    """Tests simulating real-world COBOL record scenarios."""

    def test_mainframe_style_record(self) -> None:
        """Test record similar to mainframe batch processing."""
        from decimal import Decimal

        cobol = """
01 BATCH-RECORD.
    03 RECORD-TYPE PIC X(2).
    03 FILLER PIC X(3).
    03 ACCOUNT-NUMBER PIC 9(10).
    03 TRANSACTION-AMOUNT PIC S9(9)V99.
    03 TRANSACTION-DATE.
        05 TRANS-YEAR PIC 9(4).
        05 TRANS-MONTH PIC 9(2).
        05 TRANS-DAY PIC 9(2).
    03 DESCRIPTION PIC X(30).
    03 FILLER PIC X(10).
"""
        record = parse_string(cobol)

        # Total: 2 + 3 + 10 + 12 (S9(9)V99 with sign) + 8 + 30 + 10 = 75 bytes
        assert record.total_length == 75

        holder = DataHolder(record)
        data = (
            "DR"  # RECORD-TYPE
            "   "  # FILLER
            "1234567890"  # ACCOUNT-NUMBER
            "-00000012345"  # TRANSACTION-AMOUNT (-123.45): sign(1) + 9 digits + 2 decimal
            "2024"  # TRANS-YEAR
            "01"  # TRANS-MONTH
            "15"  # TRANS-DAY
            "Payment received              "  # DESCRIPTION
            "          "  # FILLER
        )
        holder.fill_from_string(data)

        assert holder.record_type == "DR"
        assert holder.account_number == 1234567890
        assert holder.transaction_amount == Decimal("-123.45")
        assert holder["TRANSACTION-DATE"]["TRANS-YEAR"] == 2024
        assert holder.description.strip() == "Payment received"

    def test_variable_format_record(self) -> None:
        """Test record with different interpretations via REDEFINES."""
        cobol = """
01 MULTI-FORMAT-RECORD.
    03 FORMAT-CODE PIC X.
    03 COMMON-DATA PIC X(10).
    03 FORMAT-SPECIFIC PIC X(50).
    03 FORMAT-A-DATA REDEFINES FORMAT-SPECIFIC.
        05 A-NAME PIC X(30).
        05 A-CODE PIC 9(10).
        05 FILLER PIC X(10).
    03 FORMAT-B-DATA REDEFINES FORMAT-SPECIFIC.
        05 B-ID PIC 9(15).
        05 B-AMOUNT PIC 9(10)V99.
        05 FILLER PIC X(23).
"""
        record = parse_string(cobol)
        holder = DataHolder(record)

        # Format A record
        data_a = (
            "A"  # FORMAT-CODE
            "COMMON    "  # COMMON-DATA
            "John Smith                    "  # A-NAME
            "1234567890"  # A-CODE
            "          "  # FILLER
        )
        holder.fill_from_string(data_a)

        assert holder.format_code == "A"
        assert holder["FORMAT-A-DATA"]["A-NAME"].strip() == "John Smith"
        assert holder["FORMAT-A-DATA"]["A-CODE"] == 1234567890
