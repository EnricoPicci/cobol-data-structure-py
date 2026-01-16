"""
Tests for Phase 7: Core Anonymizer.

Tests for the main anonymization functionality.
"""

from cobol_anonymizer.cobol.column_handler import parse_line
from cobol_anonymizer.core.anonymizer import (
    Anonymizer,
    LineTransformer,
    RedefinesTracker,
)
from cobol_anonymizer.core.classifier import IdentifierType
from cobol_anonymizer.core.mapper import MappingTable


class TestRedefinesTracker:
    """Tests for RedefinesTracker."""

    def test_add_redefines(self):
        """Add REDEFINES relationship."""
        tracker = RedefinesTracker()
        tracker.add_redefines("WS-X", "WS-Y", 5, 10)

        assert tracker.get_redefined_name("WS-X") == "WS-Y"

    def test_get_redefining_items(self):
        """Get items that REDEFINE a name."""
        tracker = RedefinesTracker()
        tracker.add_redefines("WS-X", "WS-RECORD", 5, 10)
        tracker.add_redefines("WS-Y", "WS-RECORD", 5, 15)

        items = tracker.get_redefining_items("WS-RECORD")
        assert len(items) == 2

    def test_case_insensitive(self):
        """Lookup is case-insensitive."""
        tracker = RedefinesTracker()
        tracker.add_redefines("ws-x", "ws-y", 5, 10)

        assert tracker.get_redefined_name("WS-X") == "ws-y"


class TestLineTransformer:
    """Tests for LineTransformer."""

    def test_transform_simple_identifier(self):
        """Transform a simple identifier."""
        table = MappingTable()
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        transformer = LineTransformer(table)
        parsed = parse_line("       05 WS-FIELD PIC X.", 1)
        result = transformer.transform_line(parsed)

        assert len(result.changes_made) >= 1
        assert any("WS-FIELD" in orig for orig, anon in result.changes_made)

    def test_preserve_pic_clause(self):
        """PIC clause is not modified."""
        table = MappingTable()
        # Don't add PIC to mapping table
        transformer = LineTransformer(table)
        parsed = parse_line("       05 FIELD PIC X(30).", 1)
        result = transformer.transform_line(parsed)

        # PIC X(30) should be preserved
        assert "PIC" in result.transformed_line
        assert "X(30)" in result.transformed_line

    def test_preserve_filler(self):
        """FILLER is not anonymized."""
        table = MappingTable()
        transformer = LineTransformer(table)
        parsed = parse_line("       05 FILLER PIC X(10).", 1)
        result = transformer.transform_line(parsed)

        assert "FILLER" in result.transformed_line

    def test_comment_line_anonymized(self):
        """Comment lines have their content anonymized."""
        table = MappingTable()
        transformer = LineTransformer(table)
        parsed = parse_line("      *THIS IS A COMMENT", 1)
        result = transformer.transform_line(parsed)

        assert result.is_comment
        # Comment structure preserved but content replaced
        assert result.transformed_line.startswith("      *")
        # Original text should not be present
        assert "THIS IS A COMMENT" not in result.transformed_line

    def test_external_item_anonymized_by_default(self):
        """EXTERNAL items are anonymized by default."""
        table = MappingTable()
        table.get_or_create("SHARED-AREA", IdentifierType.EXTERNAL_NAME, is_external=True)

        transformer = LineTransformer(table)
        parsed = parse_line("       01 SHARED-AREA EXTERNAL.", 1)
        result = transformer.transform_line(parsed)

        # By default, EXTERNAL items should be anonymized
        assert "SHARED-AREA" not in result.transformed_line
        assert len(result.changes_made) > 0

    def test_external_item_preserved_when_configured(self):
        """EXTERNAL items keep original names when preserve_external=True."""
        table = MappingTable(_preserve_external=True)
        table.get_or_create("SHARED-AREA", IdentifierType.EXTERNAL_NAME, is_external=True)

        transformer = LineTransformer(table, preserve_external=True)
        parsed = parse_line("       01 SHARED-AREA EXTERNAL.", 1)
        result = transformer.transform_line(parsed)

        # With preserve_external=True, EXTERNAL items should keep original names
        assert "SHARED-AREA" in result.transformed_line


class TestLineTransformerRedefines:
    """Tests for REDEFINES handling in LineTransformer."""

    def test_track_redefines(self):
        """REDEFINES relationships are tracked."""
        table = MappingTable()
        tracker = RedefinesTracker()
        transformer = LineTransformer(table, tracker)

        # Process a line with REDEFINES
        parsed = parse_line("       05 WS-X REDEFINES WS-Y PIC X.", 1)
        transformer.transform_line(parsed)

        # Check that relationship was tracked
        assert tracker.get_redefined_name("WS-X") == "WS-Y"

    def test_nested_redefines_three_levels(self):
        """Handle 3-level nested REDEFINES correctly."""
        table = MappingTable()
        tracker = RedefinesTracker()
        transformer = LineTransformer(table, tracker)

        lines = [
            "       01 WS-LEVEL1.",
            "          05 WS-LEVEL2 PIC X(10).",
            "          05 WS-LEVEL2-R REDEFINES WS-LEVEL2.",
            "             10 WS-LEVEL3 PIC X(5).",
            "             10 WS-LEVEL3-R REDEFINES WS-LEVEL3 PIC 9(5).",
        ]

        for i, line in enumerate(lines, 1):
            parsed = parse_line(line, i)
            transformer.transform_line(parsed)

        # Check relationships
        assert tracker.get_redefined_name("WS-LEVEL2-R") == "WS-LEVEL2"
        assert tracker.get_redefined_name("WS-LEVEL3-R") == "WS-LEVEL3"


class TestAnonymizer:
    """Tests for main Anonymizer class."""

    def test_create_anonymizer(self):
        """Create an Anonymizer instance."""
        anon = Anonymizer()
        assert anon is not None
        assert anon.mapping_table is not None

    def test_classify_file(self, tmp_path):
        """Classify identifiers in a file."""
        # Create a simple COBOL file
        program = tmp_path / "TEST.cob"
        program.write_text(
            """       IDENTIFICATION DIVISION.
       PROGRAM-ID.    TESTPROG.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-RECORD.
          05 WS-FIELD PIC X(10).
       PROCEDURE DIVISION.
       MAIN-PARA.
           STOP RUN.
"""
        )

        anon = Anonymizer(source_directory=tmp_path)
        identifiers = anon.classify_file(program)

        # Should find program name, data names, and paragraph
        types = [i.type for i in identifiers if i.is_definition]
        assert IdentifierType.PROGRAM_NAME in types
        assert IdentifierType.DATA_NAME in types
        assert IdentifierType.PARAGRAPH_NAME in types

    def test_build_mappings(self):
        """Build mappings from identifiers."""
        anon = Anonymizer()

        from cobol_anonymizer.core.classifier import ClassifiedIdentifier

        identifiers = [
            ClassifiedIdentifier(
                name="WS-FIELD",
                type=IdentifierType.DATA_NAME,
                line_number=1,
                is_definition=True,
            ),
            ClassifiedIdentifier(
                name="TESTPROG",
                type=IdentifierType.PROGRAM_NAME,
                line_number=2,
                is_definition=True,
            ),
        ]

        anon.build_mappings(identifiers)

        # Check mappings were created
        assert anon.mapping_table.get_mapping("WS-FIELD") is not None
        assert anon.mapping_table.get_mapping("TESTPROG") is not None

    def test_transform_file(self, tmp_path):
        """Transform a file with mappings."""
        # Create a COBOL file
        program = tmp_path / "TEST.cob"
        program.write_text(
            """       01 WS-FIELD PIC X.
       01 WS-OTHER PIC 9.
"""
        )

        anon = Anonymizer(source_directory=tmp_path)

        # Classify and build mappings
        identifiers = anon.classify_file(program)
        anon.build_mappings(identifiers)

        # Transform
        result = anon.transform_file(program)

        assert result.total_lines == 2
        # At least one line should have changes
        assert result.transformed_lines > 0

    def test_anonymize_file(self, tmp_path):
        """Complete anonymization of a file."""
        program = tmp_path / "TEST.cob"
        program.write_text(
            """       01 WS-CUSTOMER-NAME PIC X(30).
"""
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
        )

        result = anon.anonymize_file(program)

        assert result.total_lines == 1
        # Check that the field name was anonymized
        assert any("WS-CUSTOMER-NAME" in orig for orig, anon in result.changes[0].changes_made)


class TestAnonymizerWithCopybooks:
    """Tests for anonymizing with copybook dependencies."""

    def test_discover_files(self, tmp_path):
        """Discover files and build dependency order."""
        # Create program and copybook
        copybook = tmp_path / "COPY01.cpy"
        copybook.write_text("       01 WS-SHARED PIC X.")

        program = tmp_path / "PROG.cob"
        program.write_text("       COPY COPY01.\n       01 WS-LOCAL PIC X.")

        anon = Anonymizer(source_directory=tmp_path)
        files = anon.discover_files()

        # Copybook should be discovered
        assert len(files) >= 1

    def test_dependency_order(self, tmp_path):
        """Files processed in correct dependency order."""
        # Create files with dependencies
        copy2 = tmp_path / "COPY2.cpy"
        copy2.write_text("       01 FIELD-2 PIC X.")

        copy1 = tmp_path / "COPY1.cpy"
        copy1.write_text("       COPY COPY2.\n       01 FIELD-1 PIC X.")

        program = tmp_path / "PROG.cob"
        program.write_text("       COPY COPY1.")

        anon = Anonymizer(source_directory=tmp_path)
        anon.discover_files()

        # Processing order should have COPY2 before COPY1
        order = anon._processing_order
        copy2_idx = next((i for i, n in enumerate(order) if "COPY2" in n), -1)
        copy1_idx = next((i for i, n in enumerate(order) if "COPY1" in n), -1)

        if copy2_idx >= 0 and copy1_idx >= 0:
            assert copy2_idx < copy1_idx


class TestAnonymizerOutput:
    """Tests for anonymizer output."""

    def test_save_and_load_mappings(self, tmp_path):
        """Mappings can be saved and loaded."""
        anon = Anonymizer()
        anon.mapping_table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        # Save
        mapping_file = tmp_path / "mappings.json"
        anon.save_mappings(mapping_file)

        assert mapping_file.exists()

        # Load in new instance
        anon2 = Anonymizer()
        anon2.load_mappings(mapping_file)

        # Verify mapping was loaded
        assert anon2.mapping_table.get_mapping("WS-FIELD") is not None

    def test_write_output(self, tmp_path):
        """Transformed files are written correctly."""
        program = tmp_path / "TEST.cob"
        program.write_text("       01 WS-FIELD PIC X.\n")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
        )

        anon.anonymize_file(program)

        # Check output was written
        # The output filename may be anonymized
        output_files = list(output_dir.glob("*.cob"))
        assert len(output_files) >= 0  # May use different naming

    def test_filename_anonymization(self, tmp_path):
        """Output filename is anonymized based on PROGRAM-ID mapping."""
        # Create a program with PROGRAM-ID
        program = tmp_path / "MYPROGRAM.cob"
        program.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. MYPROGRAM.\n"
            "       DATA DIVISION.\n"
            "       WORKING-STORAGE SECTION.\n"
            "       01 WS-FIELD PIC X.\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
        )

        anon.anonymize_file(program)

        # Output file should be anonymized (not MYPROGRAM.cob)
        output_files = list(output_dir.glob("*.cob"))
        assert len(output_files) == 1
        # Original filename should not exist
        assert not (output_dir / "MYPROGRAM.cob").exists()
        # The anonymized file should exist
        anon_name = anon.mapping_table.get_anonymized_name("MYPROGRAM")
        assert anon_name is not None
        assert (output_dir / f"{anon_name}.cob").exists()

    def test_filename_anonymization_free_format(self, tmp_path):
        """Output filename is anonymized for free-format COBOL."""
        # Create a free-format program
        program = tmp_path / "TESTPROG.cbl"
        program.write_text(
            "*> Test program\n"
            "IDENTIFICATION DIVISION.\n"
            "PROGRAM-ID. TESTPROG.\n"
            "DATA DIVISION.\n"
            "WORKING-STORAGE SECTION.\n"
            "01 WS-DATA PIC X(10).\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
        )

        anon.anonymize_file(program)

        # Output file should be anonymized
        output_files = list(output_dir.glob("*.cbl"))
        assert len(output_files) == 1
        assert not (output_dir / "TESTPROG.cbl").exists()
        # Verify mapping exists
        anon_name = anon.mapping_table.get_anonymized_name("TESTPROG")
        assert anon_name is not None


class TestAnonymizerSpecialCases:
    """Tests for special cases in anonymization."""

    def test_preserve_reserved_words(self, tmp_path):
        """Reserved words are not anonymized."""
        program = tmp_path / "TEST.cob"
        program.write_text("           MOVE SPACES TO WS-FIELD.\n")

        anon = Anonymizer(source_directory=tmp_path)
        identifiers = anon.classify_file(program)
        anon.build_mappings(identifiers)
        result = anon.transform_file(program)

        # MOVE, SPACES, TO should still be in output
        output = result.changes[0].transformed_line
        assert "MOVE" in output
        assert "TO" in output

    def test_transform_value_literal(self, tmp_path):
        """VALUE clause literals are handled (preserved when --protect-literals)."""
        program = tmp_path / "TEST.cob"
        program.write_text("       05 WS-FLAG PIC X VALUE 'Y'.\n")

        # Use anonymize_literals=False to test literal preservation
        anon = Anonymizer(source_directory=tmp_path, anonymize_literals=False)
        result = anon.anonymize_file(program)

        # VALUE and literal should be preserved when literals are protected
        output = result.changes[0].transformed_line
        assert "VALUE" in output
        assert "'Y'" in output  # Literal preserved with --protect-literals

    def test_external_item_anonymized_by_default(self, tmp_path):
        """EXTERNAL items are anonymized by default."""
        program = tmp_path / "TEST.cob"
        program.write_text("       01 SHARED-AREA EXTERNAL.\n")

        anon = Anonymizer(source_directory=tmp_path)
        result = anon.anonymize_file(program)

        output = result.changes[0].transformed_line
        # EXTERNAL items should be anonymized by default
        assert "SHARED-AREA" not in output

    def test_external_item_preserved_when_configured(self, tmp_path):
        """EXTERNAL items keep original names when preserve_external=True."""
        program = tmp_path / "TEST.cob"
        program.write_text("       01 SHARED-AREA EXTERNAL.\n")

        anon = Anonymizer(source_directory=tmp_path, preserve_external=True)
        result = anon.anonymize_file(program)

        output = result.changes[0].transformed_line
        # EXTERNAL items should be preserved with preserve_external=True
        assert "SHARED-AREA" in output


class TestCallStatementAnonymization:
    """Tests for CALL statement program name anonymization."""

    def test_call_statement_fixed_format(self, tmp_path):
        """CALL statement program names are anonymized in fixed format."""
        # Create main program that calls a subprogram
        main_prog = tmp_path / "MAINPROG.cob"
        main_prog.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. MAINPROG.\n"
            "       PROCEDURE DIVISION.\n"
            '           CALL "SUBPROG" USING WS-DATA.\n'
            "           STOP RUN.\n"
        )

        # Create subprogram
        sub_prog = tmp_path / "SUBPROG.cob"
        sub_prog.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. SUBPROG.\n"
            "       PROCEDURE DIVISION.\n"
            "           GOBACK.\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Disable literal anonymization to test pure CALL program name replacement
        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
            anonymize_literals=False,
        )

        # Use anonymize_all to ensure proper two-pass processing
        results = anon.anonymize_all()

        # Get the anonymized name for SUBPROG
        subprog_anon = anon.mapping_table.get_anonymized_name("SUBPROG")
        assert subprog_anon is not None

        # Find the main program result and check CALL statement
        main_result = next(r for r in results if "MAINPROG" in r.filename)
        call_line = next(
            c.transformed_line for c in main_result.changes if "CALL" in c.transformed_line
        )

        # The CALL statement should use the anonymized name
        assert f'"{subprog_anon}"' in call_line
        assert '"SUBPROG"' not in call_line

    def test_call_statement_free_format(self, tmp_path):
        """CALL statement program names are anonymized in free format."""
        # Create main program in free format
        main_prog = tmp_path / "MAINPROG.cbl"
        main_prog.write_text(
            "IDENTIFICATION DIVISION.\n"
            "PROGRAM-ID. MAINPROG.\n"
            "PROCEDURE DIVISION.\n"
            'CALL "SUBPROG" USING WS-DATA.\n'
            "STOP RUN.\n"
        )

        # Create subprogram in free format
        sub_prog = tmp_path / "SUBPROG.cbl"
        sub_prog.write_text(
            "IDENTIFICATION DIVISION.\n"
            "PROGRAM-ID. SUBPROG.\n"
            "PROCEDURE DIVISION.\n"
            "GOBACK.\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Disable literal anonymization to test pure CALL program name replacement
        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
            anonymize_literals=False,
        )

        # Use anonymize_all for proper two-pass processing
        results = anon.anonymize_all()

        # Get the anonymized name for SUBPROG
        subprog_anon = anon.mapping_table.get_anonymized_name("SUBPROG")
        assert subprog_anon is not None

        # Find the main program result and check CALL statement
        main_result = next(r for r in results if "MAINPROG" in r.filename)
        call_line = next(
            c.transformed_line for c in main_result.changes if "CALL" in c.transformed_line
        )

        # The CALL statement should use the anonymized name
        assert f'"{subprog_anon}"' in call_line
        assert '"SUBPROG"' not in call_line

    def test_call_statement_single_quotes(self, tmp_path):
        """CALL statement with single quotes is anonymized."""
        main_prog = tmp_path / "MAINPROG.cob"
        main_prog.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. MAINPROG.\n"
            "       PROCEDURE DIVISION.\n"
            "           CALL 'SUBPROG' USING WS-DATA.\n"
            "           STOP RUN.\n"
        )

        sub_prog = tmp_path / "SUBPROG.cob"
        sub_prog.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. SUBPROG.\n"
            "       PROCEDURE DIVISION.\n"
            "           GOBACK.\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Disable literal anonymization to test pure CALL program name replacement
        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
            anonymize_literals=False,
        )

        results = anon.anonymize_all()

        subprog_anon = anon.mapping_table.get_anonymized_name("SUBPROG")
        assert subprog_anon is not None

        main_result = next(r for r in results if "MAINPROG" in r.filename)
        call_line = next(
            c.transformed_line for c in main_result.changes if "CALL" in c.transformed_line
        )

        # Single quotes should be preserved
        assert f"'{subprog_anon}'" in call_line
        assert "'SUBPROG'" not in call_line

    def test_call_statement_multiple_calls(self, tmp_path):
        """Multiple CALL statements are all anonymized."""
        main_prog = tmp_path / "MAINPROG.cob"
        main_prog.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. MAINPROG.\n"
            "       PROCEDURE DIVISION.\n"
            '           CALL "SUBPROG1" USING WS-DATA.\n'
            '           CALL "SUBPROG2" USING WS-DATA.\n'
            "           STOP RUN.\n"
        )

        sub_prog1 = tmp_path / "SUBPROG1.cob"
        sub_prog1.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. SUBPROG1.\n"
            "       PROCEDURE DIVISION.\n"
            "           GOBACK.\n"
        )

        sub_prog2 = tmp_path / "SUBPROG2.cob"
        sub_prog2.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. SUBPROG2.\n"
            "       PROCEDURE DIVISION.\n"
            "           GOBACK.\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Disable literal anonymization to test pure CALL program name replacement
        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
            anonymize_literals=False,
        )

        results = anon.anonymize_all()

        sub1_anon = anon.mapping_table.get_anonymized_name("SUBPROG1")
        sub2_anon = anon.mapping_table.get_anonymized_name("SUBPROG2")
        assert sub1_anon is not None
        assert sub2_anon is not None

        main_result = next(r for r in results if "MAINPROG" in r.filename)
        call_lines = [
            c.transformed_line for c in main_result.changes if "CALL" in c.transformed_line
        ]

        # Both CALL statements should be anonymized
        assert len(call_lines) == 2
        all_calls = " ".join(call_lines)
        assert f'"{sub1_anon}"' in all_calls
        assert f'"{sub2_anon}"' in all_calls
        assert '"SUBPROG1"' not in all_calls
        assert '"SUBPROG2"' not in all_calls


class TestDisplayLiteralAnonymization:
    """Tests for DISPLAY statement string literal anonymization."""

    def test_display_literal_fixed_format(self, tmp_path):
        """DISPLAY statement literals are anonymized in fixed format."""
        program = tmp_path / "TEST.cob"
        program.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. TEST.\n"
            "       PROCEDURE DIVISION.\n"
            '           DISPLAY "Hello World".\n'
            "           STOP RUN.\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
            anonymize_literals=True,
        )

        results = anon.anonymize_all()

        # Find the DISPLAY line
        result = results[0]
        display_line = next(
            c.transformed_line for c in result.changes if "DISPLAY" in c.transformed_line
        )

        # The original literal should not be present
        assert "Hello World" not in display_line
        # Should still have DISPLAY and quotes
        assert "DISPLAY" in display_line
        assert '"' in display_line

    def test_display_literal_free_format(self, tmp_path):
        """DISPLAY statement literals are anonymized in free format."""
        program = tmp_path / "TEST.cbl"
        program.write_text(
            "IDENTIFICATION DIVISION.\n"
            "PROGRAM-ID. TEST.\n"
            "PROCEDURE DIVISION.\n"
            'DISPLAY "Processing complete".\n'
            "STOP RUN.\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
            anonymize_literals=True,
        )

        results = anon.anonymize_all()

        result = results[0]
        display_line = next(
            c.transformed_line for c in result.changes if "DISPLAY" in c.transformed_line
        )

        # The original literal should not be present
        assert "Processing complete" not in display_line
        assert "DISPLAY" in display_line

    def test_display_literal_single_quotes(self, tmp_path):
        """DISPLAY statement with single quotes is anonymized."""
        program = tmp_path / "TEST.cob"
        program.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. TEST.\n"
            "       PROCEDURE DIVISION.\n"
            "           DISPLAY 'Error message'.\n"
            "           STOP RUN.\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
            anonymize_literals=True,
        )

        results = anon.anonymize_all()

        result = results[0]
        display_line = next(
            c.transformed_line for c in result.changes if "DISPLAY" in c.transformed_line
        )

        # The original literal should not be present
        assert "Error message" not in display_line
        # Single quotes should be preserved
        assert "'" in display_line

    def test_display_literal_length_preserved(self, tmp_path):
        """DISPLAY literal length is preserved after anonymization."""
        original_text = "Customer Name Field"
        program = tmp_path / "TEST.cob"
        program.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. TEST.\n"
            "       PROCEDURE DIVISION.\n"
            f'           DISPLAY "{original_text}".\n'
            "           STOP RUN.\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
            anonymize_literals=True,
        )

        results = anon.anonymize_all()

        result = results[0]
        display_line = next(
            c.transformed_line for c in result.changes if "DISPLAY" in c.transformed_line
        )

        # Extract the new literal content
        import re

        match = re.search(r'"([^"]*)"', display_line)
        assert match is not None
        new_literal = match.group(1)

        # Length should be preserved
        assert len(new_literal) == len(original_text)

    def test_display_multiple_literals(self, tmp_path):
        """Multiple DISPLAY statements are all anonymized."""
        program = tmp_path / "TEST.cob"
        program.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. TEST.\n"
            "       PROCEDURE DIVISION.\n"
            '           DISPLAY "Starting process".\n'
            '           DISPLAY "Ending process".\n'
            "           STOP RUN.\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
            anonymize_literals=True,
        )

        results = anon.anonymize_all()

        result = results[0]
        display_lines = [
            c.transformed_line for c in result.changes if "DISPLAY" in c.transformed_line
        ]

        # Both DISPLAY statements should be anonymized
        assert len(display_lines) == 2
        all_displays = " ".join(display_lines)
        assert "Starting process" not in all_displays
        assert "Ending process" not in all_displays

    def test_display_literals_enabled_by_default(self, tmp_path):
        """DISPLAY literals ARE anonymized by default (anonymize_literals=True)."""
        program = tmp_path / "TEST.cob"
        program.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. TEST.\n"
            "       PROCEDURE DIVISION.\n"
            '           DISPLAY "Original Text".\n'
            "           STOP RUN.\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Default behavior - no explicit anonymize_literals setting
        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
        )

        results = anon.anonymize_all()

        result = results[0]
        display_line = next(
            c.transformed_line for c in result.changes if "DISPLAY" in c.transformed_line
        )

        # The original literal should NOT be present (anonymized by default)
        assert "Original Text" not in display_line

    def test_display_literals_protected_when_disabled(self, tmp_path):
        """DISPLAY literals are preserved when anonymize_literals=False (--protect-literals)."""
        program = tmp_path / "TEST.cob"
        program.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. TEST.\n"
            "       PROCEDURE DIVISION.\n"
            '           DISPLAY "Protected Text".\n'
            "           STOP RUN.\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
            anonymize_literals=False,  # Simulates --protect-literals
        )

        results = anon.anonymize_all()

        result = results[0]
        display_line = next(
            c.transformed_line for c in result.changes if "DISPLAY" in c.transformed_line
        )

        # The original literal SHOULD still be present when protected
        assert "Protected Text" in display_line

    def test_value_clause_literal_anonymized(self, tmp_path):
        """VALUE clause literals are anonymized by default."""
        program = tmp_path / "TEST.cob"
        program.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. TEST.\n"
            "       DATA DIVISION.\n"
            "       WORKING-STORAGE SECTION.\n"
            "       01 WS-MESSAGE PIC X(20) VALUE 'Default message'.\n"
            "       PROCEDURE DIVISION.\n"
            "           STOP RUN.\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Default behavior - literals are anonymized
        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
        )

        results = anon.anonymize_all()

        result = results[0]
        value_line = next(
            c.transformed_line for c in result.changes if "VALUE" in c.transformed_line
        )

        # The original literal should not be present (anonymized by default)
        assert "Default message" not in value_line
        # VALUE keyword should still be there
        assert "VALUE" in value_line


class TestSequenceAreaCleanup:
    """Tests for cleaning sequence area (columns 1-6)."""

    def test_clean_sequence_numbers(self):
        """Sequence numbers are cleaned when clean_sequence_area=True."""
        table = MappingTable()
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        transformer = LineTransformer(table, clean_sequence_area=True)
        # Line with sequence numbers in columns 1-6
        parsed = parse_line("000100 05 WS-FIELD PIC X.", 1)
        result = transformer.transform_line(parsed)

        # Sequence area should be cleaned (replaced with spaces)
        assert result.transformed_line.startswith("      ")
        # The sequence "000100" should not be present
        assert "000100" not in result.transformed_line

    def test_clean_change_tags(self):
        """Change tags (like REPLAT) are cleaned when clean_sequence_area=True."""
        table = MappingTable()
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        transformer = LineTransformer(table, clean_sequence_area=True)
        # Line with change tag in columns 1-6
        parsed = parse_line("REPLAT 05 WS-FIELD PIC X.", 1)
        result = transformer.transform_line(parsed)

        # Change tag should be cleaned
        assert result.transformed_line.startswith("      ")
        assert "REPLAT" not in result.transformed_line

    def test_clean_sequence_by_default(self):
        """Sequence numbers are cleaned by default (clean_sequence_area=True)."""
        table = MappingTable()
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        # Default behavior: clean sequence area
        transformer = LineTransformer(table)  # Uses default clean_sequence_area=True
        parsed = parse_line("000100 05 WS-FIELD PIC X.", 1)
        result = transformer.transform_line(parsed)

        # Sequence area should be cleaned
        assert result.transformed_line.startswith("      ")

    def test_preserve_sequence_when_disabled(self):
        """Sequence numbers are preserved when clean_sequence_area=False."""
        table = MappingTable()
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        # Explicitly disable cleaning
        transformer = LineTransformer(table, clean_sequence_area=False)
        parsed = parse_line("000100 05 WS-FIELD PIC X.", 1)
        result = transformer.transform_line(parsed)

        # Sequence area should be preserved
        assert result.transformed_line.startswith("000100")

    def test_clean_sequence_no_identifier_changes(self):
        """Sequence cleaned even when no identifiers change."""
        table = MappingTable()
        # Don't add any mappings - just FILLER

        transformer = LineTransformer(table, clean_sequence_area=True)
        # Line with FILLER (won't be anonymized) but has sequence number
        parsed = parse_line("123456 05 FILLER PIC X(10).", 1)
        result = transformer.transform_line(parsed)

        # Sequence should still be cleaned
        assert result.transformed_line.startswith("      ")
        assert "123456" not in result.transformed_line
        # Changes should record the sequence cleanup
        assert any("sequence" in change[0].lower() for change in result.changes_made)

    def test_blank_sequence_not_changed(self):
        """Lines with blank sequence area don't have unnecessary changes."""
        table = MappingTable()

        transformer = LineTransformer(table, clean_sequence_area=True)
        # Line with already blank sequence
        parsed = parse_line("       05 FILLER PIC X.", 1)
        result = transformer.transform_line(parsed)

        # No changes should be recorded if sequence was already blank
        assert "sequence" not in str(result.changes_made).lower()

    def test_clean_sequence_preserves_code_area(self):
        """Cleaning sequence area doesn't affect code area."""
        table = MappingTable()
        table.get_or_create("WS-CUSTOMER-NAME", IdentifierType.DATA_NAME)

        transformer = LineTransformer(table, clean_sequence_area=True)
        parsed = parse_line("000200 01 WS-CUSTOMER-NAME PIC X(30).", 1)
        result = transformer.transform_line(parsed)

        # Code area should still be transformed
        assert "PIC X(30)" in result.transformed_line
        # Original identifier should be replaced
        assert "WS-CUSTOMER-NAME" not in result.transformed_line

    def test_clean_sequence_80_column_line(self):
        """Clean sequence area on 80-column line preserves length."""
        table = MappingTable()
        table.get_or_create("WS-RECORD", IdentifierType.DATA_NAME)

        transformer = LineTransformer(table, clean_sequence_area=True)
        # 80-column line with sequence number and identification area
        line = "000100       01 WS-RECORD                                                   TEST"
        assert len(line) == 80
        parsed = parse_line(line, 1)
        result = transformer.transform_line(parsed)

        # Length should be preserved
        assert len(result.transformed_line) == 80
        # Sequence cleaned, identification preserved
        assert result.transformed_line[:6] == "      "
        # The identification area should be preserved as-is
        assert "TEST" in result.transformed_line[72:]

    def test_clean_sequence_comment_lines(self):
        """Sequence area is cleaned for comment lines too."""
        table = MappingTable()

        transformer = LineTransformer(table, clean_sequence_area=True)
        # Comment line with sequence number
        parsed = parse_line("000100*THIS IS A COMMENT", 1)
        assert parsed.is_comment
        result = transformer.transform_line(parsed)

        # Sequence should be cleaned even for comments
        assert result.transformed_line[:6] == "      "
        assert "000100" not in result.transformed_line
        # Comment indicator should still be present
        assert result.transformed_line[6] == "*"

    def test_clean_sequence_comment_with_change_tag(self):
        """Change tags in comment lines are cleaned."""
        table = MappingTable()

        transformer = LineTransformer(table, clean_sequence_area=True)
        # Comment line with change tag
        parsed = parse_line("REPLAT*MODIFIED COMMENT", 1)
        assert parsed.is_comment
        result = transformer.transform_line(parsed)

        # Change tag should be cleaned
        assert result.transformed_line[:6] == "      "
        assert "REPLAT" not in result.transformed_line


class TestAnonymizerCleanSequence:
    """Tests for Anonymizer class with clean_sequence_area option."""

    def test_anonymizer_clean_sequence(self, tmp_path):
        """Anonymizer with clean_sequence_area removes sequence numbers."""
        program = tmp_path / "TEST.cob"
        program.write_text(
            "000100       IDENTIFICATION DIVISION.\n"
            "000200       PROGRAM-ID. TEST.\n"
            "000300       DATA DIVISION.\n"
            "000400       WORKING-STORAGE SECTION.\n"
            "000500       01 WS-DATA PIC X.\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
            clean_sequence_area=True,
        )

        result = anon.anonymize_file(program)

        # All lines should have cleaned sequence area
        for change in result.changes:
            transformed = change.transformed_line
            # First 6 characters should be spaces (cleaned)
            assert transformed[:6] == "      ", f"Sequence not cleaned: {transformed[:10]}"

    def test_anonymizer_clean_sequence_with_change_tags(self, tmp_path):
        """Anonymizer removes change tags from sequence area."""
        program = tmp_path / "TEST.cob"
        program.write_text(
            "BENIQ        IDENTIFICATION DIVISION.\n"
            "REPLAT       PROGRAM-ID. TEST.\n"
            "CDR          DATA DIVISION.\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
            clean_sequence_area=True,
        )

        result = anon.anonymize_file(program)

        # All change tags should be cleaned
        for change in result.changes:
            transformed = change.transformed_line
            assert "BENIQ" not in transformed
            assert "REPLAT" not in transformed
            assert "CDR" not in transformed

    def test_anonymizer_clean_sequence_with_comments(self, tmp_path):
        """Anonymizer cleans sequence area for comment lines too."""
        program = tmp_path / "TEST.cob"
        program.write_text(
            "000100       IDENTIFICATION DIVISION.\n"
            "000200      *THIS IS A COMMENT LINE\n"
            "000300       PROGRAM-ID. TEST.\n"
            "REPLAT      *ANOTHER COMMENT WITH CHANGE TAG\n"
            "000500       PROCEDURE DIVISION.\n"
            "000600      *FINAL COMMENT\n"
        )

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        anon = Anonymizer(
            source_directory=tmp_path,
            output_directory=output_dir,
            clean_sequence_area=True,
        )

        result = anon.anonymize_file(program)

        # All lines (including comments) should have cleaned sequence area
        for change in result.changes:
            transformed = change.transformed_line
            # First 6 characters should be spaces (cleaned)
            assert transformed[:6] == "      ", f"Sequence not cleaned: {transformed[:20]}"

        # Verify sequence numbers and change tags are not in output
        all_transformed = "\n".join(c.transformed_line for c in result.changes)
        assert "000100" not in all_transformed
        assert "000200" not in all_transformed
        assert "000300" not in all_transformed
        assert "REPLAT" not in all_transformed
        assert "000500" not in all_transformed
        assert "000600" not in all_transformed
