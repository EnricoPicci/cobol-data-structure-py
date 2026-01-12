"""COBOL Data Structure Python Package.

A Python library for parsing COBOL DATA DIVISION structures and
extracting data from raw bytes/strings.

Basic Usage:
    >>> from cobol_data_structure import parse_string, DataHolder
    >>>
    >>> record = parse_string('''
    ... 01 CUSTOMER-RECORD.
    ...     03 NAME PIC X(20).
    ...     03 AGE PIC 9(3).
    ... ''')
    >>>
    >>> holder = DataHolder(record)
    >>> holder.fill_from_string("John Doe            025")
    >>> print(holder.name.strip())
    John Doe
    >>> print(holder.age)
    25
"""

__version__ = "0.1.0"

from .data_holder import DataHolder, NestedDataHolder
from .models import (
    CobolDataError,
    CobolError,
    CobolField,
    CobolFieldError,
    CobolParseError,
    CobolRecord,
    FieldType,
    PicClause,
)
from .parser import CobolParser, parse_copybook, parse_string
from .warnings_log import WarningsLog

__all__ = [
    # Version
    "__version__",
    # Main API
    "parse_copybook",
    "parse_string",
    "DataHolder",
    # Parser
    "CobolParser",
    # Models
    "CobolRecord",
    "CobolField",
    "PicClause",
    "FieldType",
    # Helpers
    "NestedDataHolder",
    "WarningsLog",
    # Exceptions
    "CobolError",
    "CobolParseError",
    "CobolDataError",
    "CobolFieldError",
]
