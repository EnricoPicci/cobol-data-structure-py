"""COBOL Data Structure Python Package.

A Python library for parsing COBOL data structures and extracting values
from raw data.

Example usage:
    >>> from cobol_data_structure import parse_cobol_string
    >>> cobol_source = '''
    ... 01 CUSTOMER-RECORD.
    ...    05 CUST-NAME    PIC X(20).
    ...    05 CUST-ID      PIC 9(5).
    ... '''
    >>> structure = parse_cobol_string(cobol_source)
    >>> record = structure.parse_data("John Smith          12345")
    >>> print(record.get_field("CUST-NAME"))
    John Smith
"""

__version__ = "0.1.0"

from .models import (
    CobolDataStructure,
    CobolField,
    ParsedRecord,
    Warning,
)
from .parser import (
    parse_cobol_file,
    parse_cobol_source,
    parse_cobol_string,
)

__all__ = [
    # Version
    "__version__",
    # Core classes
    "CobolDataStructure",
    "CobolField",
    "ParsedRecord",
    "Warning",
    # Parser functions
    "parse_cobol_file",
    "parse_cobol_source",
    "parse_cobol_string",
]
