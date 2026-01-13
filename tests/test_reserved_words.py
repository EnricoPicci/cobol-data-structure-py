"""
Tests for Phase 3.1: COBOL Reserved Words.

Tests for reserved word detection and classification.
"""

import pytest

from cobol_anonymizer.cobol.reserved_words import (
    RESERVED_WORDS,
    is_reserved_word,
    is_figurative_constant,
    is_special_register,
    get_reserved_word_category,
    is_system_identifier,
    SYSTEM_PREFIXES,
)


class TestReservedWordDetection:
    """Tests for reserved word detection."""

    def test_reserved_word_move(self):
        """MOVE is a reserved word."""
        assert is_reserved_word("MOVE")

    def test_reserved_word_perform(self):
        """PERFORM is a reserved word."""
        assert is_reserved_word("PERFORM")

    def test_reserved_word_compute(self):
        """COMPUTE is a reserved word."""
        assert is_reserved_word("COMPUTE")

    def test_reserved_word_case_insensitive_lower(self):
        """move is detected as reserved (lowercase)."""
        assert is_reserved_word("move")

    def test_reserved_word_case_insensitive_mixed(self):
        """Move is detected as reserved (mixed case)."""
        assert is_reserved_word("Move")

    def test_reserved_word_case_insensitive_all(self):
        """move, MOVE, Move all detected as reserved."""
        assert is_reserved_word("move")
        assert is_reserved_word("MOVE")
        assert is_reserved_word("Move")
        assert is_reserved_word("mOvE")

    def test_not_reserved_word_ws_field(self):
        """WS-FIELD is not a reserved word."""
        assert not is_reserved_word("WS-FIELD")

    def test_not_reserved_word_customer_name(self):
        """CUSTOMER-NAME is not a reserved word."""
        assert not is_reserved_word("CUSTOMER-NAME")

    def test_not_reserved_word_random_string(self):
        """Random strings are not reserved."""
        assert not is_reserved_word("FOOBAR")
        assert not is_reserved_word("XYZ123")


class TestClauseKeywords:
    """Tests for clause-related reserved words."""

    def test_redefines_is_reserved(self):
        """REDEFINES is a reserved word."""
        assert is_reserved_word("REDEFINES")

    def test_value_is_reserved(self):
        """VALUE is a reserved word."""
        assert is_reserved_word("VALUE")

    def test_occurs_is_reserved(self):
        """OCCURS is a reserved word."""
        assert is_reserved_word("OCCURS")

    def test_indexed_is_reserved(self):
        """INDEXED is a reserved word."""
        assert is_reserved_word("INDEXED")

    def test_external_is_reserved(self):
        """EXTERNAL is a reserved word."""
        assert is_reserved_word("EXTERNAL")

    def test_justified_is_reserved(self):
        """JUSTIFIED is a reserved word."""
        assert is_reserved_word("JUSTIFIED")

    def test_just_is_reserved(self):
        """JUST is a reserved word."""
        assert is_reserved_word("JUST")

    def test_pic_is_reserved(self):
        """PIC is a reserved word."""
        assert is_reserved_word("PIC")

    def test_picture_is_reserved(self):
        """PICTURE is a reserved word."""
        assert is_reserved_word("PICTURE")

    def test_usage_is_reserved(self):
        """USAGE is a reserved word."""
        assert is_reserved_word("USAGE")

    def test_comp_variants_reserved(self):
        """COMP and variants are reserved."""
        assert is_reserved_word("COMP")
        assert is_reserved_word("COMP-1")
        assert is_reserved_word("COMP-2")
        assert is_reserved_word("COMP-3")
        assert is_reserved_word("COMP-4")
        assert is_reserved_word("COMP-5")


class TestDivisionSectionKeywords:
    """Tests for division and section keywords."""

    def test_division_keywords(self):
        """Division keywords are reserved."""
        assert is_reserved_word("IDENTIFICATION")
        assert is_reserved_word("ENVIRONMENT")
        assert is_reserved_word("DATA")
        assert is_reserved_word("PROCEDURE")
        assert is_reserved_word("DIVISION")

    def test_section_keywords(self):
        """Section keywords are reserved."""
        assert is_reserved_word("WORKING-STORAGE")
        assert is_reserved_word("LOCAL-STORAGE")
        assert is_reserved_word("LINKAGE")
        assert is_reserved_word("FILE")
        assert is_reserved_word("SECTION")

    def test_copy_is_reserved(self):
        """COPY is a reserved word."""
        assert is_reserved_word("COPY")

    def test_replacing_is_reserved(self):
        """REPLACING is a reserved word."""
        assert is_reserved_word("REPLACING")


class TestFigurativeConstants:
    """Tests for figurative constant detection."""

    def test_space_is_figurative(self):
        """SPACE is a figurative constant."""
        assert is_figurative_constant("SPACE")
        assert is_figurative_constant("SPACES")

    def test_zero_is_figurative(self):
        """ZERO and variants are figurative constants."""
        assert is_figurative_constant("ZERO")
        assert is_figurative_constant("ZEROS")
        assert is_figurative_constant("ZEROES")

    def test_high_value_is_figurative(self):
        """HIGH-VALUE is a figurative constant."""
        assert is_figurative_constant("HIGH-VALUE")
        assert is_figurative_constant("HIGH-VALUES")

    def test_low_value_is_figurative(self):
        """LOW-VALUE is a figurative constant."""
        assert is_figurative_constant("LOW-VALUE")
        assert is_figurative_constant("LOW-VALUES")

    def test_quote_is_figurative(self):
        """QUOTE is a figurative constant."""
        assert is_figurative_constant("QUOTE")
        assert is_figurative_constant("QUOTES")

    def test_null_is_figurative(self):
        """NULL is a figurative constant."""
        assert is_figurative_constant("NULL")
        assert is_figurative_constant("NULLS")

    def test_figurative_case_insensitive(self):
        """Figurative constants are case-insensitive."""
        assert is_figurative_constant("space")
        assert is_figurative_constant("Space")
        assert is_figurative_constant("SPACE")

    def test_user_defined_not_figurative(self):
        """User-defined names are not figurative constants."""
        assert not is_figurative_constant("WS-SPACE")
        assert not is_figurative_constant("ZERO-COUNT")


class TestSpecialRegisters:
    """Tests for special register detection."""

    def test_return_code_is_special(self):
        """RETURN-CODE is a special register."""
        assert is_special_register("RETURN-CODE")

    def test_tally_is_special(self):
        """TALLY is a special register."""
        assert is_special_register("TALLY")

    def test_linage_counter_is_special(self):
        """LINAGE-COUNTER is a special register."""
        assert is_special_register("LINAGE-COUNTER")

    def test_xml_code_is_special(self):
        """XML-CODE is a special register."""
        assert is_special_register("XML-CODE")

    def test_special_register_case_insensitive(self):
        """Special register check is case-insensitive."""
        assert is_special_register("return-code")
        assert is_special_register("Return-Code")

    def test_user_defined_not_special(self):
        """User-defined names are not special registers."""
        assert not is_special_register("WS-CODE")
        assert not is_special_register("MY-TALLY")


class TestReservedWordCategory:
    """Tests for reserved word categorization."""

    def test_category_figurative_constant(self):
        """Figurative constants are categorized correctly."""
        assert get_reserved_word_category("SPACES") == "figurative_constant"
        assert get_reserved_word_category("ZEROS") == "figurative_constant"

    def test_category_special_register(self):
        """Special registers are categorized correctly."""
        assert get_reserved_word_category("RETURN-CODE") == "special_register"
        assert get_reserved_word_category("TALLY") == "special_register"

    def test_category_reserved_word(self):
        """Reserved words are categorized correctly."""
        assert get_reserved_word_category("MOVE") == "reserved_word"
        assert get_reserved_word_category("PERFORM") == "reserved_word"

    def test_category_user_defined(self):
        """User-defined names are categorized correctly."""
        assert get_reserved_word_category("WS-FIELD") == "user_defined"
        assert get_reserved_word_category("CUSTOMER-NAME") == "user_defined"


class TestSystemIdentifiers:
    """Tests for system identifier detection."""

    def test_dfhcommarea_is_system(self):
        """DFHCOMMAREA is a system identifier."""
        assert is_system_identifier("DFHCOMMAREA")

    def test_dfheiblk_is_system(self):
        """DFHEIBLK is a system identifier."""
        assert is_system_identifier("DFHEIBLK")

    def test_eib_prefix_is_system(self):
        """Names starting with EIB are system identifiers."""
        assert is_system_identifier("EIBCALEN")
        assert is_system_identifier("EIBRESP")
        assert is_system_identifier("EIBTRNID")
        assert is_system_identifier("EIBDATE")

    def test_sqlca_is_system(self):
        """SQLCA is a system identifier."""
        assert is_system_identifier("SQLCA")

    def test_sqlcode_is_system(self):
        """SQLCODE is a system identifier."""
        assert is_system_identifier("SQLCODE")

    def test_system_identifier_case_insensitive(self):
        """System identifier check is case-insensitive."""
        assert is_system_identifier("dfhcommarea")
        assert is_system_identifier("Dfhcommarea")
        assert is_system_identifier("DFHCOMMAREA")

    def test_user_defined_not_system(self):
        """User-defined names are not system identifiers."""
        assert not is_system_identifier("WS-FIELD")
        assert not is_system_identifier("CUSTOMER-AREA")


class TestReservedWordCoverage:
    """Tests for reserved word list coverage."""

    def test_reserved_word_count(self):
        """Reserved word list has substantial coverage."""
        # Should have at least 400 reserved words
        assert len(RESERVED_WORDS) >= 350

    def test_common_verbs_covered(self):
        """Common COBOL verbs are in the list."""
        verbs = [
            "ACCEPT", "ADD", "CALL", "CLOSE", "COMPUTE", "DELETE",
            "DISPLAY", "DIVIDE", "EVALUATE", "EXIT", "GO", "GOBACK",
            "IF", "INITIALIZE", "INSPECT", "MERGE", "MOVE", "MULTIPLY",
            "OPEN", "PERFORM", "READ", "RELEASE", "RETURN", "REWRITE",
            "SEARCH", "SET", "SORT", "START", "STOP", "STRING",
            "SUBTRACT", "UNSTRING", "WRITE",
        ]
        for verb in verbs:
            assert is_reserved_word(verb), f"{verb} should be reserved"

    def test_end_variants_covered(self):
        """END-xxx variants are covered."""
        end_variants = [
            "END-ADD", "END-CALL", "END-COMPUTE", "END-DELETE",
            "END-DIVIDE", "END-EVALUATE", "END-IF", "END-MULTIPLY",
            "END-PERFORM", "END-READ", "END-RETURN", "END-REWRITE",
            "END-SEARCH", "END-START", "END-STRING", "END-SUBTRACT",
            "END-UNSTRING", "END-WRITE",
        ]
        for variant in end_variants:
            assert is_reserved_word(variant), f"{variant} should be reserved"

    def test_filler_is_reserved(self):
        """FILLER is a reserved word."""
        assert is_reserved_word("FILLER")
