"""
Output Writer - Writes anonymized COBOL files with exact column alignment.

This module handles:
- Writing anonymized lines with correct column format
- Renaming output files (programs and copybooks)
- Preserving original file encoding
- Preserving line endings
- Validating column boundaries before writing
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from cobol_anonymizer.cobol.column_handler import (
    MAX_LINE_LENGTH,
    CODE_END,
    validate_code_area,
)
from cobol_anonymizer.exceptions import ColumnOverflowError


@dataclass
class WriteResult:
    """Result of writing a file."""
    source_path: Path
    output_path: Path
    original_name: str
    anonymized_name: str
    total_lines: int
    modified_lines: int
    encoding: str
    line_ending: str
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class WriterConfig:
    """Configuration for output writer."""
    output_directory: Optional[Path] = None
    preserve_encoding: bool = True
    default_encoding: str = "latin-1"
    preserve_line_ending: bool = True
    default_line_ending: str = "\n"
    validate_columns: bool = True
    create_directories: bool = True
    overwrite_existing: bool = False


def detect_encoding(file_path: Path) -> str:
    """
    Detect file encoding by reading and trying common encodings.

    Args:
        file_path: Path to the file

    Returns:
        Detected encoding name (defaults to latin-1)
    """
    if not file_path.exists():
        return "latin-1"  # Default for missing files

    encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                f.read()
            return encoding
        except UnicodeDecodeError:
            continue

    return "latin-1"  # Fallback


def detect_line_ending(file_path: Path, encoding: str = "latin-1") -> str:
    """
    Detect line ending style in a file.

    Args:
        file_path: Path to the file
        encoding: File encoding

    Returns:
        Line ending string ("\\n", "\\r\\n", or "\\r")
    """
    try:
        with open(file_path, "rb") as f:
            content = f.read(8192)  # Read first 8KB

        if b"\r\n" in content:
            return "\r\n"  # Windows
        elif b"\r" in content:
            return "\r"  # Old Mac
        else:
            return "\n"  # Unix
    except IOError:
        return "\n"


def validate_line_columns(line: str, line_number: int, filename: str) -> None:
    """
    Validate that a line doesn't exceed column limits.

    Args:
        line: The line to validate
        line_number: Line number for error reporting
        filename: Filename for error reporting

    Raises:
        ColumnOverflowError: If line exceeds limits
    """
    # Strip line ending
    stripped = line.rstrip("\r\n")

    # Check total line length
    if len(stripped) > MAX_LINE_LENGTH:
        raise ColumnOverflowError(
            file=filename,
            line=line_number,
            actual_length=len(stripped),
            max_length=MAX_LINE_LENGTH,
            message=f"Line exceeds {MAX_LINE_LENGTH} columns",
        )

    # Check code area (columns 8-72)
    if len(stripped) > 7:
        code_area = stripped[7:CODE_END]  # Columns 8-72
        if len(code_area) > CODE_END - 7:  # 65 characters
            raise ColumnOverflowError(
                file=filename,
                line=line_number,
                actual_length=len(code_area),
                max_length=CODE_END - 7,
                message="Code area exceeds column 72",
            )


class OutputWriter:
    """
    Writes anonymized COBOL files with correct formatting.

    Usage:
        writer = OutputWriter(config)
        result = writer.write_file(source, lines, output_name)
    """

    def __init__(self, config: Optional[WriterConfig] = None):
        """
        Initialize the output writer.

        Args:
            config: Writer configuration (uses defaults if not provided)
        """
        self.config = config or WriterConfig()
        self._write_results: List[WriteResult] = []

    def write_file(
        self,
        source_path: Path,
        lines: List[str],
        anonymized_name: Optional[str] = None,
        output_directory: Optional[Path] = None,
    ) -> WriteResult:
        """
        Write anonymized content to a file.

        Args:
            source_path: Original source file path
            lines: List of anonymized lines
            anonymized_name: Anonymized filename (uses original if not provided)
            output_directory: Override output directory

        Returns:
            WriteResult with details of the operation
        """
        # Detect original file properties
        encoding = (
            detect_encoding(source_path)
            if self.config.preserve_encoding and source_path.exists()
            else self.config.default_encoding
        )

        line_ending = (
            detect_line_ending(source_path, encoding)
            if self.config.preserve_line_ending and source_path.exists()
            else self.config.default_line_ending
        )

        # Determine output path
        out_dir = output_directory or self.config.output_directory or source_path.parent
        out_name = anonymized_name or source_path.name
        output_path = out_dir / out_name

        result = WriteResult(
            source_path=source_path,
            output_path=output_path,
            original_name=source_path.name,
            anonymized_name=out_name,
            total_lines=len(lines),
            modified_lines=0,  # Will be updated
            encoding=encoding,
            line_ending=line_ending,
        )

        try:
            # Create output directory if needed
            if self.config.create_directories and not out_dir.exists():
                out_dir.mkdir(parents=True, exist_ok=True)

            # Check for existing file
            if output_path.exists() and not self.config.overwrite_existing:
                result.success = False
                result.error_message = f"Output file already exists: {output_path}"
                return result

            # Validate columns if enabled
            if self.config.validate_columns:
                for i, line in enumerate(lines, 1):
                    validate_line_columns(line, i, out_name)

            # Write the file
            with open(output_path, "w", encoding=encoding, newline="") as f:
                for line in lines:
                    # Ensure correct line ending
                    stripped = line.rstrip("\r\n")
                    f.write(stripped + line_ending)

            result.success = True
            self._write_results.append(result)
            return result

        except ColumnOverflowError as e:
            result.success = False
            result.error_message = str(e)
            return result
        except IOError as e:
            result.success = False
            result.error_message = f"IO error: {e}"
            return result

    def write_files(
        self,
        files: Dict[Path, Tuple[List[str], Optional[str]]],
        output_directory: Optional[Path] = None,
    ) -> List[WriteResult]:
        """
        Write multiple anonymized files.

        Args:
            files: Dict mapping source path to (lines, anonymized_name)
            output_directory: Override output directory

        Returns:
            List of WriteResult for each file
        """
        results = []
        for source_path, (lines, anon_name) in files.items():
            result = self.write_file(source_path, lines, anon_name, output_directory)
            results.append(result)
        return results

    def get_results(self) -> List[WriteResult]:
        """Get all write results."""
        return list(self._write_results)

    def get_statistics(self) -> Dict[str, int]:
        """Get writing statistics."""
        successful = [r for r in self._write_results if r.success]
        failed = [r for r in self._write_results if not r.success]

        return {
            "total_files": len(self._write_results),
            "successful": len(successful),
            "failed": len(failed),
            "total_lines": sum(r.total_lines for r in successful),
        }


def write_anonymized_file(
    source_path: Path,
    lines: List[str],
    output_path: Path,
    encoding: str = "latin-1",
    line_ending: str = "\n",
) -> bool:
    """
    Convenience function to write a single anonymized file.

    Args:
        source_path: Original source file path
        lines: List of anonymized lines
        output_path: Where to write the output
        encoding: File encoding
        line_ending: Line ending to use

    Returns:
        True if successful, False otherwise
    """
    config = WriterConfig(
        output_directory=output_path.parent,
        default_encoding=encoding,
        default_line_ending=line_ending,
        overwrite_existing=True,
    )
    writer = OutputWriter(config)
    result = writer.write_file(source_path, lines, output_path.name)
    return result.success
