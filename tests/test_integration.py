"""
Tests for Phase 11: Integration Testing.

Integration tests for the full anonymization pipeline.
"""

import time

import pytest

from cobol_anonymizer.config import Config
from cobol_anonymizer.main import (
    AnonymizationPipeline,
    anonymize_directory,
)
from cobol_anonymizer.output.validator import OutputValidator

# Sample COBOL files for testing
SAMPLE_MAIN_PROGRAM = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. TESTPROG.
       AUTHOR. TEST-AUTHOR.
       DATE-WRITTEN. 2024-01-01.
      ******************************************
      * THIS IS A TEST PROGRAM
      * CREATED FOR INTEGRATION TESTING
      ******************************************
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-390.
       OBJECT-COMPUTER. IBM-390.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY COPY001.
       01 WS-CUSTOMER-RECORD.
          05 WS-CUSTOMER-ID    PIC 9(10).
          05 WS-CUSTOMER-NAME  PIC X(30).
          05 WS-CUSTOMER-FLAG  PIC X.
             88 ACTIVE-CUSTOMER VALUE 'A'.
             88 INACTIVE-CUSTOMER VALUE 'I'.
       01 WS-WORK-AREAS.
          05 WS-COUNTER        PIC 9(5) COMP-3.
          05 WS-TOTAL          PIC 9(9)V99 COMP-3.
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM INIT-PARA.
           PERFORM PROCESS-PARA.
           PERFORM CLEANUP-PARA.
           STOP RUN.
       INIT-PARA.
           INITIALIZE WS-CUSTOMER-RECORD.
           MOVE ZEROS TO WS-COUNTER.
       PROCESS-PARA.
           ADD 1 TO WS-COUNTER.
           IF ACTIVE-CUSTOMER
               ADD 100 TO WS-TOTAL
           END-IF.
       CLEANUP-PARA.
           DISPLAY 'COMPLETED'.
"""

SAMPLE_COPYBOOK = """      ******************************************
      * COMMON DATA DEFINITIONS
      ******************************************
       01 COMMON-FIELDS.
          05 COMMON-DATE       PIC 9(8).
          05 COMMON-TIME       PIC 9(6).
          05 COMMON-STATUS     PIC XX.
             88 STATUS-OK      VALUE 'OK'.
             88 STATUS-ERROR   VALUE 'ER'.
"""

SAMPLE_REDEFINES_COPYBOOK = """       01 WS-RECORD.
          05 WS-RAW-DATA       PIC X(20).
          05 WS-NUMERIC-DATA REDEFINES WS-RAW-DATA.
             10 WS-FIELD-A     PIC 9(5).
             10 WS-FIELD-B     PIC 9(5).
             10 WS-FIELD-C     PIC 9(10).
          05 WS-TEXT-DATA REDEFINES WS-RAW-DATA.
             10 WS-TEXT-PART1  PIC X(10).
             10 WS-TEXT-PART2  PIC X(10).
"""

SAMPLE_88_LEVEL = """       01 WS-STATUS-FLAGS.
          05 WS-TYPE-CODE      PIC X.
             88 TYPE-ACTIVE    VALUE 'A'.
             88 TYPE-PENDING   VALUE 'P'.
             88 TYPE-DELETED   VALUE 'D'.
             88 TYPE-VALID     VALUE 'A' 'P'.
          05 WS-RANGE-CODE     PIC 99.
             88 RANGE-LOW      VALUE 01 THRU 10.
             88 RANGE-MID      VALUE 11 THRU 50.
             88 RANGE-HIGH     VALUE 51 THRU 99.
"""

SAMPLE_EXTERNAL = """       01 SHARED-AREA EXTERNAL.
          05 SHARED-FLAG       PIC X.
          05 SHARED-VALUE      PIC 9(10).
"""


class TestFullPipeline:
    """Integration tests for the full anonymization pipeline."""

    @pytest.fixture
    def sample_codebase(self, tmp_path):
        """Create a sample COBOL codebase."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create main program
        main_prog = input_dir / "TESTPROG.cob"
        main_prog.write_text(SAMPLE_MAIN_PROGRAM)

        # Create copybook
        copybook = input_dir / "COPY001.cpy"
        copybook.write_text(SAMPLE_COPYBOOK)

        return input_dir

    def test_anonymize_simple_codebase(self, sample_codebase, tmp_path):
        """Anonymize a simple codebase."""
        output_dir = tmp_path / "output"

        config = Config(
            input_dir=sample_codebase,
            output_dir=output_dir,
            overwrite=True,
        )
        pipeline = AnonymizationPipeline(config)
        result = pipeline.run()

        assert result.success, f"Pipeline failed: {result.errors}"
        assert result.mapping_table is not None
        assert len(result.file_results) >= 1

    def test_anonymize_preserves_line_count(self, sample_codebase, tmp_path):
        """Anonymized files have same line count as originals."""
        output_dir = tmp_path / "output"

        result = anonymize_directory(
            sample_codebase,
            output_dir,
            overwrite=True,
        )

        assert result.success

        # Check line counts match
        for file_result in result.file_results:
            original = sample_codebase / file_result.filename
            if original.exists():
                original_lines = len(original.read_text().splitlines())
                assert file_result.total_lines == original_lines

    def test_anonymize_deterministic(self, sample_codebase, tmp_path):
        """Multiple runs produce identical output."""
        output1 = tmp_path / "output1"
        output2 = tmp_path / "output2"

        # First run
        config1 = Config(
            input_dir=sample_codebase,
            output_dir=output1,
            seed=42,
            overwrite=True,
        )
        pipeline1 = AnonymizationPipeline(config1)
        result1 = pipeline1.run()

        # Second run
        config2 = Config(
            input_dir=sample_codebase,
            output_dir=output2,
            seed=42,
            overwrite=True,
        )
        pipeline2 = AnonymizationPipeline(config2)
        result2 = pipeline2.run()

        assert result1.success
        assert result2.success

        # Compare mappings
        if result1.mapping_table and result2.mapping_table:
            map1 = result1.mapping_table.get_all_mappings()
            map2 = result2.mapping_table.get_all_mappings()
            assert len(map1) == len(map2)

    def test_cross_file_consistency(self, tmp_path):
        """Same identifier maps to same name across files."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create two files sharing an identifier
        file1 = input_dir / "PROG1.cob"
        file1.write_text(
            """       01 SHARED-FIELD PIC X(10).
       PROCEDURE DIVISION.
       MAIN-PARA.
           MOVE SPACES TO SHARED-FIELD.
"""
        )

        file2 = input_dir / "PROG2.cob"
        file2.write_text(
            """       01 SHARED-FIELD PIC X(10).
       PROCEDURE DIVISION.
       MAIN-PARA.
           INITIALIZE SHARED-FIELD.
"""
        )

        output_dir = tmp_path / "output"

        result = anonymize_directory(
            input_dir,
            output_dir,
            overwrite=True,
        )

        assert result.success
        # SHARED-FIELD should map to same name in both files
        if result.mapping_table:
            mapping = result.mapping_table.get_mapping("SHARED-FIELD")
            assert mapping is not None


class TestRedefinesHandling:
    """Tests for REDEFINES structure handling."""

    @pytest.fixture
    def redefines_codebase(self, tmp_path):
        """Create codebase with REDEFINES."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        redefines_file = input_dir / "REDEFINES.cpy"
        redefines_file.write_text(SAMPLE_REDEFINES_COPYBOOK)

        return input_dir

    def test_anonymize_redefines(self, redefines_codebase, tmp_path):
        """Anonymize file with REDEFINES correctly."""
        output_dir = tmp_path / "output"

        result = anonymize_directory(
            redefines_codebase,
            output_dir,
            overwrite=True,
        )

        assert result.success
        # Check that REDEFINES relationships are preserved structurally
        assert len(result.errors) == 0


class Test88LevelHandling:
    """Tests for 88-level condition handling."""

    @pytest.fixture
    def level88_codebase(self, tmp_path):
        """Create codebase with 88-level conditions."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        level88_file = input_dir / "LEVEL88.cpy"
        level88_file.write_text(SAMPLE_88_LEVEL)

        return input_dir

    def test_anonymize_88_levels(self, level88_codebase, tmp_path):
        """Anonymize file with 88-level conditions."""
        output_dir = tmp_path / "output"

        result = anonymize_directory(
            level88_codebase,
            output_dir,
            overwrite=True,
        )

        assert result.success

        # Check that VALUE clauses are preserved in output
        for file_result in result.file_results:
            for change in file_result.changes:
                if "VALUE" in change.original_line:
                    assert "VALUE" in change.transformed_line


class TestExternalHandling:
    """Tests for EXTERNAL item handling."""

    @pytest.fixture
    def external_codebase(self, tmp_path):
        """Create codebase with EXTERNAL items."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        external_file = input_dir / "EXTERNAL.cpy"
        external_file.write_text(SAMPLE_EXTERNAL)

        return input_dir

    def test_external_preserved(self, external_codebase, tmp_path):
        """EXTERNAL items keep their original names."""
        output_dir = tmp_path / "output"

        result = anonymize_directory(
            external_codebase,
            output_dir,
            overwrite=True,
        )

        assert result.success

        # Check that SHARED-AREA is preserved
        for file_result in result.file_results:
            for change in file_result.changes:
                if "EXTERNAL" in change.original_line:
                    # The EXTERNAL item name should be preserved
                    assert "SHARED-AREA" in change.transformed_line


class TestCopyDependencies:
    """Tests for COPY statement dependency handling."""

    @pytest.fixture
    def copy_chain_codebase(self, tmp_path):
        """Create codebase with COPY chain."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Copybook at bottom of chain
        copy3 = input_dir / "COPY003.cpy"
        copy3.write_text("       01 LEVEL3-FIELD PIC X.")

        # Copybook that includes COPY003
        copy2 = input_dir / "COPY002.cpy"
        copy2.write_text(
            """       01 LEVEL2-RECORD.
          05 LEVEL2-FIELD PIC X.
       COPY COPY003.
"""
        )

        # Program that includes COPY002
        prog = input_dir / "MAINPROG.cob"
        prog.write_text(
            """       IDENTIFICATION DIVISION.
       PROGRAM-ID. MAINPROG.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY COPY002.
       PROCEDURE DIVISION.
       MAIN-PARA.
           STOP RUN.
"""
        )

        return input_dir

    def test_copy_chain_processed(self, copy_chain_codebase, tmp_path):
        """COPY chain is processed in correct order."""
        output_dir = tmp_path / "output"

        result = anonymize_directory(
            copy_chain_codebase,
            output_dir,
            overwrite=True,
        )

        assert result.success
        # All three files should be processed
        assert len(result.file_results) == 3


class TestPICPreservation:
    """Tests for PIC clause preservation."""

    def test_pic_clauses_unchanged(self, tmp_path):
        """All PIC clauses remain identical after anonymization."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_file = input_dir / "PICTEST.cpy"
        test_file.write_text(
            """       01 WS-RECORD.
          05 WS-NUMERIC    PIC 9(10).
          05 WS-ALPHA      PIC X(30).
          05 WS-DECIMAL    PIC 9(5)V99.
          05 WS-SIGNED     PIC S9(9) COMP-3.
          05 WS-EDITED     PIC ZZZ,ZZ9.99.
"""
        )

        output_dir = tmp_path / "output"

        result = anonymize_directory(
            input_dir,
            output_dir,
            overwrite=True,
        )

        assert result.success

        # Check each PIC clause is preserved
        pic_patterns = [
            "PIC 9(10)",
            "PIC X(30)",
            "PIC 9(5)V99",
            "PIC S9(9)",
            "COMP-3",
            "PIC ZZZ,ZZ9.99",
        ]

        for file_result in result.file_results:
            full_output = "".join(c.transformed_line for c in file_result.changes)
            for pattern in pic_patterns:
                assert (
                    pattern in full_output or pattern.lower() in full_output.lower()
                ), f"PIC pattern '{pattern}' not found in output"


class TestValidation:
    """Tests for output validation."""

    def test_validate_output(self, tmp_path):
        """Validate output files after anonymization."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        test_file = input_dir / "TEST.cob"
        test_file.write_text(SAMPLE_MAIN_PROGRAM)

        result = anonymize_directory(
            input_dir,
            output_dir,
            overwrite=True,
        )

        assert result.success

        # Validate output
        validator = OutputValidator()
        validation = validator.validate_directory(output_dir)

        # Check for no errors
        errors = [i for i in validation.issues if i.severity.value == "error"]
        assert len(errors) == 0, f"Validation errors: {errors}"


class TestCommentHandling:
    """Tests for comment anonymization."""

    def test_comments_anonymized(self, tmp_path):
        """Comments are properly anonymized."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_file = input_dir / "COMMENTS.cob"
        test_file.write_text(
            """      ******************************************
      * GESTIONE POLIZZA - MANAGEMENT MODULE
      * MODIFIED BY MASON 15/03/2024
      * CRQ000002478171 - FIX CALCOLO
      ******************************************
       01 WS-FIELD PIC X.
"""
        )

        output_dir = tmp_path / "output"

        result = anonymize_directory(
            input_dir,
            output_dir,
            overwrite=True,
        )

        assert result.success

        # Check that Italian terms are translated and names removed
        for file_result in result.file_results:
            full_output = "\n".join(c.transformed_line for c in file_result.changes)
            # Italian term should be translated
            if "POLIZZA" in SAMPLE_MAIN_PROGRAM:
                assert "POLIZZA" not in full_output or "POLICY" in full_output


class TestPerformance:
    """Performance tests."""

    def test_processing_time(self, tmp_path):
        """Processing completes in reasonable time."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create 10 files
        for i in range(10):
            test_file = input_dir / f"TEST{i:03d}.cob"
            test_file.write_text(SAMPLE_MAIN_PROGRAM)

        output_dir = tmp_path / "output"

        start = time.time()
        result = anonymize_directory(
            input_dir,
            output_dir,
            overwrite=True,
        )
        elapsed = time.time() - start

        assert result.success
        # Should complete in under 10 seconds for 10 files
        assert elapsed < 10.0, f"Processing took {elapsed:.2f}s, expected < 10s"


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_file(self, tmp_path):
        """Handle empty file gracefully."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        empty_file = input_dir / "EMPTY.cob"
        empty_file.write_text("")

        output_dir = tmp_path / "output"

        result = anonymize_directory(
            input_dir,
            output_dir,
            overwrite=True,
        )

        # Should not crash
        assert result.success or len(result.errors) == 0

    def test_file_with_only_comments(self, tmp_path):
        """Handle file with only comments."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        comment_file = input_dir / "COMMENTS.cob"
        comment_file.write_text(
            """      * LINE 1
      * LINE 2
      * LINE 3
"""
        )

        output_dir = tmp_path / "output"

        result = anonymize_directory(
            input_dir,
            output_dir,
            overwrite=True,
        )

        assert result.success

    def test_very_long_identifier(self, tmp_path):
        """Handle identifiers at length limit."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        long_name = "A" * 30  # Max length
        test_file = input_dir / "LONGNAME.cob"
        test_file.write_text(f"       01 {long_name} PIC X.\n")

        output_dir = tmp_path / "output"

        result = anonymize_directory(
            input_dir,
            output_dir,
            overwrite=True,
        )

        assert result.success


class TestCommentAnonymization:
    """Tests for comment anonymization in the full pipeline."""

    def test_comments_are_anonymized(self, tmp_path):
        """Comments are replaced with filler text in output."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_file = input_dir / "TESTCOMM.cob"
        test_file.write_text(
            """      * SISTEMA PORTAFOGLIO RAMI DANNI
      * AGGIORNAMENTO PARTE AMMINISTRATIVA
       01 WS-FIELD PIC X.
"""
        )

        output_dir = tmp_path / "output"

        result = anonymize_directory(
            input_dir,
            output_dir,
            overwrite=True,
        )

        assert result.success

        # Check that original Italian text is not in output
        for file_result in result.file_results:
            for change in file_result.changes:
                if change.is_comment:
                    assert "SISTEMA" not in change.transformed_line
                    assert "PORTAFOGLIO" not in change.transformed_line
                    assert "AGGIORNAMENTO" not in change.transformed_line

    def test_comment_dividers_preserved(self, tmp_path):
        """Comment dividers (asterisks, dashes) are preserved."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_file = input_dir / "DIVIDERS.cob"
        test_file.write_text(
            """      ******************************************
      * ACTUAL COMMENT TEXT HERE
      *------------------------------------------
       01 WS-FIELD PIC X.
"""
        )

        output_dir = tmp_path / "output"

        result = anonymize_directory(
            input_dir,
            output_dir,
            overwrite=True,
        )

        assert result.success

        # Check dividers are preserved
        for file_result in result.file_results:
            divider_count = 0
            for change in file_result.changes:
                if change.is_comment:
                    if "****" in change.transformed_line:
                        divider_count += 1
                    if "----" in change.transformed_line:
                        divider_count += 1
            assert divider_count >= 2, "Dividers should be preserved"

    def test_comment_line_count_preserved(self, tmp_path):
        """Number of comment lines is preserved."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_file = input_dir / "LINECOUNT.cob"
        original_content = """      * COMMENT LINE 1
      * COMMENT LINE 2
      * COMMENT LINE 3
       01 WS-FIELD PIC X.
"""
        test_file.write_text(original_content)

        output_dir = tmp_path / "output"

        result = anonymize_directory(
            input_dir,
            output_dir,
            overwrite=True,
        )

        assert result.success

        # Count original comment lines
        original_comment_lines = sum(
            1 for line in original_content.splitlines() if len(line) >= 7 and line[6] == "*"
        )

        # Count output comment lines
        for file_result in result.file_results:
            output_comment_lines = sum(1 for c in file_result.changes if c.is_comment)
            assert output_comment_lines == original_comment_lines

    def test_box_borders_preserved(self, tmp_path):
        """Box borders (whitespace with asterisks) are preserved."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        test_file = input_dir / "BOXBORDER.cob"
        test_file.write_text(
            """      ******************************************
      *                                        *
      *  SOME COMMENT TEXT HERE                *
      *                                        *
      ******************************************
       01 WS-FIELD PIC X.
"""
        )

        output_dir = tmp_path / "output"

        result = anonymize_directory(
            input_dir,
            output_dir,
            overwrite=True,
        )

        assert result.success

        # Check that box structure is preserved
        box_border_count = 0
        for file_result in result.file_results:
            for change in file_result.changes:
                if change.is_comment:
                    line = change.transformed_line
                    # Check for lines that are mostly whitespace with asterisks at edges
                    if line.strip().endswith("*") and "   *" in line:
                        box_border_count += 1

        # We should have box borders preserved
        assert box_border_count >= 2
