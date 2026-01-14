"""
COBOL Identifier Mapping Table - Manages original to anonymized name mappings.

This module provides a global mapping table that:
- Maps original identifiers to anonymized names
- Ensures cross-file consistency
- Tracks EXTERNAL identifiers (which should not be anonymized)
- Supports case-insensitive lookup (COBOL standard)
- Provides persistence via JSON export/import
"""

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from cobol_anonymizer.core.classifier import IdentifierType
from cobol_anonymizer.generators.name_generator import (
    NameGenerator,
    NameGeneratorConfig,
)
from cobol_anonymizer.generators.naming_schemes import NamingScheme


@dataclass
class MappingEntry:
    """
    A single mapping from original to anonymized name.

    Attributes:
        original_name: The original identifier name
        anonymized_name: The generated anonymized name
        id_type: The type of identifier
        is_external: True if this is an EXTERNAL item (should not be changed)
        first_seen_file: File where identifier was first seen
        first_seen_line: Line number where first seen
        occurrence_count: Number of times this identifier appears
    """

    original_name: str
    anonymized_name: str
    id_type: IdentifierType
    is_external: bool = False
    first_seen_file: Optional[str] = None
    first_seen_line: Optional[int] = None
    occurrence_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "original_name": self.original_name,
            "anonymized_name": self.anonymized_name,
            "id_type": self.id_type.name,
            "is_external": self.is_external,
            "first_seen_file": self.first_seen_file,
            "first_seen_line": self.first_seen_line,
            "occurrence_count": self.occurrence_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MappingEntry":
        """Create from dictionary."""
        return cls(
            original_name=data["original_name"],
            anonymized_name=data["anonymized_name"],
            id_type=IdentifierType[data["id_type"]],
            is_external=data.get("is_external", False),
            first_seen_file=data.get("first_seen_file"),
            first_seen_line=data.get("first_seen_line"),
            occurrence_count=data.get("occurrence_count", 1),
        )


@dataclass
class MappingTable:
    """
    Global mapping table for identifier anonymization.

    Provides case-insensitive lookup and ensures consistent
    mapping across all files in a project.

    Usage:
        table = MappingTable()
        anon_name = table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        # With a different naming scheme:
        table = MappingTable(_naming_scheme=NamingScheme.ANIMALS)
        anon_name = table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        # -> "FLUFFY-LLAMA-1"
    """

    _mappings: dict[str, MappingEntry] = field(default_factory=dict)
    _external_names: set[str] = field(default_factory=set)
    _generator: NameGenerator = field(default_factory=NameGenerator)
    _preserve_length: bool = True
    _naming_scheme: NamingScheme = NamingScheme.CORPORATE

    def __post_init__(self):
        # Configure the generator with naming scheme
        config = NameGeneratorConfig(
            preserve_length=self._preserve_length,
            naming_scheme=self._naming_scheme,
        )
        self._generator = NameGenerator(config=config)

    def get_or_create(
        self,
        original_name: str,
        id_type: IdentifierType,
        is_external: bool = False,
        file_name: Optional[str] = None,
        line_number: Optional[int] = None,
    ) -> str:
        """
        Get existing mapping or create a new one.

        Args:
            original_name: The original identifier name
            id_type: The type of identifier
            is_external: True if this is an EXTERNAL item
            file_name: Source file name for tracking
            line_number: Line number for tracking

        Returns:
            The anonymized name (or original if EXTERNAL)
        """
        # Normalize to uppercase for case-insensitive lookup
        key = original_name.upper()

        # Check if this is an EXTERNAL item
        if is_external or id_type == IdentifierType.EXTERNAL_NAME:
            self._external_names.add(key)
            # EXTERNAL items keep their original names
            if key not in self._mappings:
                self._mappings[key] = MappingEntry(
                    original_name=original_name,
                    anonymized_name=original_name,  # Keep original
                    id_type=id_type,
                    is_external=True,
                    first_seen_file=file_name,
                    first_seen_line=line_number,
                )
            return original_name

        # Check for existing mapping
        if key in self._mappings:
            entry = self._mappings[key]
            entry.occurrence_count += 1
            return entry.anonymized_name

        # Check if it's a known EXTERNAL name
        if key in self._external_names:
            return original_name

        # Generate new anonymized name
        anonymized = self._generator.generate(original_name, id_type)

        # Create mapping entry
        self._mappings[key] = MappingEntry(
            original_name=original_name,
            anonymized_name=anonymized,
            id_type=id_type,
            is_external=False,
            first_seen_file=file_name,
            first_seen_line=line_number,
        )

        return anonymized

    def get_mapping(self, original_name: str) -> Optional[MappingEntry]:
        """
        Get the mapping entry for an identifier.

        Args:
            original_name: The original identifier name

        Returns:
            The MappingEntry, or None if not mapped
        """
        return self._mappings.get(original_name.upper())

    def get_anonymized_name(self, original_name: str) -> Optional[str]:
        """
        Get the anonymized name for an identifier.

        Args:
            original_name: The original identifier name

        Returns:
            The anonymized name, or None if not mapped
        """
        entry = self.get_mapping(original_name)
        return entry.anonymized_name if entry else None

    def get_original_name(self, anonymized_name: str) -> Optional[str]:
        """
        Reverse lookup: get original name from anonymized.

        Args:
            anonymized_name: The anonymized name

        Returns:
            The original name, or None if not found
        """
        for entry in self._mappings.values():
            if entry.anonymized_name.upper() == anonymized_name.upper():
                return entry.original_name
        return None

    def is_external(self, name: str) -> bool:
        """
        Check if a name is marked as EXTERNAL.

        Args:
            name: The identifier name

        Returns:
            True if this is an EXTERNAL item
        """
        return name.upper() in self._external_names

    def mark_external(self, name: str) -> None:
        """
        Mark an identifier as EXTERNAL.

        Args:
            name: The identifier name
        """
        self._external_names.add(name.upper())

    def get_all_mappings(self) -> list[MappingEntry]:
        """Get all mapping entries."""
        return list(self._mappings.values())

    def get_mappings_by_type(self, id_type: IdentifierType) -> list[MappingEntry]:
        """Get mappings of a specific type."""
        return [e for e in self._mappings.values() if e.id_type == id_type]

    def get_external_names(self) -> set[str]:
        """Get all EXTERNAL identifier names."""
        return set(self._external_names)

    def get_statistics(self) -> dict[str, Any]:
        """Get mapping statistics."""
        stats = {
            "total_mappings": len(self._mappings),
            "external_count": len(self._external_names),
            "by_type": {},
        }
        for id_type in IdentifierType:
            count = len(self.get_mappings_by_type(id_type))
            if count > 0:
                stats["by_type"][id_type.name] = count
        return stats

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "generated_at": datetime.now().isoformat(),
            "naming_scheme": self._naming_scheme.value,
            "mappings": [e.to_dict() for e in self._mappings.values()],
            "external_names": list(self._external_names),
            "generator_state": {k.name: v for k, v in self._generator.get_counter_state().items()},
        }

    def save_to_file(self, path: Path) -> None:
        """
        Save mapping table to JSON file.

        Args:
            path: Path to save the JSON file
        """
        # Ensure the parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def save_to_csv(self, path: Path) -> None:
        """
        Save mapping table to CSV file.

        The CSV contains one row per mapping entry with columns:
        original_name, anonymized_name, id_type, is_external,
        first_seen_file, first_seen_line, occurrence_count,
        naming_scheme, generated_at

        Args:
            path: Path to save the CSV file
        """
        # Ensure the parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().isoformat()
        scheme_name = self._naming_scheme.value

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(
                [
                    "original_name",
                    "anonymized_name",
                    "id_type",
                    "is_external",
                    "first_seen_file",
                    "first_seen_line",
                    "occurrence_count",
                    "naming_scheme",
                    "generated_at",
                ]
            )

            # Write mapping entries
            for entry in self._mappings.values():
                writer.writerow(
                    [
                        entry.original_name,
                        entry.anonymized_name,
                        entry.id_type.name,
                        str(entry.is_external).lower(),
                        entry.first_seen_file or "",
                        entry.first_seen_line if entry.first_seen_line is not None else "",
                        entry.occurrence_count,
                        scheme_name,
                        timestamp,
                    ]
                )

            # Write external names that weren't already in mappings
            for ext_name in self._external_names:
                if ext_name not in self._mappings:
                    writer.writerow(
                        [
                            ext_name,
                            ext_name,  # External names keep original
                            "EXTERNAL_NAME",
                            "true",
                            "",
                            "",
                            0,
                            scheme_name,
                            timestamp,
                        ]
                    )

    @classmethod
    def load_from_file(cls, path: Path) -> "MappingTable":
        """
        Load mapping table from JSON file.

        Args:
            path: Path to the JSON file

        Returns:
            Loaded MappingTable instance
        """
        with open(path) as f:
            data = json.load(f)

        # Restore naming scheme (default to NUMERIC for backward compatibility)
        scheme_value = data.get("naming_scheme", "numeric")
        try:
            naming_scheme = NamingScheme(scheme_value)
        except ValueError:
            naming_scheme = NamingScheme.NUMERIC

        table = cls(_naming_scheme=naming_scheme)

        # Load mappings
        for entry_data in data.get("mappings", []):
            entry = MappingEntry.from_dict(entry_data)
            table._mappings[entry.original_name.upper()] = entry

        # Load external names
        for name in data.get("external_names", []):
            table._external_names.add(name.upper())

        # Restore generator state
        generator_state = data.get("generator_state", {})
        state = {IdentifierType[k]: v for k, v in generator_state.items()}
        table._generator.set_counter_state(state)

        return table

    def reset(self) -> None:
        """Reset the mapping table."""
        self._mappings.clear()
        self._external_names.clear()
        self._generator.reset()


def create_mapping_report(table: MappingTable) -> str:
    """
    Create a human-readable mapping report.

    Args:
        table: The mapping table

    Returns:
        Formatted report string
    """
    lines = [
        "=" * 70,
        "COBOL Anonymization Mapping Report",
        "=" * 70,
        "",
    ]

    # Statistics
    stats = table.get_statistics()
    lines.extend(
        [
            "Statistics:",
            f"  Total mappings: {stats['total_mappings']}",
            f"  External items: {stats['external_count']}",
            "",
            "Mappings by type:",
        ]
    )
    for type_name, count in stats["by_type"].items():
        lines.append(f"  {type_name}: {count}")

    lines.extend(["", "=" * 70, ""])

    # Detailed mappings by type
    for id_type in IdentifierType:
        mappings = table.get_mappings_by_type(id_type)
        if not mappings:
            continue

        lines.extend(
            [
                f"{id_type.name}:",
                "-" * 40,
            ]
        )

        for entry in sorted(mappings, key=lambda e: e.original_name):
            ext_marker = " [EXTERNAL]" if entry.is_external else ""
            lines.append(f"  {entry.original_name:30} -> {entry.anonymized_name}{ext_marker}")

        lines.append("")

    return "\n".join(lines)
