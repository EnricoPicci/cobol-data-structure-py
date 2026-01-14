"""
Tests for Phase 3.2: PIC Clause Parser.

Tests for PIC and USAGE clause detection and parsing.
"""

from cobol_anonymizer.cobol.pic_parser import (
    PICType,
    UsageType,
    calculate_pic_length,
    determine_pic_type,
    extract_pic_from_line,
    find_pic_clauses,
    find_usage_clauses,
    get_protected_ranges,
    has_external_clause,
    has_global_clause,
    has_occurs_clause,
    has_redefines_clause,
    has_value_clause,
    is_in_pic_clause,
    is_protected_position,
)


class TestFindPICClauses:
    """Tests for finding PIC clauses in lines."""

    def test_find_pic_x_simple(self):
        """Find simple PIC X clause."""
        line = "05 WS-FIELD PIC X."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 1
        assert clauses[0].pattern == "X"  # Period is not part of pattern

    def test_find_pic_x_with_length(self):
        """Find PIC X(n) clause."""
        line = "05 WS-FIELD PIC X(30)."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 1
        assert clauses[0].pattern == "X(30)"  # Period is not part of pattern
        assert clauses[0].length == 30

    def test_find_pic_9(self):
        """Find PIC 9(n) clause."""
        line = "05 WS-COUNT PIC 9(5)."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 1
        assert "9(5)" in clauses[0].pattern
        assert clauses[0].length == 5

    def test_find_pic_s9(self):
        """Find PIC S9(n) clause (signed)."""
        line = "05 WS-AMOUNT PIC S9(7)."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 1
        assert clauses[0].pic_type == PICType.SIGN

    def test_find_pic_s9v99(self):
        """Find PIC S9(n)V99 clause (decimal)."""
        line = "05 WS-AMOUNT PIC S9(7)V99."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 1
        assert "V99" in clauses[0].pattern.upper()

    def test_find_pic_z(self):
        """Find edited numeric PIC Z(n)9."""
        line = "05 WS-EDITED PIC Z(5)9."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 1
        assert clauses[0].pic_type == PICType.EDITED_NUMERIC

    def test_find_picture_keyword(self):
        """Find PICTURE keyword (full form)."""
        line = "05 WS-FIELD PICTURE X(10)."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 1
        assert clauses[0].length == 10

    def test_find_picture_is(self):
        """Find PICTURE IS clause."""
        line = "05 WS-FIELD PICTURE IS X(10)."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 1

    def test_find_pic_is(self):
        """Find PIC IS clause."""
        line = "05 WS-FIELD PIC IS X(10)."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 1

    def test_find_multiple_pic_clauses(self):
        """Find multiple PIC clauses on one line (rare but valid)."""
        # This could happen with 88 levels or certain constructs
        line = "05 FIELD-A PIC X(5). 05 FIELD-B PIC 9(3)."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 2

    def test_find_no_pic_clause(self):
        """No PIC clause found."""
        line = "05 WS-RECORD."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 0

    def test_pic_case_insensitive(self):
        """PIC detection is case-insensitive."""
        lines = [
            "05 FIELD pic x(10).",
            "05 FIELD Pic X(10).",
            "05 FIELD PIC X(10).",
        ]
        for line in lines:
            clauses = find_pic_clauses(line)
            assert len(clauses) == 1


class TestFindUsageClauses:
    """Tests for finding USAGE clauses."""

    def test_find_usage_comp(self):
        """Find USAGE COMP clause."""
        line = "05 WS-FIELD PIC S9(9) COMP."
        clauses = find_usage_clauses(line)
        assert len(clauses) == 1
        assert clauses[0].usage_type == UsageType.COMP

    def test_find_usage_comp_3(self):
        """Find USAGE COMP-3 clause."""
        line = "05 WS-AMOUNT PIC S9(7)V99 COMP-3."
        clauses = find_usage_clauses(line)
        assert len(clauses) == 1
        assert clauses[0].usage_type == UsageType.COMP_3

    def test_find_usage_computational_3(self):
        """Find COMPUTATIONAL-3 (full form)."""
        line = "05 WS-AMOUNT PIC S9(7)V99 COMPUTATIONAL-3."
        clauses = find_usage_clauses(line)
        assert len(clauses) == 1
        assert clauses[0].usage_type == UsageType.COMP_3

    def test_find_usage_binary(self):
        """Find USAGE BINARY clause."""
        line = "05 WS-INDEX PIC S9(9) BINARY."
        clauses = find_usage_clauses(line)
        assert len(clauses) == 1
        assert clauses[0].usage_type == UsageType.BINARY

    def test_find_usage_display(self):
        """Find USAGE DISPLAY clause."""
        line = "05 WS-FIELD PIC X(10) DISPLAY."
        clauses = find_usage_clauses(line)
        assert len(clauses) == 1
        assert clauses[0].usage_type == UsageType.DISPLAY

    def test_find_usage_is(self):
        """Find USAGE IS clause."""
        line = "05 WS-FIELD PIC S9(5) USAGE IS COMP-3."
        clauses = find_usage_clauses(line)
        assert len(clauses) >= 1

    def test_find_usage_index(self):
        """Find USAGE INDEX clause."""
        line = "05 WS-IDX USAGE INDEX."
        clauses = find_usage_clauses(line)
        assert len(clauses) == 1
        assert clauses[0].usage_type == UsageType.INDEX

    def test_find_no_usage_clause(self):
        """No USAGE clause found (default DISPLAY)."""
        line = "05 WS-FIELD PIC X(10)."
        clauses = find_usage_clauses(line)
        # DISPLAY might appear as the implicit default
        # But if not explicitly stated, might not match
        # Test depends on pattern - adjust if needed
        assert len(clauses) == 0  # No explicit USAGE


class TestCalculatePICLength:
    """Tests for PIC length calculation."""

    def test_length_x_simple(self):
        """Calculate length for PIC X."""
        assert calculate_pic_length("X") == 1

    def test_length_x_with_count(self):
        """Calculate length for PIC X(30)."""
        assert calculate_pic_length("X(30)") == 30

    def test_length_9_simple(self):
        """Calculate length for PIC 9."""
        assert calculate_pic_length("9") == 1

    def test_length_9_with_count(self):
        """Calculate length for PIC 9(5)."""
        assert calculate_pic_length("9(5)") == 5

    def test_length_s9_signed(self):
        """Calculate length for PIC S9(7) - S doesn't add length."""
        assert calculate_pic_length("S9(7)") == 7

    def test_length_s9v99_decimal(self):
        """Calculate length for PIC S9(5)V99 - V doesn't add length."""
        assert calculate_pic_length("S9(5)V99") == 7  # 5 + 2

    def test_length_z_edited(self):
        """Calculate length for PIC Z(5)9."""
        assert calculate_pic_length("Z(5)9") == 6  # 5 + 1

    def test_length_mixed(self):
        """Calculate length for complex pattern."""
        assert calculate_pic_length("X(10)9(5)") == 15


class TestDeterminePICType:
    """Tests for determining PIC type."""

    def test_type_alphanumeric(self):
        """X pattern is alphanumeric."""
        assert determine_pic_type("X(10)") == PICType.ALPHANUMERIC

    def test_type_numeric(self):
        """9 pattern is numeric."""
        assert determine_pic_type("9(5)") == PICType.NUMERIC

    def test_type_alphabetic(self):
        """A pattern is alphabetic."""
        assert determine_pic_type("A(10)") == PICType.ALPHABETIC

    def test_type_signed(self):
        """S9 pattern is signed."""
        assert determine_pic_type("S9(7)") == PICType.SIGN

    def test_type_decimal(self):
        """V in pattern indicates decimal."""
        assert determine_pic_type("9(5)V99") == PICType.DECIMAL

    def test_type_edited(self):
        """Z pattern is edited."""
        assert determine_pic_type("Z(5)9") == PICType.EDITED_NUMERIC


class TestIsInPICClause:
    """Tests for checking if position is in PIC clause."""

    def test_position_in_pic(self):
        """Position within PIC clause returns True."""
        line = "05 WS-FIELD PIC X(30)."
        # Find where PIC starts
        pic_start = line.index("PIC")
        assert is_in_pic_clause(line, pic_start)
        assert is_in_pic_clause(line, pic_start + 5)  # In pattern

    def test_position_before_pic(self):
        """Position before PIC clause returns False."""
        line = "05 WS-FIELD PIC X(30)."
        assert not is_in_pic_clause(line, 0)  # In level number
        assert not is_in_pic_clause(line, 5)  # In field name

    def test_position_no_pic(self):
        """Position in line without PIC returns False."""
        line = "05 WS-RECORD."
        assert not is_in_pic_clause(line, 5)


class TestProtectedRanges:
    """Tests for getting protected ranges."""

    def test_protected_ranges_pic_only(self):
        """Get protected ranges for PIC clause."""
        line = "05 WS-FIELD PIC X(30)."
        ranges = get_protected_ranges(line)
        assert len(ranges) >= 1

    def test_protected_ranges_pic_and_usage(self):
        """Get protected ranges for PIC and USAGE."""
        line = "05 WS-AMOUNT PIC S9(7)V99 COMP-3."
        ranges = get_protected_ranges(line)
        assert len(ranges) >= 2  # At least PIC and COMP-3

    def test_is_protected_position(self):
        """is_protected_position returns True for PIC/USAGE."""
        line = "05 WS-FIELD PIC X(30) COMP."
        pic_start = line.index("PIC")
        assert is_protected_position(line, pic_start)


class TestExtractPIC:
    """Tests for extracting PIC patterns."""

    def test_extract_pic_simple(self):
        """Extract PIC pattern from line."""
        line = "05 WS-FIELD PIC X(30)."
        pattern = extract_pic_from_line(line)
        assert pattern is not None
        assert "X(30)" in pattern

    def test_extract_pic_none(self):
        """Return None when no PIC found."""
        line = "05 WS-RECORD."
        pattern = extract_pic_from_line(line)
        assert pattern is None


class TestClauseDetection:
    """Tests for detecting various COBOL clauses."""

    def test_has_value_clause_present(self):
        """Detect VALUE clause."""
        assert has_value_clause("05 WS-FLAG PIC X VALUE 'Y'.")
        assert has_value_clause("05 WS-FLAG PIC X VALUE IS 'Y'.")

    def test_has_value_clause_absent(self):
        """No VALUE clause."""
        assert not has_value_clause("05 WS-FIELD PIC X(30).")

    def test_has_redefines_clause_present(self):
        """Detect REDEFINES clause."""
        assert has_redefines_clause("05 WS-X REDEFINES WS-Y PIC X(10).")

    def test_has_redefines_clause_absent(self):
        """No REDEFINES clause."""
        assert not has_redefines_clause("05 WS-FIELD PIC X(30).")

    def test_has_occurs_clause_present(self):
        """Detect OCCURS clause."""
        assert has_occurs_clause("05 WS-TABLE OCCURS 10 TIMES.")
        assert has_occurs_clause("05 WS-ARRAY OCCURS 5 TO 100 DEPENDING ON WS-COUNT.")

    def test_has_occurs_clause_absent(self):
        """No OCCURS clause."""
        assert not has_occurs_clause("05 WS-FIELD PIC X(30).")

    def test_has_external_clause_present(self):
        """Detect EXTERNAL clause."""
        assert has_external_clause("01 SHARED-AREA EXTERNAL.")
        assert has_external_clause("01 WS-COMMON IS EXTERNAL.")

    def test_has_external_clause_absent(self):
        """No EXTERNAL clause."""
        assert not has_external_clause("01 WS-RECORD.")

    def test_has_global_clause_present(self):
        """Detect GLOBAL clause."""
        assert has_global_clause("01 GLOBAL-AREA GLOBAL.")

    def test_has_global_clause_absent(self):
        """No GLOBAL clause."""
        assert not has_global_clause("01 WS-RECORD.")


class TestRealWorldPICPatterns:
    """Tests using realistic PIC patterns from COBOL files."""

    def test_complex_numeric_edited(self):
        """Parse complex edited numeric pattern."""
        line = "05 WS-AMOUNT-ED PIC -(7)9.99."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 1
        assert clauses[0].pic_type == PICType.EDITED_NUMERIC

    def test_group_level_no_pic(self):
        """Group level items have no PIC."""
        line = "01 WS-CUSTOMER-RECORD."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 0

    def test_88_level_no_pic(self):
        """88 level condition names have no PIC."""
        line = "88 WS-VALID VALUE 'Y'."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 0

    def test_pic_with_trailing_period(self):
        """Handle PIC with period immediately after."""
        line = "05 WS-FIELD PIC X."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 1
        assert clauses[0].length == 1

    def test_pic_in_copy_file(self):
        """PIC patterns as found in copybooks."""
        lines = [
            "           05 Q130-NUMERO-POLIZZA         PIC X(20).",
            "           05 Q130-CODICE-CLIENTE         PIC 9(10).",
            "           05 Q130-IMPORTO-PREMIO         PIC S9(13)V99 COMP-3.",
        ]
        for line in lines:
            clauses = find_pic_clauses(line)
            assert len(clauses) == 1

    def test_pic_alphabetic(self):
        """PIC A (alphabetic only)."""
        line = "05 WS-INITIALS PIC A(3)."
        clauses = find_pic_clauses(line)
        assert len(clauses) == 1
        assert clauses[0].pic_type == PICType.ALPHABETIC
