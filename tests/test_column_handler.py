"""
Tests for Phase 2: COBOL Column Handler.

Tests for fixed-format line parsing, reconstruction, and validation.
"""

import pytest

from cobol_anonymizer.cobol.column_handler import (
    COBOLLine,
    IndicatorType,
    CHANGE_TAGS,
    detect_change_tag,
    parse_line,
    reconstruct_line,
    reconstruct_line_with_ending,
    validate_code_area,
    extract_line_ending,
    parse_file_line,
    get_code_start_column,
    is_area_a_content,
)
from cobol_anonymizer.exceptions import ColumnOverflowError


class TestCOBOLLineDataclass:
    """Tests for the COBOLLine dataclass."""

    def test_cobol_line_basic_creation(self):
        """COBOLLine can be created with all fields."""
        line = COBOLLine(
            raw="      *COMMENT",
            line_number=1,
            sequence="      ",
            indicator="*",
            area_a="COMM",
            area_b="ENT" + " " * 58,
            identification="        ",
            original_length=14,
            line_ending="\n",
            has_change_tag=False,
        )
        assert line.line_number == 1
        assert line.indicator == "*"

    def test_is_comment_star(self):
        """Line with * indicator is a comment."""
        line = parse_line("      *COMMENT LINE")
        assert line.is_comment

    def test_is_comment_slash(self):
        """Line with / indicator is a comment (page eject)."""
        line = parse_line("      /PAGE EJECT")
        assert line.is_comment

    def test_is_not_comment(self):
        """Normal code line is not a comment."""
        line = parse_line("       01 WS-FIELD PIC X.")
        assert not line.is_comment

    def test_is_continuation(self):
        """Line with - indicator is continuation."""
        line = parse_line("      -    'CONTINUED'")
        assert line.is_continuation

    def test_is_debug(self):
        """Line with D indicator is debug."""
        line = parse_line("      D    DISPLAY 'DEBUG'")
        assert line.is_debug

    def test_is_blank(self):
        """Empty code area is blank."""
        line = parse_line("      ")
        assert line.is_blank

    def test_code_area_combined(self):
        """code_area combines area_a and area_b."""
        line = parse_line("       01 WS-FIELD            PIC X(10).")
        assert "01 WS-FIELD" in line.code_area

    def test_indicator_type_enum(self):
        """get_indicator_type returns correct enum."""
        assert parse_line("      *COMMENT").get_indicator_type() == IndicatorType.COMMENT
        assert parse_line("      /PAGE").get_indicator_type() == IndicatorType.PAGE
        assert parse_line("      D DEBUG").get_indicator_type() == IndicatorType.DEBUG
        assert parse_line("      -CONT").get_indicator_type() == IndicatorType.CONTINUATION
        assert parse_line("       CODE").get_indicator_type() == IndicatorType.BLANK


class TestParseStandardLine:
    """Tests for parsing standard COBOL lines."""

    def test_parse_standard_line(self):
        """Parse a typical 80-column COBOL line."""
        line = "000100       01 WS-RECORD                                                   TEST"
        parsed = parse_line(line)
        assert parsed.sequence == "000100"
        assert parsed.indicator == " "
        assert "01 WS-RECORD" in parsed.code_area
        assert parsed.identification.strip() == "TEST"

    def test_parse_comment_line(self):
        """Parse line with * in column 7."""
        line = "      *    THIS IS A COMMENT LINE"
        parsed = parse_line(line)
        assert parsed.indicator == "*"
        assert parsed.is_comment
        assert "THIS IS A COMMENT" in parsed.code_area

    def test_parse_preserves_sequence_numbers(self):
        """Sequence numbers are preserved exactly."""
        line = "123456 01 LEVEL."
        parsed = parse_line(line)
        assert parsed.sequence == "123456"

    def test_parse_preserves_indicator(self):
        """Indicator character is preserved exactly."""
        indicators = [" ", "*", "/", "D", "-"]
        for ind in indicators:
            line = f"      {ind}CODE"
            parsed = parse_line(line)
            assert parsed.indicator == ind


class TestParseShortLines:
    """Tests for handling short lines."""

    def test_parse_short_line(self):
        """Handle lines shorter than 80 characters."""
        line = "       05 FIELD"
        parsed = parse_line(line)
        assert "FIELD" in parsed.code_area
        assert parsed.original_length == 15

    def test_parse_very_short_line(self):
        """Handle very short lines."""
        line = "      *"
        parsed = parse_line(line)
        assert parsed.is_comment
        assert parsed.original_length == 7

    def test_parse_empty_line(self):
        """Handle empty lines without error."""
        line = ""
        parsed = parse_line(line)
        assert parsed.is_blank
        assert parsed.original_length == 0

    def test_parse_whitespace_only_line(self):
        """Handle whitespace-only lines."""
        line = "        "
        parsed = parse_line(line)
        assert parsed.is_blank


class TestParseLongLines:
    """Tests for handling long lines."""

    def test_parse_80_column_line(self):
        """Parse exactly 80-column line."""
        line = "0" * 80
        parsed = parse_line(line)
        assert parsed.original_length == 80
        assert len(parsed.sequence) == 6
        assert len(parsed.identification) == 8

    def test_parse_longer_than_80(self):
        """Handle lines longer than 80 columns."""
        line = "X" * 100
        parsed = parse_line(line)
        assert parsed.original_length == 100
        # Standard areas are still 80 chars
        assert len(parsed.sequence + parsed.indicator +
                   parsed.area_a + parsed.area_b + parsed.identification) == 80


class TestParseChangeTags:
    """Tests for change tag detection."""

    def test_parse_change_tag_beniq(self):
        """Detect BENIQ change tag in sequence area."""
        line = "BENIQ  01 RECORD."
        parsed = parse_line(line)
        assert parsed.has_change_tag
        assert parsed.change_tag == "BENIQ"

    def test_parse_change_tag_cdr(self):
        """Detect CDR change tag in sequence area."""
        line = "CDR    05 FIELD."
        parsed = parse_line(line)
        assert parsed.has_change_tag
        assert parsed.change_tag == "CDR"

    def test_parse_change_tag_dm2724(self):
        """Detect DM2724 change tag in sequence area."""
        line = "DM2724 01 REC."
        parsed = parse_line(line)
        assert parsed.has_change_tag
        assert parsed.change_tag == "DM2724"

    def test_parse_change_tag_replat(self):
        """Detect REPLAT change tag in sequence area."""
        line = "REPLAT 01 REC."
        parsed = parse_line(line)
        assert parsed.has_change_tag
        assert parsed.change_tag == "REPLAT"

    def test_parse_no_change_tag(self):
        """Normal sequence number is not a change tag."""
        line = "000100 01 RECORD."
        parsed = parse_line(line)
        assert not parsed.has_change_tag
        assert parsed.change_tag is None

    def test_detect_change_tag_function(self):
        """detect_change_tag function works correctly."""
        assert detect_change_tag("BENIQ ") == "BENIQ"
        assert detect_change_tag("CDR   ") == "CDR"
        assert detect_change_tag("000100") is None


class TestPreserveOriginalLength:
    """Tests for preserving original line length."""

    def test_preserve_original_length(self):
        """original_length field matches input line length."""
        for length in [0, 7, 15, 40, 72, 80, 100]:
            line = "X" * length
            parsed = parse_line(line)
            assert parsed.original_length == length

    def test_preserve_length_after_tab_conversion(self):
        """Original length preserved even with tabs."""
        line = "\t\tCODE"
        parsed = parse_line(line)
        assert parsed.original_length == 6  # Original length, not expanded


class TestLineEndings:
    """Tests for line ending preservation."""

    def test_preserve_line_ending_unix(self):
        """Preserve \\n line ending."""
        content, ending = extract_line_ending("       CODE\n")
        assert content == "       CODE"
        assert ending == "\n"

    def test_preserve_line_ending_windows(self):
        """Preserve \\r\\n line ending."""
        content, ending = extract_line_ending("       CODE\r\n")
        assert content == "       CODE"
        assert ending == "\r\n"

    def test_preserve_line_ending_old_mac(self):
        """Preserve \\r line ending (old Mac format)."""
        content, ending = extract_line_ending("       CODE\r")
        assert content == "       CODE"
        assert ending == "\r"

    def test_preserve_no_line_ending(self):
        """Handle last line without ending."""
        content, ending = extract_line_ending("       CODE")
        assert content == "       CODE"
        assert ending == ""

    def test_parse_file_line_with_unix_ending(self):
        """parse_file_line handles Unix line endings."""
        parsed = parse_file_line("       05 FIELD.\n")
        assert parsed.line_ending == "\n"

    def test_parse_file_line_with_windows_ending(self):
        """parse_file_line handles Windows line endings."""
        parsed = parse_file_line("       05 FIELD.\r\n")
        assert parsed.line_ending == "\r\n"


class TestReconstructLine:
    """Tests for line reconstruction."""

    def test_reconstruct_preserves_columns(self):
        """Round-trip parsing maintains exact format."""
        original = "000100 01 WS-RECORD                                                        TEST"
        parsed = parse_line(original)
        reconstructed = reconstruct_line(parsed, preserve_length=False)
        # Compare meaningful parts (trimmed)
        assert reconstructed.strip() == original.strip()

    def test_reconstruct_preserves_length(self):
        """Reconstruction preserves original length."""
        original = "       05 FIELD."
        parsed = parse_line(original)
        reconstructed = reconstruct_line(parsed, preserve_length=True)
        assert len(reconstructed) == len(original)

    def test_reconstruct_with_ending(self):
        """Reconstruction includes line ending."""
        parsed = parse_file_line("       05 FIELD.\n")
        reconstructed = reconstruct_line_with_ending(parsed)
        assert reconstructed.endswith("\n")

    def test_roundtrip_short_line(self):
        """Short line survives round-trip."""
        original = "      *COMMENT"
        parsed = parse_line(original)
        reconstructed = reconstruct_line(parsed, preserve_length=True)
        assert len(reconstructed) == len(original)

    def test_roundtrip_80_column_line(self):
        """80-column line survives round-trip."""
        # Build a proper 80-column line
        original = "000100       05 WS-FIELD-NAME                  PIC X(10).                   TEST"
        assert len(original) == 80
        parsed = parse_line(original)
        reconstructed = reconstruct_line(parsed, preserve_length=True)
        assert len(reconstructed) == 80
        assert reconstructed == original


class TestValidateCodeArea:
    """Tests for code area validation."""

    def test_validate_code_area_within_limit(self):
        """Accept code area within 65 characters."""
        line = "       05 WS-FIELD PIC X(10)."
        parsed = parse_line(line, 1)
        # Should not raise
        validate_code_area(parsed)

    def test_validate_code_area_exactly_65(self):
        """Accept code area at exactly 65 characters."""
        # Area A (4 chars) + Area B (61 chars) = 65 chars
        area_a = "CODE"
        area_b = "X" * 61
        line = f"      {' '}{area_a}{area_b}"
        parsed = parse_line(line, 1)
        validate_code_area(parsed)

    def test_validate_code_area_overflow(self):
        """Raise ColumnOverflowError when exceeding column 72."""
        # Create a normal line, then validate proposed new content that overflows
        line = "       05 FIELD PIC X."
        parsed = parse_line(line, 10)

        # Propose new content that exceeds 65 characters
        overflow_content = "X" * 70

        with pytest.raises(ColumnOverflowError) as exc_info:
            validate_code_area(parsed, "TEST.cob", new_code_content=overflow_content)

        assert exc_info.value.line == 10
        assert exc_info.value.actual_length == 70
        assert exc_info.value.max_length == 65

    def test_validate_code_area_includes_file_name(self):
        """ColumnOverflowError includes file name."""
        line = "       05 FIELD."
        parsed = parse_line(line, 5)

        overflow_content = "X" * 70

        with pytest.raises(ColumnOverflowError) as exc_info:
            validate_code_area(parsed, "PROGRAM.cob", new_code_content=overflow_content)

        assert "PROGRAM.cob" in str(exc_info.value)


class TestMalformedLines:
    """Tests for handling malformed input."""

    def test_parse_malformed_line(self):
        """Handle lines with unexpected format gracefully."""
        # Line with only partial content
        line = "ABC"
        parsed = parse_line(line)
        assert parsed.sequence == "ABC   "  # Padded to 6 chars
        assert parsed.original_length == 3

    def test_parse_line_with_tabs(self):
        """Handle lines containing tab characters."""
        line = "\t\t05 FIELD."
        parsed = parse_line(line)
        # Tabs are converted to spaces internally
        assert "FIELD" in parsed.code_area

    def test_parse_unicode_content(self):
        """Handle lines with unicode characters."""
        # Column 7 must have the asterisk for it to be a comment
        line = "      * COMMENT: résumé"  # 6 spaces + asterisk
        parsed = parse_line(line)
        assert parsed.is_comment


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_code_start_column_area_a(self):
        """get_code_start_column for Area A content."""
        line = "       01 RECORD."
        parsed = parse_line(line)
        assert get_code_start_column(parsed) == 8

    def test_get_code_start_column_area_b(self):
        """get_code_start_column for Area B content."""
        line = "           05 FIELD."
        parsed = parse_line(line)
        # Content starts at column 12 (Area B)
        assert get_code_start_column(parsed) == 12

    def test_is_area_a_content_true(self):
        """is_area_a_content returns True for Area A entries."""
        line = "       01 RECORD."
        parsed = parse_line(line)
        assert is_area_a_content(parsed)

    def test_is_area_a_content_false(self):
        """is_area_a_content returns False for Area B entries."""
        line = "           05 FIELD."
        parsed = parse_line(line)
        assert not is_area_a_content(parsed)


class TestRealWorldExamples:
    """Tests using realistic COBOL patterns."""

    def test_parse_division_header(self):
        """Parse IDENTIFICATION DIVISION header."""
        line = "       IDENTIFICATION DIVISION."
        parsed = parse_line(line)
        assert "IDENTIFICATION DIVISION" in parsed.code_area
        assert is_area_a_content(parsed)

    def test_parse_program_id(self):
        """Parse PROGRAM-ID statement."""
        line = "       PROGRAM-ID.    TESTPROG."
        parsed = parse_line(line)
        assert "PROGRAM-ID" in parsed.code_area

    def test_parse_data_definition_01(self):
        """Parse 01 level data definition."""
        line = "       01  WS-RECORD."
        parsed = parse_line(line)
        assert "01" in parsed.code_area
        assert is_area_a_content(parsed)

    def test_parse_data_definition_05(self):
        """Parse 05 level data definition."""
        line = "           05 WS-FIELD           PIC X(10)."
        parsed = parse_line(line)
        assert "05 WS-FIELD" in parsed.code_area
        assert not is_area_a_content(parsed)

    def test_parse_level_88(self):
        """Parse 88 level condition."""
        line = "              88 WS-VALID        VALUE 'Y'."
        parsed = parse_line(line)
        assert "88" in parsed.code_area

    def test_parse_copy_statement(self):
        """Parse COPY statement."""
        line = "       COPY SAMPLE01."
        parsed = parse_line(line)
        assert "COPY SAMPLE01" in parsed.code_area

    def test_parse_move_statement(self):
        """Parse MOVE statement."""
        line = "           MOVE SPACES TO WS-FIELD."
        parsed = parse_line(line)
        assert "MOVE SPACES TO WS-FIELD" in parsed.code_area

    def test_parse_perform_statement(self):
        """Parse PERFORM statement."""
        line = "           PERFORM A001-INIT THRU A001-EXIT."
        parsed = parse_line(line)
        assert "PERFORM A001-INIT" in parsed.code_area

    def test_parse_continuation_literal(self):
        """Parse string literal continuation."""
        line1 = "           DISPLAY 'THIS IS A LONG STRING THAT"
        line2 = "      -    'CONTINUES ON NEXT LINE'."
        parsed1 = parse_line(line1)
        parsed2 = parse_line(line2)
        assert not parsed1.is_continuation
        assert parsed2.is_continuation
