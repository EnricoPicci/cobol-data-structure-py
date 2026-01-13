"""
COBOL Anonymizer - Anonymize COBOL source code while preserving logic.

This package provides tools to automatically anonymize COBOL source code,
replacing identifiable elements (variable names, program names, comments, etc.)
with generic equivalents while maintaining exact logical equivalence.

Basic Usage:
    from cobol_anonymizer import anonymize_directory, Config

    # Simple usage
    result = anonymize_directory(
        input_dir=Path("original/"),
        output_dir=Path("anonymized/"),
    )

    # With configuration
    config = Config(
        input_dir=Path("original/"),
        output_dir=Path("anonymized/"),
        preserve_external=True,
        anonymize_comments=True,
    )
    pipeline = AnonymizationPipeline(config)
    result = pipeline.run()

Command-Line Usage:
    cobol-anonymize --input original/ --output anonymized/
    cobol-anonymize --input original/ --output anonymized/ --verbose
    cobol-anonymize --input original/ --output anonymized/ --validate-only
"""

__version__ = "1.0.0"
__author__ = "COBOL Anonymizer Team"

from cobol_anonymizer.exceptions import (
    AnonymizerError,
    ParseError,
    MappingError,
    ValidationError,
    ColumnOverflowError,
    IdentifierLengthError,
    ConfigError,
    CopyNotFoundError,
    CircularDependencyError,
)

from cobol_anonymizer.config import Config, create_default_config
from cobol_anonymizer.main import (
    AnonymizationPipeline,
    AnonymizationResult,
    anonymize_directory,
    validate_directory,
)
from cobol_anonymizer.core.anonymizer import Anonymizer
from cobol_anonymizer.core.mapper import MappingTable
from cobol_anonymizer.core.classifier import IdentifierType

__all__ = [
    # Version
    "__version__",
    # Main API
    "anonymize_directory",
    "validate_directory",
    "AnonymizationPipeline",
    "AnonymizationResult",
    "Anonymizer",
    # Configuration
    "Config",
    "create_default_config",
    # Data Types
    "MappingTable",
    "IdentifierType",
    # Exceptions
    "AnonymizerError",
    "ParseError",
    "MappingError",
    "ValidationError",
    "ColumnOverflowError",
    "IdentifierLengthError",
    "ConfigError",
    "CopyNotFoundError",
    "CircularDependencyError",
]
