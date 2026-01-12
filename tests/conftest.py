"""Pytest configuration and fixtures."""

import pytest

from cobol_data_structure import (
    CobolParser,
    parse_string,
)


@pytest.fixture
def simple_record_cobol() -> str:
    """Simple COBOL record definition."""
    return """
01 CUSTOMER-RECORD.
    03 CUSTOMER-ID PIC 9(8).
    03 CUSTOMER-NAME PIC X(30).
    03 BALANCE PIC S9(7)V99.
"""


@pytest.fixture
def nested_record_cobol() -> str:
    """COBOL record with nested groups."""
    return """
01 EMPLOYEE-RECORD.
    03 EMP-ID PIC 9(6).
    03 EMP-NAME.
        05 FIRST-NAME PIC X(15).
        05 LAST-NAME PIC X(20).
    03 EMP-ADDRESS.
        05 STREET PIC X(30).
        05 CITY PIC X(20).
        05 ZIP PIC 9(5).
"""


@pytest.fixture
def occurs_record_cobol() -> str:
    """COBOL record with OCCURS clause."""
    return """
01 ORDER-RECORD.
    03 ORDER-ID PIC 9(8).
    03 ITEM-COUNT PIC 9(2).
    03 ITEMS OCCURS 5 TIMES.
        05 ITEM-CODE PIC X(10).
        05 ITEM-QTY PIC 9(3).
        05 ITEM-PRICE PIC 9(5)V99.
"""


@pytest.fixture
def redefines_record_cobol() -> str:
    """COBOL record with REDEFINES clause."""
    return """
01 DATA-RECORD.
    03 RECORD-TYPE PIC X.
    03 RECORD-DATA PIC X(50).
    03 RECORD-DATA-NUM REDEFINES RECORD-DATA.
        05 NUM-FIELD-1 PIC 9(10).
        05 NUM-FIELD-2 PIC 9(10).
        05 FILLER PIC X(30).
"""


@pytest.fixture
def filler_record_cobol() -> str:
    """COBOL record with multiple FILLER fields."""
    return """
01 FIXED-RECORD.
    03 HEADER PIC X(4).
    03 FILLER PIC X(2).
    03 DATA-FIELD PIC X(10).
    03 FILLER PIC X(4).
    03 TRAILER PIC X(4).
"""


@pytest.fixture
def parser() -> CobolParser:
    """Create a CobolParser instance."""
    return CobolParser()


@pytest.fixture
def simple_record(simple_record_cobol: str):
    """Parse the simple record."""
    return parse_string(simple_record_cobol)


@pytest.fixture
def nested_record(nested_record_cobol: str):
    """Parse the nested record."""
    return parse_string(nested_record_cobol)


@pytest.fixture
def occurs_record(occurs_record_cobol: str):
    """Parse the occurs record."""
    return parse_string(occurs_record_cobol)
