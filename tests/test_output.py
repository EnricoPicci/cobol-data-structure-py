"""
Tests for Phase 9: Output Writer and Validator.

Tests for writing anonymized files and validation.
"""

from pathlib import Path

import pytest

from cobol_anonymizer.core.anonymizer import FileTransformResult, TransformResult
from cobol_anonymizer.core.classifier import IdentifierType
from cobol_anonymizer.core.mapper import MappingTable
from cobol_anonymizer.exceptions import ColumnOverflowError
from cobol_anonymizer.output.report import (
    AnonymizationReport,
    FileStatistics,
    ReportGenerator,
    create_mapping_report,
    create_summary_report,
)
from cobol_anonymizer.output.validator import (
    OutputValidator,
    ValidationResult,
    validate_mapping_table,
)
from cobol_anonymizer.output.writer import (
    OutputWriter,
    WriterConfig,
    detect_encoding,
    detect_line_ending,
    validate_line_columns,
    write_anonymized_file,
)


class TestDetectEncoding:
    """Tests for encoding detection."""

    def test_detect_utf8(self, tmp_path):
        """Detect UTF-8 encoding."""
        f = tmp_path / "test.cob"
        f.write_text("UTF-8 content", encoding="utf-8")
        encoding = detect_encoding(f)
        assert encoding in ["utf-8", "latin-1"]  # Both work for ASCII

    def test_detect_latin1(self, tmp_path):
        """Detect Latin-1 encoding."""
        f = tmp_path / "test.cob"
        f.write_bytes("Latin-1 content with \xe9".encode("latin-1"))
        encoding = detect_encoding(f)
        assert encoding == "latin-1"

    def test_default_for_missing_file(self, tmp_path):
        """Return default for nonexistent file."""
        f = tmp_path / "nonexistent.cob"
        encoding = detect_encoding(f)
        assert encoding == "latin-1"


class TestDetectLineEnding:
    """Tests for line ending detection."""

    def test_detect_unix(self, tmp_path):
        """Detect Unix line endings."""
        f = tmp_path / "test.cob"
        f.write_bytes(b"line1\nline2\n")
        ending = detect_line_ending(f)
        assert ending == "\n"

    def test_detect_windows(self, tmp_path):
        """Detect Windows line endings."""
        f = tmp_path / "test.cob"
        f.write_bytes(b"line1\r\nline2\r\n")
        ending = detect_line_ending(f)
        assert ending == "\r\n"

    def test_detect_old_mac(self, tmp_path):
        """Detect old Mac line endings."""
        f = tmp_path / "test.cob"
        f.write_bytes(b"line1\rline2\r")
        ending = detect_line_ending(f)
        assert ending == "\r"


class TestValidateLineColumns:
    """Tests for column validation."""

    def test_valid_line(self):
        """Line within limits passes."""
        line = "       01 WS-FIELD PIC X(10)."
        validate_line_columns(line, 1, "test.cob")  # Should not raise

    def test_line_exceeds_80(self):
        """Line over 80 chars raises error."""
        line = "A" * 81
        with pytest.raises(ColumnOverflowError):
            validate_line_columns(line, 1, "test.cob")

    def test_line_exactly_80(self):
        """Line exactly 80 chars is valid."""
        line = "A" * 80
        validate_line_columns(line, 1, "test.cob")


class TestOutputWriter:
    """Tests for OutputWriter class."""

    def test_create_writer(self):
        """Create writer with default config."""
        writer = OutputWriter()
        assert writer is not None

    def test_write_simple_file(self, tmp_path):
        """Write a simple file."""
        source = tmp_path / "source.cob"
        source.write_text("       01 WS-FIELD PIC X.\n")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = WriterConfig(output_directory=output_dir, overwrite_existing=True)
        writer = OutputWriter(config)

        lines = ["       01 D0000001 PIC X."]
        result = writer.write_file(source, lines)

        assert result.success
        assert (output_dir / "source.cob").exists()

    def test_write_with_renamed_file(self, tmp_path):
        """Write file with anonymized name."""
        source = tmp_path / "MYPROG.cob"
        source.write_text("       01 WS-FIELD PIC X.\n")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = WriterConfig(output_directory=output_dir, overwrite_existing=True)
        writer = OutputWriter(config)

        lines = ["       01 D0000001 PIC X."]
        result = writer.write_file(source, lines, "PG000001.cob")

        assert result.success
        assert result.anonymized_name == "PG000001.cob"
        assert (output_dir / "PG000001.cob").exists()

    def test_preserve_line_endings(self, tmp_path):
        """Preserve original line endings."""
        source = tmp_path / "source.cob"
        source.write_bytes(b"       01 WS-FIELD PIC X.\r\n")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = WriterConfig(
            output_directory=output_dir,
            preserve_line_ending=True,
            overwrite_existing=True,
        )
        writer = OutputWriter(config)

        lines = ["       01 D0000001 PIC X."]
        result = writer.write_file(source, lines)

        assert result.success
        assert result.line_ending == "\r\n"

    def test_write_creates_directory(self, tmp_path):
        """Writer creates output directory if needed."""
        source = tmp_path / "source.cob"
        source.write_text("       01 WS-FIELD PIC X.\n")

        output_dir = tmp_path / "new" / "deep" / "dir"

        config = WriterConfig(
            output_directory=output_dir,
            create_directories=True,
            overwrite_existing=True,
        )
        writer = OutputWriter(config)

        lines = ["       01 D0000001 PIC X."]
        result = writer.write_file(source, lines)

        assert result.success
        assert output_dir.exists()

    def test_no_overwrite_existing(self, tmp_path):
        """Don't overwrite existing file when disabled."""
        source = tmp_path / "source.cob"
        source.write_text("original content")

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        existing = output_dir / "source.cob"
        existing.write_text("existing content")

        config = WriterConfig(output_directory=output_dir, overwrite_existing=False)
        writer = OutputWriter(config)

        result = writer.write_file(source, ["new content"])

        assert not result.success
        assert "already exists" in result.error_message

    def test_get_statistics(self, tmp_path):
        """Get writer statistics."""
        source = tmp_path / "source.cob"
        source.write_text("content\n")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = WriterConfig(output_directory=output_dir, overwrite_existing=True)
        writer = OutputWriter(config)

        writer.write_file(source, ["line1", "line2"])

        stats = writer.get_statistics()
        assert stats["total_files"] == 1
        assert stats["successful"] == 1
        assert stats["total_lines"] == 2


class TestOutputValidator:
    """Tests for OutputValidator class."""

    def test_create_validator(self):
        """Create validator with default config."""
        validator = OutputValidator()
        assert validator is not None

    def test_validate_valid_file(self, tmp_path):
        """Validate a valid file."""
        f = tmp_path / "test.cob"
        f.write_text("       01 WS-FIELD PIC X(10).\n")

        validator = OutputValidator()
        result = validator.validate_file(f)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_missing_file(self, tmp_path):
        """Validation fails for missing file."""
        f = tmp_path / "nonexistent.cob"

        validator = OutputValidator()
        result = validator.validate_file(f)

        assert not result.is_valid
        assert len(result.errors) == 1

    def test_validate_line_too_long(self, tmp_path):
        """Detect line exceeding 80 chars."""
        f = tmp_path / "test.cob"
        f.write_text("A" * 85 + "\n")

        validator = OutputValidator()
        result = validator.validate_file(f)

        assert not result.is_valid
        assert any("exceeds" in e.message for e in result.errors)

    def test_validate_multiple_files(self, tmp_path):
        """Validate multiple files."""
        f1 = tmp_path / "test1.cob"
        f1.write_text("       01 WS-FIELD PIC X.\n")

        f2 = tmp_path / "test2.cob"
        f2.write_text("       01 WS-OTHER PIC 9.\n")

        validator = OutputValidator()
        result = validator.validate_files([f1, f2])

        assert result.is_valid
        assert result.files_validated == 2

    def test_validate_directory(self, tmp_path):
        """Validate all files in directory."""
        f1 = tmp_path / "test1.cob"
        f1.write_text("       01 WS-FIELD PIC X.\n")

        f2 = tmp_path / "test2.cpy"
        f2.write_text("       01 WS-COPY PIC 9.\n")

        validator = OutputValidator()
        result = validator.validate_directory(tmp_path)

        assert result.is_valid
        assert result.files_validated == 2


class TestValidateMappingTable:
    """Tests for mapping table validation."""

    def test_valid_mapping_table(self):
        """Valid mapping table passes."""
        table = MappingTable()
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        result = validate_mapping_table(table)
        assert result.is_valid

    def test_identifier_too_long(self):
        """Detect identifier exceeding 30 chars."""
        table = MappingTable()
        # Manually add an invalid entry
        from cobol_anonymizer.core.mapper import MappingEntry

        entry = MappingEntry(
            original_name="SHORT",
            anonymized_name="A" * 35,
            id_type=IdentifierType.DATA_NAME,
        )
        table._mappings["SHORT"] = entry

        result = validate_mapping_table(table)
        assert not result.is_valid
        assert any("exceeds 30" in e.message for e in result.errors)

    def test_leading_hyphen(self):
        """Detect identifier with leading hyphen."""
        table = MappingTable()
        from cobol_anonymizer.core.mapper import MappingEntry

        entry = MappingEntry(
            original_name="FIELD",
            anonymized_name="-INVALID",
            id_type=IdentifierType.DATA_NAME,
        )
        table._mappings["FIELD"] = entry

        result = validate_mapping_table(table)
        assert not result.is_valid

    def test_trailing_hyphen(self):
        """Detect identifier with trailing hyphen."""
        table = MappingTable()
        from cobol_anonymizer.core.mapper import MappingEntry

        entry = MappingEntry(
            original_name="FIELD",
            anonymized_name="INVALID-",
            id_type=IdentifierType.DATA_NAME,
        )
        table._mappings["FIELD"] = entry

        result = validate_mapping_table(table)
        assert not result.is_valid


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_is_valid_no_errors(self):
        """Result is valid with no errors."""
        result = ValidationResult()
        result.add_warning("Just a warning")
        assert result.is_valid

    def test_is_invalid_with_errors(self):
        """Result is invalid with errors."""
        result = ValidationResult()
        result.add_error("An error")
        assert not result.is_valid

    def test_get_errors(self):
        """Get only errors."""
        result = ValidationResult()
        result.add_error("Error 1")
        result.add_warning("Warning 1")
        result.add_error("Error 2")

        errors = result.errors
        assert len(errors) == 2

    def test_get_warnings(self):
        """Get only warnings."""
        result = ValidationResult()
        result.add_error("Error 1")
        result.add_warning("Warning 1")
        result.add_warning("Warning 2")

        warnings = result.warnings
        assert len(warnings) == 2


class TestFileStatistics:
    """Tests for FileStatistics dataclass."""

    def test_to_dict(self):
        """Convert to dictionary."""
        stats = FileStatistics(
            filename="TEST.cob",
            anonymized_filename="PG000001.cob",
            total_lines=100,
            transformed_lines=50,
            identifiers_found=25,
        )
        data = stats.to_dict()
        assert data["filename"] == "TEST.cob"
        assert data["total_lines"] == 100


class TestAnonymizationReport:
    """Tests for AnonymizationReport class."""

    def test_create_report(self):
        """Create an anonymization report."""
        report = AnonymizationReport(
            source_directory="/source",
            output_directory="/output",
            total_files=10,
            total_lines=1000,
        )
        assert report.total_files == 10

    def test_to_dict(self):
        """Convert report to dictionary."""
        report = AnonymizationReport(
            total_files=5,
            total_lines=500,
        )
        data = report.to_dict()
        assert "metadata" in data
        assert "summary" in data
        assert data["summary"]["total_files"] == 5

    def test_to_json(self):
        """Convert report to JSON."""
        report = AnonymizationReport(total_files=3)
        json_str = report.to_json()
        assert "total_files" in json_str
        assert "3" in json_str

    def test_to_text(self):
        """Convert report to text."""
        report = AnonymizationReport(
            total_files=5,
            total_lines=500,
            total_identifiers=100,
        )
        text = report.to_text()
        assert "COBOL ANONYMIZATION REPORT" in text
        assert "Total Files: 5" in text

    def test_save_json(self, tmp_path):
        """Save report as JSON file."""
        report = AnonymizationReport(total_files=3)
        path = tmp_path / "report.json"
        report.save_json(path)

        assert path.exists()
        content = path.read_text()
        assert "total_files" in content

    def test_save_text(self, tmp_path):
        """Save report as text file."""
        report = AnonymizationReport(total_files=3)
        path = tmp_path / "report.txt"
        report.save_text(path)

        assert path.exists()
        content = path.read_text()
        assert "REPORT" in content


class TestReportGenerator:
    """Tests for ReportGenerator class."""

    def test_create_generator(self):
        """Create report generator."""
        generator = ReportGenerator()
        assert generator is not None

    def test_generate_report(self):
        """Generate report from results."""
        table = MappingTable()
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        generator = ReportGenerator(
            mapping_table=table,
            source_directory=Path("/source"),
            output_directory=Path("/output"),
        )

        result = TransformResult(
            line_number=1,
            original_line="       01 WS-FIELD PIC X.",
            transformed_line="       01 D0000001 PIC X.",
            changes_made=[("WS-FIELD", "D0000001")],
        )

        file_result = FileTransformResult(
            filename="TEST.cob",
            original_path=Path("/source/TEST.cob"),
            total_lines=1,
            transformed_lines=1,
            changes=[result],
            warnings=[],
        )

        report = generator.generate_report([file_result], processing_time=1.5)

        assert report.total_files == 1
        assert report.total_lines == 1
        assert report.processing_time_seconds == 1.5


class TestCreateMappingReport:
    """Tests for create_mapping_report function."""

    def test_create_report(self):
        """Create mapping report text."""
        table = MappingTable()
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        table.get_or_create("TESTPROG", IdentifierType.PROGRAM_NAME)

        report = create_mapping_report(table)

        assert "WS-FIELD" in report
        assert "TESTPROG" in report
        assert "DATA_NAME" in report

    def test_report_shows_external(self):
        """Report shows external markers."""
        table = MappingTable()
        table.get_or_create("SHARED", IdentifierType.EXTERNAL_NAME, is_external=True)

        report = create_mapping_report(table)

        assert "[EXTERNAL]" in report


class TestCreateSummaryReport:
    """Tests for create_summary_report function."""

    def test_create_summary(self):
        """Create summary report."""
        table = MappingTable()
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        result = TransformResult(
            line_number=1,
            original_line="       01 WS-FIELD PIC X.",
            transformed_line="       01 D0000001 PIC X.",
            changes_made=[("WS-FIELD", "D0000001")],
        )

        file_result = FileTransformResult(
            filename="TEST.cob",
            original_path=Path("/source/TEST.cob"),
            total_lines=100,
            transformed_lines=50,
            changes=[result],
            warnings=[],
        )

        summary = create_summary_report([file_result], table)

        assert "Files processed: 1" in summary
        assert "Total lines: 100" in summary


class TestWriteAnonymizedFileFunction:
    """Tests for convenience function."""

    def test_write_simple(self, tmp_path):
        """Write with convenience function."""
        source = tmp_path / "source.cob"
        source.write_text("content\n")

        output = tmp_path / "output.cob"

        success = write_anonymized_file(
            source,
            ["       01 D0000001 PIC X."],
            output,
        )

        assert success
        assert output.exists()
