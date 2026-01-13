"""
Tests for Phase 4: Identifier Classification.

Tests for COBOL identifier classification by type.
"""

import pytest

from cobol_anonymizer.core.classifier import (
    IdentifierType,
    Division,
    DataSection,
    ClassifiedIdentifier,
    FileContext,
    IdentifierClassifier,
    classify_cobol_file,
)


class TestFileContext:
    """Tests for FileContext dataclass."""

    def test_initial_state(self):
        """FileContext has correct initial state."""
        ctx = FileContext(filename="TEST.cob")
        assert ctx.filename == "TEST.cob"
        assert ctx.current_division == Division.NONE
        assert ctx.in_procedure_division is False

    def test_enter_division(self):
        """enter_division updates state correctly."""
        ctx = FileContext(filename="TEST.cob")
        ctx.enter_division(Division.DATA)
        assert ctx.current_division == Division.DATA
        ctx.enter_division(Division.PROCEDURE)
        assert ctx.current_division == Division.PROCEDURE
        assert ctx.in_procedure_division is True

    def test_enter_section(self):
        """enter_section updates state correctly."""
        ctx = FileContext(filename="TEST.cob")
        ctx.enter_division(Division.DATA)
        ctx.enter_section(DataSection.WORKING_STORAGE)
        assert ctx.current_section == DataSection.WORKING_STORAGE

    def test_push_level(self):
        """push_level maintains level stack correctly."""
        ctx = FileContext(filename="TEST.cob")
        ctx.push_level(1, "WS-RECORD")
        ctx.push_level(5, "WS-FIELD-A")
        ctx.push_level(10, "WS-SUBFIELD")
        assert ctx.get_parent_name() == "WS-FIELD-A"

    def test_push_level_pops_higher(self):
        """push_level pops items with same or higher level."""
        ctx = FileContext(filename="TEST.cob")
        ctx.push_level(1, "WS-RECORD")
        ctx.push_level(5, "WS-FIELD-A")
        ctx.push_level(5, "WS-FIELD-B")  # Same level, should replace
        assert ctx.get_parent_name() == "WS-RECORD"


class TestClassifiedIdentifier:
    """Tests for ClassifiedIdentifier dataclass."""

    def test_basic_creation(self):
        """ClassifiedIdentifier can be created."""
        ident = ClassifiedIdentifier(
            name="WS-FIELD",
            type=IdentifierType.DATA_NAME,
            line_number=10,
            context="Level 05 data item",
            is_definition=True,
        )
        assert ident.name == "WS-FIELD"
        assert ident.type == IdentifierType.DATA_NAME
        assert ident.is_definition is True

    def test_with_level_number(self):
        """ClassifiedIdentifier with level number."""
        ident = ClassifiedIdentifier(
            name="WS-FLAG",
            type=IdentifierType.CONDITION_NAME,
            line_number=15,
            level_number=88,
            is_definition=True,
        )
        assert ident.level_number == 88


class TestClassifyProgramId:
    """Tests for PROGRAM-ID classification."""

    def test_classify_program_id(self):
        """Classify PROGRAM-ID declaration."""
        classifier = IdentifierClassifier("TEST.cob")
        results = classifier.classify_line("       PROGRAM-ID.    TESTPROG.", 1)
        assert len(results) == 1
        assert results[0].type == IdentifierType.PROGRAM_NAME
        assert results[0].name == "TESTPROG"
        assert results[0].is_definition is True

    def test_classify_program_id_simple(self):
        """Classify simple PROGRAM-ID."""
        classifier = IdentifierClassifier("TEST.cob")
        results = classifier.classify_line("PROGRAM-ID. MYPROG.", 1)
        assert len(results) == 1
        assert results[0].name == "MYPROG"


class TestClassifyCopyStatement:
    """Tests for COPY statement classification."""

    def test_classify_copy_simple(self):
        """Classify simple COPY statement."""
        classifier = IdentifierClassifier("TEST.cob")
        results = classifier.classify_line("COPY SAMPLE01.", 10)
        assert len(results) == 1
        assert results[0].type == IdentifierType.COPYBOOK_NAME
        assert results[0].name == "SAMPLE01"

    def test_classify_copy_with_replacing(self):
        """Classify COPY with REPLACING."""
        classifier = IdentifierClassifier("TEST.cob")
        results = classifier.classify_line("COPY COPYBOOK REPLACING ==OLD== BY ==NEW==.", 10)
        assert any(r.type == IdentifierType.COPYBOOK_NAME for r in results)
        copybook = [r for r in results if r.type == IdentifierType.COPYBOOK_NAME][0]
        assert copybook.name == "COPYBOOK"


class TestClassifyDataDefinition:
    """Tests for data definition classification."""

    def test_classify_01_level(self):
        """Classify 01 level record definition."""
        classifier = IdentifierClassifier("TEST.cob")
        results = classifier.classify_line("01 WS-RECORD.", 5)
        assert len(results) == 1
        assert results[0].type == IdentifierType.DATA_NAME
        assert results[0].name == "WS-RECORD"
        assert results[0].level_number == 1

    def test_classify_05_level_with_pic(self):
        """Classify 05 level with PIC clause."""
        classifier = IdentifierClassifier("TEST.cob")
        results = classifier.classify_line("05 WS-FIELD PIC X(30).", 6)
        assert len(results) == 1
        assert results[0].type == IdentifierType.DATA_NAME
        assert results[0].name == "WS-FIELD"
        assert results[0].level_number == 5

    def test_classify_88_level(self):
        """Classify 88 level condition name."""
        classifier = IdentifierClassifier("TEST.cob")
        results = classifier.classify_line("88 WS-VALID VALUE 'Y'.", 7)
        assert len(results) == 1
        assert results[0].type == IdentifierType.CONDITION_NAME
        assert results[0].name == "WS-VALID"
        assert results[0].level_number == 88

    def test_classify_77_level(self):
        """Classify 77 level standalone item."""
        classifier = IdentifierClassifier("TEST.cob")
        results = classifier.classify_line("77 WS-COUNTER PIC 9(5).", 8)
        assert len(results) == 1
        assert results[0].type == IdentifierType.DATA_NAME
        assert results[0].level_number == 77

    def test_classify_indexed_by(self):
        """Classify INDEXED BY index name."""
        classifier = IdentifierClassifier("TEST.cob")
        results = classifier.classify_line("05 WS-TABLE OCCURS 10 INDEXED BY WS-IDX.", 9)
        # Should find both the data name and the index name
        data_names = [r for r in results if r.type == IdentifierType.DATA_NAME]
        index_names = [r for r in results if r.type == IdentifierType.INDEX_NAME]
        assert len(data_names) == 1
        assert len(index_names) == 1
        assert index_names[0].name == "WS-IDX"


class TestClassifyExternalItems:
    """Tests for EXTERNAL item classification."""

    def test_classify_external_data_item(self):
        """Classify EXTERNAL data item (should not anonymize)."""
        classifier = IdentifierClassifier("TEST.cob")
        results = classifier.classify_line("01 SHARED-AREA EXTERNAL.", 10)
        assert len(results) == 1
        assert results[0].type == IdentifierType.EXTERNAL_NAME
        assert results[0].is_external is True

    def test_external_block_propagates(self):
        """EXTERNAL flag propagates to nested items."""
        classifier = IdentifierClassifier("TEST.cob")
        classifier.classify_line("01 SHARED-AREA EXTERNAL.", 10)
        # The context should now have is_external_block = True
        assert classifier.context.is_external_block is True


class TestClassifyProcedureDivision:
    """Tests for PROCEDURE DIVISION classification."""

    def test_classify_section_name(self):
        """Classify SECTION name in PROCEDURE DIVISION."""
        classifier = IdentifierClassifier("TEST.cob")
        # First, establish we're in PROCEDURE DIVISION
        classifier.classify_line("PROCEDURE DIVISION.", 100)
        results = classifier.classify_line("MAIN-SECTION SECTION.", 101)
        assert len(results) == 1
        assert results[0].type == IdentifierType.SECTION_NAME
        assert results[0].name == "MAIN-SECTION"

    def test_classify_paragraph_name(self):
        """Classify paragraph name in PROCEDURE DIVISION."""
        classifier = IdentifierClassifier("TEST.cob")
        classifier.classify_line("PROCEDURE DIVISION.", 100)
        results = classifier.classify_line("A001-INIT.", 102)
        assert len(results) == 1
        assert results[0].type == IdentifierType.PARAGRAPH_NAME
        assert results[0].name == "A001-INIT"

    def test_paragraph_not_detected_in_data_division(self):
        """Paragraph detection only in PROCEDURE DIVISION."""
        classifier = IdentifierClassifier("TEST.cob")
        classifier.classify_line("DATA DIVISION.", 50)
        results = classifier.classify_line("WS-RECORD.", 51)
        # Should NOT be classified as paragraph
        assert not any(r.type == IdentifierType.PARAGRAPH_NAME for r in results)


class TestClassifyFileDefinition:
    """Tests for FD/SD file classification."""

    def test_classify_fd_declaration(self):
        """Classify FD file declaration."""
        classifier = IdentifierClassifier("TEST.cob")
        results = classifier.classify_line("FD INPUT-FILE", 20)
        assert len(results) == 1
        assert results[0].type == IdentifierType.FILE_NAME
        assert results[0].name == "INPUT-FILE"

    def test_classify_sd_declaration(self):
        """Classify SD sort file declaration."""
        classifier = IdentifierClassifier("TEST.cob")
        results = classifier.classify_line("SD SORT-FILE", 25)
        assert len(results) == 1
        assert results[0].type == IdentifierType.FILE_NAME


class TestClassifyReferences:
    """Tests for identifier reference classification."""

    def test_classify_reference_in_move(self):
        """Classify references in MOVE statement."""
        classifier = IdentifierClassifier("TEST.cob")
        # First define the identifiers
        classifier.classify_line("05 WS-A PIC X.", 5)
        classifier.classify_line("05 WS-B PIC X.", 6)
        # Then use them
        classifier.classify_line("PROCEDURE DIVISION.", 100)
        results = classifier.classify_line("MOVE WS-A TO WS-B.", 101)
        # Should have references to WS-A and WS-B
        refs = [r for r in results if not r.is_definition]
        assert len(refs) >= 2


class TestClassifyCobolFile:
    """Tests for full file classification."""

    def test_classify_simple_program(self):
        """Classify a simple COBOL program."""
        lines = [
            "IDENTIFICATION DIVISION.",
            "PROGRAM-ID. TESTPROG.",
            "DATA DIVISION.",
            "WORKING-STORAGE SECTION.",
            "01 WS-RECORD.",
            "   05 WS-FIELD PIC X(10).",
            "PROCEDURE DIVISION.",
            "MAIN-PARA.",
            "   MOVE SPACES TO WS-FIELD.",
            "   STOP RUN.",
        ]
        results = classify_cobol_file(lines, "TESTPROG.cob")

        # Check for program name
        programs = [r for r in results if r.type == IdentifierType.PROGRAM_NAME]
        assert len(programs) == 1
        assert programs[0].name == "TESTPROG"

        # Check for data names
        data_names = [r for r in results if r.type == IdentifierType.DATA_NAME]
        names = [d.name for d in data_names if d.is_definition]
        assert "WS-RECORD" in names
        assert "WS-FIELD" in names

        # Check for paragraph
        paragraphs = [r for r in results if r.type == IdentifierType.PARAGRAPH_NAME]
        assert len(paragraphs) == 1
        assert paragraphs[0].name == "MAIN-PARA"


class TestIdentifierClassifierMethods:
    """Tests for IdentifierClassifier helper methods."""

    def test_get_definitions(self):
        """get_definitions returns only definitions."""
        classifier = IdentifierClassifier("TEST.cob")
        classifier.classify_line("01 WS-FIELD PIC X.", 1)
        classifier.classify_line("PROCEDURE DIVISION.", 10)
        classifier.classify_line("MOVE WS-FIELD TO WS-OTHER.", 11)

        definitions = classifier.get_definitions()
        assert all(d.is_definition for d in definitions)

    def test_get_identifiers_by_type(self):
        """get_identifiers_by_type filters correctly."""
        classifier = IdentifierClassifier("TEST.cob")
        classifier.classify_line("01 WS-FIELD PIC X.", 1)
        classifier.classify_line("88 WS-VALID VALUE 'Y'.", 2)

        data_names = classifier.get_identifiers_by_type(IdentifierType.DATA_NAME)
        conditions = classifier.get_identifiers_by_type(IdentifierType.CONDITION_NAME)

        assert len(data_names) == 1
        assert len(conditions) == 1


class TestContextTracking:
    """Tests for context tracking across lines."""

    def test_division_tracking(self):
        """Track division changes."""
        classifier = IdentifierClassifier("TEST.cob")
        classifier.classify_line("IDENTIFICATION DIVISION.", 1)
        assert classifier.context.current_division == Division.IDENTIFICATION

        classifier.classify_line("DATA DIVISION.", 10)
        assert classifier.context.current_division == Division.DATA

        classifier.classify_line("PROCEDURE DIVISION.", 50)
        assert classifier.context.current_division == Division.PROCEDURE
        assert classifier.context.in_procedure_division is True

    def test_section_tracking(self):
        """Track section changes."""
        classifier = IdentifierClassifier("TEST.cob")
        classifier.classify_line("DATA DIVISION.", 10)
        classifier.classify_line("WORKING-STORAGE SECTION.", 11)
        assert classifier.context.current_section == DataSection.WORKING_STORAGE

    def test_level_hierarchy_tracking(self):
        """Track level hierarchy for parent names."""
        classifier = IdentifierClassifier("TEST.cob")
        classifier.classify_line("01 WS-RECORD.", 1)
        classifier.classify_line("   05 WS-GROUP.", 2)
        classifier.classify_line("      10 WS-ITEM PIC X.", 3)

        # After the third line, parent should be WS-GROUP
        results = classifier.get_all_identifiers()
        ws_item = [r for r in results if r.name == "WS-ITEM"][0]
        assert ws_item.parent_name == "WS-GROUP"
