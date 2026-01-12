"""Tests for regex patterns module."""

import pytest

from cobol_data_structure.patterns import (
    COMP_PATTERN,
    FILLER_PATTERN,
    LEVEL_PATTERN,
    NAME_PATTERN,
    OCCURS_PATTERN,
    PIC_PATTERN,
    PIC_SIGNED,
    REDEFINES_PATTERN,
    count_pic_chars,
    normalize_usage,
    parse_pic_length,
)


class TestLevelPattern:
    """Tests for level number pattern."""

    @pytest.mark.parametrize(
        "line,expected",
        [
            ("01 RECORD-NAME.", "01"),
            ("03 FIELD-NAME PIC X(10).", "03"),
            ("  05  NESTED-FIELD PIC 9(5).", "05"),
            ("77 STANDALONE PIC X.", "77"),
            ("88 CONDITION VALUE 1.", "88"),
        ],
    )
    def test_level_extraction(self, line: str, expected: str) -> None:
        """Test extracting level numbers."""
        match = LEVEL_PATTERN.match(line)
        assert match is not None
        assert match.group(1) == expected

    def test_no_level_number(self) -> None:
        """Test lines without level numbers."""
        assert LEVEL_PATTERN.match("NO LEVEL HERE") is None
        assert LEVEL_PATTERN.match("  JUST TEXT") is None


class TestNamePattern:
    """Tests for field name pattern."""

    @pytest.mark.parametrize(
        "line,expected",
        [
            ("01 RECORD-NAME.", "RECORD-NAME"),
            ("03 FIELD-NAME PIC X(10).", "FIELD-NAME"),
            ("05 MY-FIELD-123 PIC 9(5).", "MY-FIELD-123"),
            ("03 A PIC X.", "A"),
        ],
    )
    def test_name_extraction(self, line: str, expected: str) -> None:
        """Test extracting field names."""
        match = NAME_PATTERN.match(line)
        assert match is not None
        assert match.group(1).upper() == expected.upper()


class TestFillerPattern:
    """Tests for FILLER detection."""

    @pytest.mark.parametrize(
        "line",
        [
            "03 FILLER PIC X(10).",
            "05 FILLER PIC 9(5).",
            "03 filler PIC X.",  # Case insensitive
        ],
    )
    def test_filler_detection(self, line: str) -> None:
        """Test detecting FILLER fields."""
        assert FILLER_PATTERN.match(line) is not None

    def test_non_filler(self) -> None:
        """Test non-FILLER fields."""
        assert FILLER_PATTERN.match("03 MY-FILLER PIC X.") is None
        assert FILLER_PATTERN.match("03 FILLER-FIELD PIC X.") is None


class TestPicPattern:
    """Tests for PIC clause pattern."""

    @pytest.mark.parametrize(
        "line,expected",
        [
            ("03 FIELD PIC X(10).", "X(10)"),
            ("03 FIELD PIC 9(5).", "9(5)"),
            ("03 FIELD PIC S9(3)V99.", "S9(3)V99"),
            ("03 FIELD PICTURE IS X(20).", "X(20)"),
            ("03 FIELD PIC IS 9(8).", "9(8)"),
            ("03 FIELD PIC XXX.", "XXX"),
            ("03 FIELD PIC 999.", "999"),
            ("03 FIELD PIC Z(5)9.", "Z(5)9"),
        ],
    )
    def test_pic_extraction(self, line: str, expected: str) -> None:
        """Test extracting PIC clauses."""
        match = PIC_PATTERN.search(line)
        assert match is not None
        assert match.group(1).upper() == expected.upper()

    def test_no_pic(self) -> None:
        """Test lines without PIC clause."""
        assert PIC_PATTERN.search("01 GROUP-FIELD.") is None


class TestPicComponents:
    """Tests for PIC component patterns."""

    @pytest.mark.parametrize(
        "pic,expected_count",
        [
            ("X(10)", 10),
            ("XXX", 3),
            ("X", 1),
            ("X(5)X(3)", 8),
        ],
    )
    def test_alpha_count(self, pic: str, expected_count: int) -> None:
        """Test counting X characters."""
        assert count_pic_chars(pic, "X") == expected_count

    @pytest.mark.parametrize(
        "pic,expected_count",
        [
            ("9(5)", 5),
            ("999", 3),
            ("9", 1),
            ("9(3)V9(2)", 5),
        ],
    )
    def test_numeric_count(self, pic: str, expected_count: int) -> None:
        """Test counting 9 characters."""
        assert count_pic_chars(pic, "9") == expected_count

    @pytest.mark.parametrize(
        "pic,is_signed",
        [
            ("S9(5)", True),
            ("9(5)", False),
            ("s9(3)v99", True),  # Lowercase
            ("X(10)", False),
        ],
    )
    def test_signed_detection(self, pic: str, is_signed: bool) -> None:
        """Test detecting signed PIC."""
        match = PIC_SIGNED.match(pic)
        assert (match is not None) == is_signed


class TestPicLength:
    """Tests for PIC length calculation."""

    @pytest.mark.parametrize(
        "pic,expected_length,expected_decimals",
        [
            ("X(10)", 10, 0),
            ("9(5)", 5, 0),
            ("S9(7)V99", 10, 2),  # 1 sign + 7 digits + 2 decimals = 10
            ("9(3)V9(2)", 5, 2),
            ("XXX", 3, 0),
            ("999V99", 5, 2),
            ("Z(5)9", 6, 0),
        ],
    )
    def test_pic_length(
        self, pic: str, expected_length: int, expected_decimals: int
    ) -> None:
        """Test calculating PIC lengths."""
        length, decimals = parse_pic_length(pic)
        assert length == expected_length
        assert decimals == expected_decimals


class TestCompPattern:
    """Tests for COMP pattern."""

    @pytest.mark.parametrize(
        "line,expected",
        [
            ("03 FIELD PIC 9(5) COMP.", "COMP"),
            ("03 FIELD PIC 9(5) COMP-3.", "COMP-3"),
            ("03 FIELD PIC 9(5) COMPUTATIONAL.", "COMPUTATIONAL"),
            ("03 FIELD PIC 9(5) COMPUTATIONAL-3.", "COMPUTATIONAL-3"),
        ],
    )
    def test_comp_detection(self, line: str, expected: str) -> None:
        """Test detecting COMP usage."""
        match = COMP_PATTERN.search(line)
        assert match is not None
        assert match.group(1).upper() == expected.upper()


class TestOccursPattern:
    """Tests for OCCURS pattern."""

    @pytest.mark.parametrize(
        "line,expected_count",
        [
            ("03 ITEMS OCCURS 10 TIMES.", "10"),
            ("03 ITEMS OCCURS 5.", "5"),
            ("03 ITEMS PIC X(10) OCCURS 3 TIMES.", "3"),
        ],
    )
    def test_occurs_detection(self, line: str, expected_count: str) -> None:
        """Test detecting OCCURS clause."""
        match = OCCURS_PATTERN.search(line)
        assert match is not None
        assert match.group(1) == expected_count


class TestRedefinesPattern:
    """Tests for REDEFINES pattern."""

    @pytest.mark.parametrize(
        "line,expected_target",
        [
            ("03 NEW-FIELD REDEFINES OLD-FIELD.", "OLD-FIELD"),
            ("03 FIELD-B PIC X(10) REDEFINES FIELD-A.", "FIELD-A"),
        ],
    )
    def test_redefines_detection(self, line: str, expected_target: str) -> None:
        """Test detecting REDEFINES clause."""
        match = REDEFINES_PATTERN.search(line)
        assert match is not None
        assert match.group(1).upper() == expected_target.upper()


class TestNormalizeUsage:
    """Tests for usage normalization."""

    @pytest.mark.parametrize(
        "usage,expected",
        [
            ("COMP", "COMP"),
            ("COMPUTATIONAL", "COMP"),
            ("COMP-3", "COMP-3"),
            ("COMPUTATIONAL-3", "COMP-3"),
            ("BINARY", "COMP"),
            ("PACKED-DECIMAL", "COMP-3"),
            ("DISPLAY", "DISPLAY"),
        ],
    )
    def test_normalize_usage(self, usage: str, expected: str) -> None:
        """Test normalizing usage strings."""
        assert normalize_usage(usage) == expected
