"""
Report Generator - Generates mapping reports and statistics.

This module handles:
- Generating JSON mapping reports
- Including statistics (files, lines, identifiers by type)
- Including external names list
- Including transformation details per file
- Optionally generating HTML reports
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from cobol_anonymizer.core.anonymizer import FileTransformResult
from cobol_anonymizer.core.classifier import IdentifierType
from cobol_anonymizer.core.mapper import MappingTable


@dataclass
class FileStatistics:
    """Statistics for a single file."""

    filename: str
    anonymized_filename: str
    total_lines: int
    transformed_lines: int
    identifiers_found: int
    comments_transformed: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "filename": self.filename,
            "anonymized_filename": self.anonymized_filename,
            "total_lines": self.total_lines,
            "transformed_lines": self.transformed_lines,
            "identifiers_found": self.identifiers_found,
            "comments_transformed": self.comments_transformed,
        }


@dataclass
class AnonymizationReport:
    """Complete anonymization report."""

    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tool_version: str = "1.0.0"
    source_directory: str = ""
    output_directory: str = ""
    file_statistics: list[FileStatistics] = field(default_factory=list)
    mapping_table: Optional[MappingTable] = None
    total_files: int = 0
    total_lines: int = 0
    total_identifiers: int = 0
    external_names: list[str] = field(default_factory=list)
    processing_time_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        # Get statistics by identifier type
        type_stats = {}
        if self.mapping_table:
            for id_type in IdentifierType:
                mappings = self.mapping_table.get_mappings_by_type(id_type)
                if mappings:
                    type_stats[id_type.name] = len(mappings)

        # Build mappings list
        mappings_list = []
        if self.mapping_table:
            for entry in self.mapping_table.get_all_mappings():
                mappings_list.append(entry.to_dict())

        return {
            "metadata": {
                "generated_at": self.generated_at,
                "tool_version": self.tool_version,
                "source_directory": self.source_directory,
                "output_directory": self.output_directory,
                "processing_time_seconds": self.processing_time_seconds,
            },
            "summary": {
                "total_files": self.total_files,
                "total_lines": self.total_lines,
                "total_identifiers": self.total_identifiers,
                "identifiers_by_type": type_stats,
                "external_names_count": len(self.external_names),
            },
            "external_names": self.external_names,
            "file_statistics": [fs.to_dict() for fs in self.file_statistics],
            "mappings": mappings_list,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save_json(self, path: Path) -> None:
        """Save report as JSON file."""
        path.write_text(self.to_json())

    def save_text(self, path: Path) -> None:
        """Save report as text file."""
        path.write_text(self.to_text())

    def to_text(self) -> str:
        """Convert report to readable text format."""
        lines = [
            "=" * 70,
            "COBOL ANONYMIZATION REPORT",
            "=" * 70,
            "",
            f"Generated: {self.generated_at}",
            f"Tool Version: {self.tool_version}",
            f"Source: {self.source_directory}",
            f"Output: {self.output_directory}",
            f"Processing Time: {self.processing_time_seconds:.2f} seconds",
            "",
            "-" * 70,
            "SUMMARY",
            "-" * 70,
            f"Total Files: {self.total_files}",
            f"Total Lines: {self.total_lines}",
            f"Total Identifiers: {self.total_identifiers}",
            f"External Names: {len(self.external_names)}",
            "",
        ]

        # Identifiers by type
        if self.mapping_table:
            lines.append("-" * 70)
            lines.append("IDENTIFIERS BY TYPE")
            lines.append("-" * 70)
            for id_type in IdentifierType:
                mappings = self.mapping_table.get_mappings_by_type(id_type)
                if mappings:
                    lines.append(f"  {id_type.name}: {len(mappings)}")
            lines.append("")

        # External names
        if self.external_names:
            lines.append("-" * 70)
            lines.append("EXTERNAL NAMES (Preserved)")
            lines.append("-" * 70)
            for name in self.external_names:
                lines.append(f"  {name}")
            lines.append("")

        # File statistics
        lines.append("-" * 70)
        lines.append("FILE STATISTICS")
        lines.append("-" * 70)
        for fs in self.file_statistics:
            lines.append(f"  {fs.filename} -> {fs.anonymized_filename}")
            lines.append(f"    Lines: {fs.total_lines}, Transformed: {fs.transformed_lines}")
            lines.append(f"    Identifiers: {fs.identifiers_found}")
            lines.append("")

        # Mapping table (abbreviated)
        if self.mapping_table:
            lines.append("-" * 70)
            lines.append("MAPPING TABLE (sample)")
            lines.append("-" * 70)
            lines.append(f"{'ORIGINAL':<30} {'ANONYMIZED':<30} TYPE")
            lines.append("-" * 70)
            for i, entry in enumerate(self.mapping_table.get_all_mappings()):
                if i >= 50:  # Limit to 50 entries in text report
                    lines.append(f"  ... and {self.total_identifiers - 50} more")
                    break
                ext_marker = " [EXT]" if entry.is_external else ""
                lines.append(
                    f"{entry.original_name:<30} {entry.anonymized_name:<30} "
                    f"{entry.id_type.name}{ext_marker}"
                )
            lines.append("")

        lines.append("=" * 70)
        lines.append("END OF REPORT")
        lines.append("=" * 70)

        return "\n".join(lines)


class ReportGenerator:
    """
    Generates anonymization reports.

    Usage:
        generator = ReportGenerator(mapping_table)
        report = generator.generate_report(results)
    """

    def __init__(
        self,
        mapping_table: Optional[MappingTable] = None,
        source_directory: Optional[Path] = None,
        output_directory: Optional[Path] = None,
    ):
        """
        Initialize the report generator.

        Args:
            mapping_table: The mapping table with all mappings
            source_directory: Source directory path
            output_directory: Output directory path
        """
        self.mapping_table = mapping_table
        self.source_directory = source_directory
        self.output_directory = output_directory

    def generate_report(
        self,
        file_results: list[FileTransformResult],
        processing_time: float = 0.0,
    ) -> AnonymizationReport:
        """
        Generate a report from transformation results.

        Args:
            file_results: List of file transformation results
            processing_time: Total processing time in seconds

        Returns:
            AnonymizationReport with all statistics
        """
        report = AnonymizationReport(
            source_directory=str(self.source_directory or ""),
            output_directory=str(self.output_directory or ""),
            mapping_table=self.mapping_table,
            processing_time_seconds=processing_time,
        )

        # Calculate totals
        for result in file_results:
            report.total_files += 1
            report.total_lines += result.total_lines

            # Create file statistics
            filename = getattr(result, "filename", None) or str(
                getattr(result, "original_path", "unknown")
            )
            fs = FileStatistics(
                filename=filename,
                anonymized_filename=filename,  # Will be updated if anonymized name available
                total_lines=result.total_lines,
                transformed_lines=result.transformed_lines,
                identifiers_found=len(
                    {orig for change in result.changes for orig, anon in change.changes_made}
                ),
            )
            report.file_statistics.append(fs)

        # Get identifier count from mapping table
        if self.mapping_table:
            report.total_identifiers = len(self.mapping_table.get_all_mappings())
            report.external_names = list(self.mapping_table.get_external_names())

        return report

    def create_mapping_json(self) -> str:
        """
        Create a JSON mapping file.

        Returns:
            JSON string with all mappings
        """
        if not self.mapping_table:
            return "{}"
        return json.dumps(self.mapping_table.to_dict(), indent=2)


def create_mapping_report(mapping_table: MappingTable) -> str:
    """
    Create a text mapping report.

    This is a simplified version for quick reference.

    Args:
        mapping_table: The mapping table

    Returns:
        Formatted text report
    """
    lines = [
        "COBOL IDENTIFIER MAPPING REPORT",
        "=" * 60,
        "",
        f"{'ORIGINAL':<30} {'ANONYMIZED':<25} TYPE",
        "-" * 60,
    ]

    for entry in mapping_table.get_all_mappings():
        ext_marker = " [EXTERNAL]" if entry.is_external else ""
        lines.append(
            f"{entry.original_name:<30} {entry.anonymized_name:<25} "
            f"{entry.id_type.name}{ext_marker}"
        )

    lines.append("-" * 60)
    stats = mapping_table.get_statistics()
    lines.append(f"Total: {stats['total_mappings']} mappings")
    lines.append(f"External: {stats['external_count']} names")

    return "\n".join(lines)


def create_summary_report(
    file_results: list[FileTransformResult],
    mapping_table: MappingTable,
) -> str:
    """
    Create a summary report.

    Args:
        file_results: List of transformation results
        mapping_table: The mapping table

    Returns:
        Summary report text
    """
    total_lines = sum(r.total_lines for r in file_results)
    transformed_lines = sum(r.transformed_lines for r in file_results)
    stats = mapping_table.get_statistics()

    lines = [
        "ANONYMIZATION SUMMARY",
        "=" * 40,
        f"Files processed: {len(file_results)}",
        f"Total lines: {total_lines}",
        f"Lines transformed: {transformed_lines}",
        f"Unique identifiers: {stats['total_mappings']}",
        f"External names: {stats['external_count']}",
        "=" * 40,
    ]

    return "\n".join(lines)
