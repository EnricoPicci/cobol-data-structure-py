"""
Tests for Phase 8: Comment Handler.

Tests for comment anonymization functionality.
"""

import pytest

from cobol_anonymizer.generators.comment_generator import (
    CommentConfig,
    CommentMode,
    CommentTransformer,
    CommentTransformResult,
    ITALIAN_TERMS,
    PERSONAL_NAMES,
    anonymize_comment,
    detect_comment_lines,
    get_comment_statistics,
    is_comment_line,
    is_divider_line,
    remove_personal_names,
    remove_system_ids,
    strip_comment,
    translate_italian_terms,
)


class TestIsCommentLine:
    """Tests for comment line detection."""

    def test_standard_comment(self):
        """Standard comment with * in column 7."""
        line = "      * THIS IS A COMMENT"
        assert is_comment_line(line)

    def test_comment_with_sequence(self):
        """Comment with sequence number in columns 1-6."""
        line = "000100* COMMENT WITH SEQUENCE"
        assert is_comment_line(line)

    def test_not_comment_code_line(self):
        """Regular code line is not a comment."""
        line = "       MOVE X TO Y."
        assert not is_comment_line(line)

    def test_not_comment_continuation(self):
        """Continuation line (- in col 7) is not a comment."""
        line = "      -    'CONTINUED TEXT'"
        assert not is_comment_line(line)

    def test_not_comment_debug(self):
        """Debug line (D in col 7) is not a comment."""
        line = "      D    DISPLAY 'DEBUG'."
        assert not is_comment_line(line)

    def test_short_line_not_comment(self):
        """Line too short to have column 7."""
        line = "     "
        assert not is_comment_line(line)

    def test_empty_comment(self):
        """Comment with no text after asterisk."""
        line = "      *"
        assert is_comment_line(line)

    def test_asterisk_in_string_not_comment(self):
        """Asterisk in Area B is not a comment indicator."""
        line = "       MOVE '*' TO X."
        assert not is_comment_line(line)


class TestIsDividerLine:
    """Tests for divider line detection."""

    def test_all_dashes(self):
        """Line of dashes is a divider."""
        assert is_divider_line("----------------------------------------")

    def test_all_asterisks(self):
        """Line of asterisks is a divider."""
        assert is_divider_line("*****************************************")

    def test_all_equals(self):
        """Line of equals is a divider."""
        assert is_divider_line("=========================================")

    def test_mixed_pattern(self):
        """Mixed repeating pattern is a divider."""
        assert is_divider_line("-*-*-*-*-*-*-*-*-*-*")

    def test_empty_string(self):
        """Empty string is a divider."""
        assert is_divider_line("")

    def test_only_spaces(self):
        """Only spaces is a divider."""
        assert is_divider_line("        ")

    def test_text_not_divider(self):
        """Line with text is not a divider."""
        assert not is_divider_line("THIS IS A COMMENT")

    def test_mostly_text_not_divider(self):
        """Line with mostly text is not a divider."""
        assert not is_divider_line("CALCULATE PREMIUM AMOUNT")

    def test_short_dashes_not_divider(self):
        """Very short dash sequences are not dividers."""
        assert not is_divider_line("--")


class TestRemovePersonalNames:
    """Tests for personal name removal."""

    def test_remove_single_name(self):
        """Remove a single personal name."""
        result, changes = remove_personal_names("MODIFIED BY MASON")
        assert "MASON" not in result
        assert len(changes) >= 1

    def test_remove_multiple_names(self):
        """Remove multiple personal names."""
        result, changes = remove_personal_names("CREATED BY LUPO, UPDATED BY ROSSI")
        assert "LUPO" not in result
        assert "ROSSI" not in result

    def test_case_insensitive(self):
        """Name removal is case-insensitive."""
        result, changes = remove_personal_names("Modified by Mason")
        assert "Mason" not in result

    def test_preserve_non_names(self):
        """Text that isn't a name is preserved."""
        result, changes = remove_personal_names("CALCULATE PREMIUM")
        assert "CALCULATE" in result
        assert "PREMIUM" in result

    def test_replacement_format(self):
        """Replacement is in USERxxx format."""
        result, changes = remove_personal_names("MASON ADDED THIS")
        assert "USER" in result


class TestRemoveSystemIds:
    """Tests for system ID removal."""

    def test_remove_crq_number(self):
        """Remove CRQ numbers."""
        result, changes = remove_system_ids("FIX FOR CRQ000002478171")
        assert "CRQ000002478171" not in result
        assert "XXXXXXXX" in result

    def test_remove_inc_number(self):
        """Remove INC numbers."""
        result, changes = remove_system_ids("RELATED TO INC000001234567")
        assert "INC000001234567" not in result

    def test_remove_date_slash(self):
        """Remove dates with slash format."""
        result, changes = remove_system_ids("MODIFIED 15/03/2024")
        assert "15/03/2024" not in result

    def test_remove_date_dash(self):
        """Remove dates with dash format."""
        result, changes = remove_system_ids("CREATED 15-03-2024")
        assert "15-03-2024" not in result

    def test_remove_yyyymmdd(self):
        """Remove 8-digit date format."""
        result, changes = remove_system_ids("VERSION 20240315")
        assert "20240315" not in result

    def test_preserve_short_numbers(self):
        """Short numbers are preserved."""
        result, changes = remove_system_ids("LINE 42 OF 100")
        assert "42" in result
        assert "100" in result


class TestTranslateItalianTerms:
    """Tests for Italian term translation."""

    def test_translate_polizza(self):
        """POLIZZA translates to POLICY."""
        result, changes = translate_italian_terms("GESTIONE POLIZZA")
        assert "POLICY" in result
        assert "POLIZZA" not in result

    def test_translate_cliente(self):
        """CLIENTE translates to CLIENT."""
        result, changes = translate_italian_terms("DATI CLIENTE")
        assert "CLIENT" in result

    def test_translate_multiple_terms(self):
        """Multiple terms are translated."""
        result, changes = translate_italian_terms("CALCOLO PREMIO POLIZZA")
        assert "POLICY" in result
        assert "PREMIUM" in result

    def test_case_insensitive(self):
        """Translation is case-insensitive."""
        result, changes = translate_italian_terms("Gestione Polizza")
        assert "POLICY" in result

    def test_all_terms_have_translations(self):
        """All defined Italian terms have translations."""
        for italian, english in ITALIAN_TERMS.items():
            assert italian  # Not empty
            assert english  # Not empty


class TestStripComment:
    """Tests for comment stripping."""

    def test_strip_text_comment(self):
        """Text comment is stripped."""
        result = strip_comment("THIS IS A COMMENT")
        assert result == ""

    def test_preserve_divider(self):
        """Divider line is preserved when configured."""
        result = strip_comment("----------------------------------------", preserve_dividers=True)
        assert "---" in result

    def test_strip_divider_when_disabled(self):
        """Divider is stripped when preservation disabled."""
        result = strip_comment("----------------------------------------", preserve_dividers=False)
        assert result == ""


class TestCommentTransformer:
    """Tests for CommentTransformer class."""

    def test_create_transformer(self):
        """Create transformer with default config."""
        transformer = CommentTransformer()
        assert transformer is not None

    def test_anonymize_mode(self):
        """Anonymize mode transforms comment."""
        config = CommentConfig(mode=CommentMode.ANONYMIZE)
        transformer = CommentTransformer(config)

        result = transformer.transform_comment("GESTIONE POLIZZA")
        assert result.transformed_text != result.original_text
        assert "POLICY" in result.transformed_text

    def test_strip_mode(self):
        """Strip mode removes comment content."""
        config = CommentConfig(mode=CommentMode.STRIP)
        transformer = CommentTransformer(config)

        result = transformer.transform_comment("THIS IS A COMMENT")
        assert result.transformed_text == ""
        assert result.is_stripped

    def test_preserve_mode(self):
        """Preserve mode keeps comment unchanged."""
        config = CommentConfig(mode=CommentMode.PRESERVE)
        transformer = CommentTransformer(config)

        result = transformer.transform_comment("KEEP THIS COMMENT")
        assert result.transformed_text == result.original_text

    def test_divider_preserved_in_strip_mode(self):
        """Divider lines preserved even in strip mode."""
        config = CommentConfig(mode=CommentMode.STRIP, preserve_dividers=True)
        transformer = CommentTransformer(config)

        result = transformer.transform_comment("----------------------------------------")
        assert result.is_divider
        assert "---" in result.transformed_text

    def test_transform_line_comment(self):
        """Transform a complete comment line."""
        transformer = CommentTransformer()
        line = "      * GESTIONE POLIZZA"

        transformed, result = transformer.transform_line(line)
        assert "POLICY" in transformed
        assert transformed.startswith("      *")

    def test_transform_line_non_comment(self):
        """Non-comment line returned unchanged."""
        transformer = CommentTransformer()
        line = "       MOVE X TO Y."

        transformed, result = transformer.transform_line(line)
        assert transformed == line

    def test_changes_tracked(self):
        """Changes made during transformation are tracked."""
        transformer = CommentTransformer()
        result = transformer.transform_comment("GESTIONE POLIZZA")
        assert len(result.changes_made) >= 1

    def test_reset(self):
        """Reset clears transformer state."""
        transformer = CommentTransformer()
        transformer.transform_comment("MODIFIED BY MASON")
        transformer.reset()
        # After reset, counter should start fresh
        result = transformer.transform_comment("MODIFIED BY LUPO")
        assert "USER000" in result.transformed_text


class TestCommentTransformerConfig:
    """Tests for CommentTransformer configuration options."""

    def test_disable_name_removal(self):
        """Personal names not removed when disabled."""
        config = CommentConfig(remove_personal_names=False)
        transformer = CommentTransformer(config)

        result = transformer.transform_comment("MODIFIED BY MASON")
        assert "MASON" in result.transformed_text

    def test_disable_system_id_removal(self):
        """System IDs not removed when disabled."""
        config = CommentConfig(remove_system_ids=False)
        transformer = CommentTransformer(config)

        result = transformer.transform_comment("FIX FOR CRQ000002478171")
        assert "CRQ000002478171" in result.transformed_text

    def test_disable_italian_translation(self):
        """Italian terms not translated when disabled."""
        config = CommentConfig(translate_italian=False)
        transformer = CommentTransformer(config)

        result = transformer.transform_comment("GESTIONE POLIZZA")
        assert "POLIZZA" in result.transformed_text


class TestDetectCommentLines:
    """Tests for detecting comment lines in files."""

    def test_detect_single_comment(self):
        """Detect single comment line."""
        lines = [
            "       01 WS-FIELD PIC X.",
            "      * THIS IS A COMMENT",
            "       MOVE X TO Y.",
        ]
        comment_lines = detect_comment_lines(lines)
        assert comment_lines == [2]

    def test_detect_multiple_comments(self):
        """Detect multiple comment lines."""
        lines = [
            "      * FIRST COMMENT",
            "       CODE LINE",
            "      * SECOND COMMENT",
            "      * THIRD COMMENT",
        ]
        comment_lines = detect_comment_lines(lines)
        assert comment_lines == [1, 3, 4]

    def test_no_comments(self):
        """No comments in file."""
        lines = [
            "       01 WS-FIELD PIC X.",
            "       MOVE X TO Y.",
        ]
        comment_lines = detect_comment_lines(lines)
        assert comment_lines == []


class TestGetCommentStatistics:
    """Tests for comment statistics."""

    def test_statistics_basic(self):
        """Basic statistics calculation."""
        lines = [
            "      * COMMENT ONE",
            "       CODE LINE",
            "      * COMMENT TWO",
            "      *----------------------------------------",
            "       MORE CODE",
        ]
        stats = get_comment_statistics(lines)

        assert stats["total_lines"] == 5
        assert stats["comment_lines"] == 3
        assert stats["divider_lines"] == 1
        assert stats["content_comments"] == 2

    def test_statistics_empty_file(self):
        """Statistics for empty file."""
        stats = get_comment_statistics([])
        assert stats["total_lines"] == 0
        assert stats["comment_lines"] == 0

    def test_statistics_all_comments(self):
        """Statistics for file with all comments."""
        lines = [
            "      * COMMENT ONE",
            "      * COMMENT TWO",
        ]
        stats = get_comment_statistics(lines)
        assert stats["comment_percentage"] == 100.0


class TestAnonymizeCommentFunction:
    """Tests for convenience function."""

    def test_anonymize_simple(self):
        """Anonymize with default config."""
        result = anonymize_comment("GESTIONE POLIZZA")
        assert "POLICY" in result

    def test_anonymize_with_config(self):
        """Anonymize with custom config."""
        config = CommentConfig(translate_italian=False)
        result = anonymize_comment("GESTIONE POLIZZA", config)
        assert "POLIZZA" in result


class TestRealWorldComments:
    """Tests using realistic COBOL comment patterns."""

    def test_header_comment_block(self):
        """Process typical header comment block."""
        transformer = CommentTransformer()
        lines = [
            "      ******************************************************",
            "      *  PROGRAMMA: GESTIONE POLIZZA                       *",
            "      *  AUTORE: MASON                                      *",
            "      *  DATA: 15/03/2024                                   *",
            "      ******************************************************",
        ]

        results = []
        for line in lines:
            transformed, result = transformer.transform_line(line)
            results.append(transformed)

        # Check transformations
        assert "POLICY" in results[1]
        assert "MASON" not in results[2]
        assert "15/03/2024" not in results[3]

    def test_inline_comment_with_crq(self):
        """Process comment with CRQ number."""
        transformer = CommentTransformer()
        line = "      * FIX PER CRQ000002478171 - ERRORE CALCOLO PREMIO"

        transformed, result = transformer.transform_line(line)
        assert "CRQ000002478171" not in transformed
        assert "PREMIUM" in transformed or "ERROR" in transformed

    def test_section_divider(self):
        """Process section divider comment."""
        transformer = CommentTransformer()
        line = "      *-------------------------------------------------"

        transformed, result = transformer.transform_line(line)
        assert result.is_divider
        assert "---" in transformed

    def test_empty_comment_preserved(self):
        """Empty comment line structure preserved."""
        transformer = CommentTransformer()
        line = "      *"

        transformed, result = transformer.transform_line(line)
        assert transformed == "      *"
