"""
Configuration - Handles anonymization configuration.

This module handles:
- Configuration dataclass with all options
- JSON configuration file support
- Command-line overrides
- Configuration validation
"""

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from cobol_anonymizer.generators.naming_schemes import NamingScheme


@dataclass
class Config:
    """
    Configuration for COBOL anonymization.

    Attributes:
        input_dir: Directory containing source COBOL files
        output_dir: Directory for anonymized output
        extensions: File extensions to process
        encoding: File encoding (default: latin-1)
        copybook_paths: Additional paths to search for copybooks
        mapping_file: Path to save/load mapping table
        anonymize_programs: Anonymize program names
        anonymize_copybooks: Anonymize copybook names
        anonymize_data: Anonymize data names
        anonymize_paragraphs: Anonymize paragraph names
        anonymize_sections: Anonymize section names
        anonymize_comments: Anonymize comment content
        anonymize_literals: Anonymize string literal contents (default: True, use --protect-literals to disable)
        strip_comments: Remove comment content entirely
        preserve_external: Keep EXTERNAL item names unchanged (default: False - anonymize them)
        clean_sequence_area: Clean columns 1-6 (sequence numbers/identification tags) by replacing with spaces (default: True)
        validate_columns: Validate column 72 limit
        validate_identifiers: Validate identifier length
        dry_run: Don't write output files
        validate_only: Only validate, don't transform
        verbose: Enable verbose output
        quiet: Suppress normal output
        seed: Random seed for deterministic output
        naming_scheme: Naming scheme for anonymized identifiers
        log_level: Logging level
        overwrite: Overwrite existing output files
    """

    input_dir: Path = field(default_factory=lambda: Path("."))
    output_dir: Path = field(default_factory=lambda: Path("anonymized"))
    extensions: list[str] = field(default_factory=lambda: [".cob", ".cbl", ".cpy"])
    encoding: str = "latin-1"
    copybook_paths: list[Path] = field(default_factory=list)
    mapping_file: Optional[Path] = None
    load_mappings: Optional[Path] = None

    # Anonymization options
    anonymize_programs: bool = True
    anonymize_copybooks: bool = True
    anonymize_data: bool = True
    anonymize_paragraphs: bool = True
    anonymize_sections: bool = True
    anonymize_comments: bool = True
    anonymize_literals: bool = True
    strip_comments: bool = False
    preserve_external: bool = False
    clean_sequence_area: bool = True  # Clean columns 1-6 (sequence numbers/tags) by default

    # Validation options
    validate_columns: bool = True
    validate_identifiers: bool = True

    # Run modes
    dry_run: bool = False
    validate_only: bool = False

    # Output options
    verbose: bool = False
    quiet: bool = False
    seed: Optional[int] = None
    naming_scheme: NamingScheme = NamingScheme.CORPORATE
    log_level: str = "INFO"
    overwrite: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        data = {}
        for key, value in asdict(self).items():
            if isinstance(value, Path):
                data[key] = str(value)
            elif isinstance(value, list) and value and isinstance(value[0], Path):
                data[key] = [str(p) for p in value]
            elif isinstance(value, Enum):
                data[key] = value.value
            else:
                data[key] = value
        return data

    def save_to_file(self, path: Path) -> None:
        """Save configuration to JSON file."""
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load_from_file(cls, path: Path) -> "Config":
        """Load configuration from JSON file."""
        data = json.loads(path.read_text())
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        # Convert path strings to Path objects
        if "input_dir" in data:
            data["input_dir"] = Path(data["input_dir"])
        if "output_dir" in data:
            data["output_dir"] = Path(data["output_dir"])
        if "mapping_file" in data and data["mapping_file"]:
            data["mapping_file"] = Path(data["mapping_file"])
        if "load_mappings" in data and data["load_mappings"]:
            data["load_mappings"] = Path(data["load_mappings"])
        if "copybook_paths" in data:
            data["copybook_paths"] = [Path(p) for p in data["copybook_paths"]]

        # Convert naming_scheme string to enum
        if "naming_scheme" in data and isinstance(data["naming_scheme"], str):
            try:
                data["naming_scheme"] = NamingScheme(data["naming_scheme"])
            except ValueError:
                # Invalid scheme, fall back to default
                data["naming_scheme"] = NamingScheme.NUMERIC

        # Filter only known fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}

        return cls(**filtered_data)

    def validate(self) -> list[str]:
        """
        Validate configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.input_dir.exists():
            errors.append(f"Input directory does not exist: {self.input_dir}")

        if not self.validate_only and not self.dry_run:
            if self.output_dir.exists() and not self.output_dir.is_dir():
                errors.append(f"Output path is not a directory: {self.output_dir}")

        if self.mapping_file and self.mapping_file.exists():
            if not self.mapping_file.is_file():
                errors.append(f"Mapping file is not a file: {self.mapping_file}")

        for cp in self.copybook_paths:
            if not cp.exists():
                errors.append(f"Copybook path does not exist: {cp}")

        if self.strip_comments and self.anonymize_comments:
            # strip_comments takes precedence
            pass  # This is fine, just a note

        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"Invalid log level: {self.log_level}")

        return errors

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0


def create_default_config() -> Config:
    """Create a configuration with default values."""
    return Config()


def merge_configs(base: Config, override: Config) -> Config:
    """
    Merge two configurations, with override taking precedence.

    Args:
        base: Base configuration
        override: Override configuration

    Returns:
        Merged configuration
    """
    base_dict = base.to_dict()
    override_dict = override.to_dict()

    # Only override non-default values from override
    merged = {}
    default = create_default_config().to_dict()

    for key in base_dict:
        # Use override value if it differs from default, otherwise use base
        if override_dict.get(key) != default.get(key):
            merged[key] = override_dict[key]
        else:
            merged[key] = base_dict[key]

    return Config.from_dict(merged)
