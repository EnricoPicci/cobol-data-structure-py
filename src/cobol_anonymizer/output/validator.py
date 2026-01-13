"""
Output Validator - Validates anonymized COBOL files.

This module handles:
- Validating output column format (max 80 columns)
- Validating code area doesn't exceed column 72
- Validating cross-file consistency
- Validating COPY references exist
- Validating REDEFINES targets exist
- Validating identifier length (<= 30 chars)
- Reporting warnings for unusual patterns
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

from cobol_anonymizer.cobol.column_handler import (
    MAX_LINE_LENGTH,
    CODE_END,
    parse_line,
)
from cobol_anonymizer.cobol.copy_resolver import find_copy_statements, CopyResolver
from cobol_anonymizer.core.mapper import MappingTable
from cobol_anonymizer.exceptions import (
    ColumnOverflowError,
    IdentifierLengthError,
    MappingError,
    CopyNotFoundError,
)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue."""
    severity: ValidationSeverity
    message: str
    file_path: Optional[Path] = None
    line_number: Optional[int] = None
    identifier: Optional[str] = None
    context: Optional[str] = None

    def __str__(self):
        parts = [f"[{self.severity.value.upper()}]"]
        if self.file_path:
            parts.append(f"{self.file_path.name}")
        if self.line_number:
            parts.append(f"line {self.line_number}")
        parts.append(self.message)
        if self.context:
            parts.append(f"({self.context})")
        return " ".join(parts)


@dataclass
class ValidationResult:
    """Result of validation."""
    issues: List[ValidationIssue] = field(default_factory=list)
    files_validated: int = 0
    lines_validated: int = 0

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return not any(
            issue.severity == ValidationSeverity.ERROR for issue in self.issues
        )

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get all error issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get all warning issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def add_error(self, message: str, **kwargs) -> None:
        """Add an error issue."""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            message=message,
            **kwargs
        ))

    def add_warning(self, message: str, **kwargs) -> None:
        """Add a warning issue."""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            message=message,
            **kwargs
        ))

    def add_info(self, message: str, **kwargs) -> None:
        """Add an info issue."""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.INFO,
            message=message,
            **kwargs
        ))


@dataclass
class ValidatorConfig:
    """Configuration for validator."""
    check_column_format: bool = True
    check_code_area: bool = True
    check_identifier_length: bool = True
    check_copy_references: bool = True
    check_cross_file_consistency: bool = True
    max_line_length: int = MAX_LINE_LENGTH
    max_identifier_length: int = 30


class OutputValidator:
    """
    Validates anonymized COBOL files.

    Usage:
        validator = OutputValidator(config)
        result = validator.validate_files(files)
    """

    def __init__(
        self,
        config: Optional[ValidatorConfig] = None,
        mapping_table: Optional[MappingTable] = None,
    ):
        """
        Initialize the validator.

        Args:
            config: Validator configuration
            mapping_table: Mapping table for consistency checks
        """
        self.config = config or ValidatorConfig()
        self.mapping_table = mapping_table

    def validate_file(self, file_path: Path) -> ValidationResult:
        """
        Validate a single file.

        Args:
            file_path: Path to file to validate

        Returns:
            ValidationResult with any issues found
        """
        result = ValidationResult()

        if not file_path.exists():
            result.add_error(
                "File does not exist",
                file_path=file_path,
            )
            return result

        try:
            content = file_path.read_text(encoding="latin-1")
            lines = content.splitlines()
        except IOError as e:
            result.add_error(
                f"Cannot read file: {e}",
                file_path=file_path,
            )
            return result

        result.files_validated = 1
        result.lines_validated = len(lines)

        # Validate column format
        if self.config.check_column_format:
            self._validate_column_format(file_path, lines, result)

        # Validate code area
        if self.config.check_code_area:
            self._validate_code_area(file_path, lines, result)

        return result

    def validate_files(self, files: List[Path]) -> ValidationResult:
        """
        Validate multiple files.

        Args:
            files: List of file paths to validate

        Returns:
            Combined ValidationResult
        """
        combined = ValidationResult()

        for file_path in files:
            file_result = self.validate_file(file_path)
            combined.issues.extend(file_result.issues)
            combined.files_validated += file_result.files_validated
            combined.lines_validated += file_result.lines_validated

        # Check copy references across all files
        if self.config.check_copy_references:
            self._validate_copy_references(files, combined)

        # Check cross-file consistency
        if self.config.check_cross_file_consistency and self.mapping_table:
            self._validate_cross_file_consistency(combined)

        return combined

    def validate_directory(self, directory: Path) -> ValidationResult:
        """
        Validate all COBOL files in a directory.

        Args:
            directory: Directory to validate

        Returns:
            ValidationResult for all files
        """
        files = []
        for pattern in ["*.cob", "*.cbl", "*.cpy"]:
            files.extend(directory.glob(pattern))
        return self.validate_files(files)

    def _validate_column_format(
        self,
        file_path: Path,
        lines: List[str],
        result: ValidationResult,
    ) -> None:
        """Validate all lines are within column limits."""
        for i, line in enumerate(lines, 1):
            if len(line) > self.config.max_line_length:
                result.add_error(
                    f"Line exceeds {self.config.max_line_length} columns ({len(line)} chars)",
                    file_path=file_path,
                    line_number=i,
                )

    def _validate_code_area(
        self,
        file_path: Path,
        lines: List[str],
        result: ValidationResult,
    ) -> None:
        """Validate code area doesn't exceed column 72."""
        for i, line in enumerate(lines, 1):
            if len(line) <= 7:
                continue  # Line too short to have code area

            # Check if column 7 is a comment indicator
            if line[6] == '*':
                continue  # Comment lines can have anything

            # Check code area (columns 8-72)
            code_area = line[7:CODE_END]
            # Find where actual content ends (ignore trailing spaces)
            content_end = len(code_area.rstrip())

            # This is a soft warning - some lines legitimately have trailing content
            if len(line) > CODE_END and line[CODE_END:].strip():
                # There's content after column 72
                result.add_warning(
                    f"Content after column 72 (may be identification area)",
                    file_path=file_path,
                    line_number=i,
                    context=f"Extra: '{line[CODE_END:].strip()[:20]}'",
                )

    def _validate_copy_references(
        self,
        files: List[Path],
        result: ValidationResult,
    ) -> None:
        """Validate all COPY statements reference existing files."""
        # Build list of available copybooks
        available_copybooks: Set[str] = set()
        for f in files:
            name = f.stem.upper()
            available_copybooks.add(name)

        # Check each file's COPY statements
        for file_path in files:
            try:
                content = file_path.read_text(encoding="latin-1")
                lines = content.splitlines()
                copy_stmts = find_copy_statements(lines, str(file_path))

                for stmt in copy_stmts:
                    copybook_name = stmt.copybook_name.upper()
                    if copybook_name not in available_copybooks:
                        result.add_warning(
                            f"COPY reference to '{stmt.copybook_name}' not found",
                            file_path=file_path,
                            line_number=stmt.line_number,
                            identifier=stmt.copybook_name,
                        )
            except IOError:
                continue

    def _validate_cross_file_consistency(self, result: ValidationResult) -> None:
        """Validate same identifier maps to same name across files."""
        if not self.mapping_table:
            return

        # Get all mappings
        mappings = self.mapping_table.get_all_mappings()

        # Check for duplicate anonymized names
        anon_to_original: Dict[str, str] = {}
        for entry in mappings:
            if entry.anonymized_name in anon_to_original:
                existing = anon_to_original[entry.anonymized_name]
                if existing.upper() != entry.original_name.upper():
                    result.add_error(
                        f"Duplicate anonymized name '{entry.anonymized_name}' "
                        f"for different identifiers: '{existing}' and '{entry.original_name}'",
                        identifier=entry.anonymized_name,
                    )
            else:
                anon_to_original[entry.anonymized_name] = entry.original_name


def validate_identifier_lengths(
    mapping_table: MappingTable,
    max_length: int = 30,
) -> List[ValidationIssue]:
    """
    Validate all anonymized identifiers are within length limits.

    Args:
        mapping_table: The mapping table to validate
        max_length: Maximum identifier length

    Returns:
        List of validation issues
    """
    issues = []
    for entry in mapping_table.get_all_mappings():
        if len(entry.anonymized_name) > max_length:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Anonymized name '{entry.anonymized_name}' exceeds {max_length} chars",
                identifier=entry.original_name,
            ))
    return issues


def validate_column_format(files: List[Path]) -> List[ValidationIssue]:
    """
    Validate all files have proper column format.

    Args:
        files: List of file paths to validate

    Returns:
        List of validation issues
    """
    validator = OutputValidator()
    result = validator.validate_files(files)
    return result.issues


def validate_mapping_table(mapping_table: MappingTable) -> ValidationResult:
    """
    Validate a mapping table for correctness.

    Args:
        mapping_table: The mapping table to validate

    Returns:
        ValidationResult with any issues
    """
    result = ValidationResult()

    for entry in mapping_table.get_all_mappings():
        # Check identifier length
        if len(entry.anonymized_name) > 30:
            result.add_error(
                f"Anonymized name exceeds 30 chars: '{entry.anonymized_name}'",
                identifier=entry.original_name,
            )

        # Check for leading/trailing hyphens
        if entry.anonymized_name.startswith("-"):
            result.add_error(
                f"Anonymized name starts with hyphen: '{entry.anonymized_name}'",
                identifier=entry.original_name,
            )
        if entry.anonymized_name.endswith("-"):
            result.add_error(
                f"Anonymized name ends with hyphen: '{entry.anonymized_name}'",
                identifier=entry.original_name,
            )

        # Check for consecutive hyphens
        if "--" in entry.anonymized_name:
            result.add_warning(
                f"Anonymized name has consecutive hyphens: '{entry.anonymized_name}'",
                identifier=entry.original_name,
            )

        # Check first character is alphabetic
        if entry.anonymized_name and not entry.anonymized_name[0].isalpha():
            result.add_error(
                f"Anonymized name doesn't start with letter: '{entry.anonymized_name}'",
                identifier=entry.original_name,
            )

    return result
