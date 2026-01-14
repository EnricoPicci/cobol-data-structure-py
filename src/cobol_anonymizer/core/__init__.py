"""
Core modules for the COBOL Anonymizer.

This package contains the core processing logic:
- tokenizer: COBOL-aware tokenization
- classifier: Identifier classification
- anonymizer: Main anonymization logic
- mapper: Global identifier mapping
- utils: Utility functions
"""

from cobol_anonymizer.core.utils import (
    identifiers_equal,
    is_filler,
    is_level_number,
    normalize_identifier,
    validate_identifier,
)

__all__ = [
    "validate_identifier",
    "normalize_identifier",
    "identifiers_equal",
    "is_level_number",
    "is_filler",
]
