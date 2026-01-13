"""
Pytest configuration and fixtures for COBOL Anonymizer tests.
"""

import pytest
from pathlib import Path


@pytest.fixture
def sample_cobol_line():
    """A typical 80-column COBOL line."""
    return "      *    THIS IS A COMMENT LINE                                              "


@pytest.fixture
def sample_data_definition():
    """A typical data definition line."""
    return "       05 WS-CUSTOMER-NAME           PIC X(30).                               "


@pytest.fixture
def sample_move_statement():
    """A typical MOVE statement."""
    return "           MOVE WS-INPUT TO WS-OUTPUT.                                        "


@pytest.fixture
def original_dir(tmp_path):
    """Create a temporary directory with sample COBOL files."""
    cobol_dir = tmp_path / "original"
    cobol_dir.mkdir()
    return cobol_dir


@pytest.fixture
def output_dir(tmp_path):
    """Create a temporary output directory."""
    out_dir = tmp_path / "anonymized"
    out_dir.mkdir()
    return out_dir


@pytest.fixture
def sample_copybook(original_dir):
    """Create a sample copybook file."""
    content = """       01  WS-SAMPLE-RECORD.
           05 WS-FIELD-A           PIC X(10).
           05 WS-FIELD-B           PIC 9(5).
              88 WS-FIELD-B-VALID  VALUE 1 THRU 99999.
           05 WS-FIELD-C           PIC S9(7)V99 COMP-3.
"""
    copybook_path = original_dir / "SAMPLE01.cpy"
    copybook_path.write_text(content)
    return copybook_path


@pytest.fixture
def sample_program(original_dir, sample_copybook):
    """Create a sample COBOL program file."""
    content = """       IDENTIFICATION DIVISION.
       PROGRAM-ID.    TESTPROG.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY SAMPLE01.
       PROCEDURE DIVISION.
       MAIN-PROCESS.
           MOVE SPACES TO WS-FIELD-A.
           STOP RUN.
"""
    program_path = original_dir / "TESTPROG.cob"
    program_path.write_text(content)
    return program_path
