"""
COBOL Reserved Words - Comprehensive list of COBOL keywords.

This module provides a complete list of COBOL reserved words including:
- COBOL-85 standard keywords
- COBOL-2002 additions
- Common IBM extensions
- Clause keywords (REDEFINES, VALUE, OCCURS, etc.)

Reserved words must never be used as user-defined identifiers
and must never be anonymized.
"""

from typing import Set


# COBOL reserved words - comprehensive list from COBOL-85, COBOL-2002, and IBM extensions
# This set includes all keywords that cannot be used as user-defined names
RESERVED_WORDS: Set[str] = {
    # A
    "ACCEPT", "ACCESS", "ADD", "ADDRESS", "ADVANCING", "AFTER", "ALL",
    "ALLOCATE", "ALPHABET", "ALPHABETIC", "ALPHABETIC-LOWER", "ALPHABETIC-UPPER",
    "ALPHANUMERIC", "ALPHANUMERIC-EDITED", "ALSO", "ALTER", "ALTERNATE",
    "AND", "ANY", "APPLY", "ARE", "AREA", "AREAS", "ASCENDING", "ASSIGN",
    "AT", "AUTHOR",

    # B
    "BEFORE", "BEGINNING", "BINARY", "BINARY-CHAR", "BINARY-DOUBLE",
    "BINARY-LONG", "BINARY-SHORT", "BLANK", "BLOCK", "BOOLEAN", "BOTTOM",
    "BY",

    # C
    "CALL", "CANCEL", "CBL", "CD", "CF", "CH", "CHARACTER", "CHARACTERS",
    "CLASS", "CLASS-ID", "CLOCK-UNITS", "CLOSE", "COBOL", "CODE",
    "CODE-SET", "COLLATING", "COLUMN", "COMMA", "COMMIT", "COMMON",
    "COMMUNICATION", "COMP", "COMP-1", "COMP-2", "COMP-3", "COMP-4",
    "COMP-5", "COMPUTATIONAL", "COMPUTATIONAL-1", "COMPUTATIONAL-2",
    "COMPUTATIONAL-3", "COMPUTATIONAL-4", "COMPUTATIONAL-5", "COMPUTE",
    "CONFIGURATION", "CONTAINS", "CONTENT", "CONTINUE", "CONTROL",
    "CONTROLS", "CONVERTING", "COPY", "CORR", "CORRESPONDING", "COUNT",
    "CRT", "CURRENCY", "CURSOR",

    # D
    "DATA", "DATE", "DATE-COMPILED", "DATE-WRITTEN", "DAY", "DAY-OF-WEEK",
    "DBCS", "DE", "DEBUG-CONTENTS", "DEBUG-ITEM", "DEBUG-LINE", "DEBUG-NAME",
    "DEBUG-SUB-1", "DEBUG-SUB-2", "DEBUG-SUB-3", "DEBUGGING", "DECIMAL-POINT",
    "DECLARATIVES", "DEFAULT", "DELETE", "DELIMITED", "DELIMITER",
    "DEPENDING", "DESCENDING", "DESTINATION", "DETAIL", "DISABLE", "DISPLAY",
    "DISPLAY-1", "DIVIDE", "DIVISION", "DOWN", "DUPLICATES", "DYNAMIC",

    # E
    "EBCDIC", "EGCS", "EGI", "EJECT", "ELSE", "EMI", "ENABLE", "END",
    "END-ADD", "END-CALL", "END-COMPUTE", "END-DELETE", "END-DISPLAY",
    "END-DIVIDE", "END-EVALUATE", "END-EXEC", "END-IF", "END-INVOKE",
    "END-MULTIPLY", "END-OF-PAGE", "END-PERFORM", "END-READ", "END-RECEIVE",
    "END-RETURN", "END-REWRITE", "END-SEARCH", "END-START", "END-STRING",
    "END-SUBTRACT", "END-UNSTRING", "END-WRITE", "ENDING", "ENTER",
    "ENTRY", "ENVIRONMENT", "EOP", "EQUAL", "ERROR", "ESI", "EVALUATE",
    "EVERY", "EXCEPTION", "EXEC", "EXECUTE", "EXIT", "EXTEND", "EXTERNAL",

    # F
    "FACTORY", "FALSE", "FD", "FILE", "FILE-CONTROL", "FILLER", "FINAL",
    "FIRST", "FLOAT-EXTENDED", "FLOAT-LONG", "FLOAT-SHORT", "FOOTING",
    "FOR", "FORMAT", "FREE", "FROM", "FULL", "FUNCTION", "FUNCTION-ID",

    # G
    "GENERATE", "GIVING", "GLOBAL", "GO", "GOBACK", "GREATER", "GROUP",
    "GROUP-USAGE",

    # H
    "HEADING", "HIGH-VALUE", "HIGH-VALUES",

    # I
    "ID", "IDENTIFICATION", "IF", "IN", "INDEX", "INDEXED", "INDICATE",
    "INHERITS", "INITIAL", "INITIALIZE", "INITIATE", "INPUT", "INPUT-OUTPUT",
    "INSPECT", "INSTALLATION", "INTERFACE", "INTERFACE-ID", "INTO",
    "INVALID", "INVOKE", "IS",

    # J
    "JUST", "JUSTIFIED",

    # K
    "KANJI", "KEY",

    # L
    "LABEL", "LAST", "LEADING", "LEFT", "LENGTH", "LESS", "LIMIT",
    "LIMITS", "LINAGE", "LINAGE-COUNTER", "LINE", "LINE-COUNTER", "LINES",
    "LINKAGE", "LOCAL-STORAGE", "LOCALE", "LOCK", "LOW-VALUE", "LOW-VALUES",

    # M
    "MEMORY", "MERGE", "MESSAGE", "METHOD", "METHOD-ID", "MINUS", "MODE",
    "MODULES", "MORE-LABELS", "MOVE", "MULTIPLE", "MULTIPLY",

    # N
    "NATIONAL", "NATIONAL-EDITED", "NATIVE", "NEGATIVE", "NESTED", "NEXT",
    "NO", "NOT", "NULL", "NULLS", "NUMBER", "NUMERIC", "NUMERIC-EDITED",

    # O
    "OBJECT", "OBJECT-COMPUTER", "OBJECT-REFERENCE", "OCCURS", "OF", "OFF",
    "OMITTED", "ON", "OPEN", "OPTIONAL", "OPTIONS", "OR", "ORDER",
    "ORGANIZATION", "OTHER", "OUTPUT", "OVERFLOW", "OVERRIDE",

    # P
    "PACKED-DECIMAL", "PADDING", "PAGE", "PAGE-COUNTER", "PARAGRAPH",
    "PASSWORD", "PERFORM", "PF", "PH", "PIC", "PICTURE", "PLUS", "POINTER",
    "POSITION", "POSITIVE", "PRESENT", "PRINTING", "PROCEDURE",
    "PROCEDURE-POINTER", "PROCEDURES", "PROCEED", "PROCESSING", "PROGRAM",
    "PROGRAM-ID", "PROGRAM-POINTER", "PROPERTY", "PROTOTYPE", "PURGE",

    # Q
    "QUEUE", "QUOTE", "QUOTES",

    # R
    "RAISE", "RAISING", "RANDOM", "RD", "READ", "READY", "RECEIVE",
    "RECORD", "RECORDING", "RECORDS", "RECURSIVE", "REDEFINES", "REEL",
    "REFERENCE", "REFERENCES", "RELATIVE", "RELEASE", "RELOAD", "REMAINDER",
    "REMOVAL", "RENAMES", "REPLACE", "REPLACING", "REPORT", "REPORTING",
    "REPORTS", "REPOSITORY", "RERUN", "RESERVE", "RESET", "RESUME",
    "RETRY", "RETURN", "RETURN-CODE", "RETURNING", "REVERSED", "REWIND",
    "REWRITE", "RF", "RH", "RIGHT", "ROLLBACK", "ROUNDED", "RUN",

    # S
    "SAME", "SCREEN", "SD", "SEARCH", "SECTION", "SECURE", "SECURITY",
    "SEGMENT", "SEGMENT-LIMIT", "SELECT", "SELF", "SEND", "SENTENCE",
    "SEPARATE", "SEQUENCE", "SEQUENTIAL", "SERVICE", "SET", "SHARING",
    "SHIFT-IN", "SHIFT-OUT", "SIGN", "SIZE", "SKIP1", "SKIP2", "SKIP3",
    "SORT", "SORT-CONTROL", "SORT-CORE-SIZE", "SORT-FILE-SIZE",
    "SORT-MERGE", "SORT-MESSAGE", "SORT-MODE-SIZE", "SORT-RETURN",
    "SOURCE", "SOURCE-COMPUTER", "SOURCES", "SPACE", "SPACES",
    "SPECIAL-NAMES", "SQL", "SQLCA", "SQLCODE", "SQLIMS", "SQLIMSCA",
    "SQLSTATE", "STANDARD", "STANDARD-1", "STANDARD-2", "START",
    "STATUS", "STOP", "STRING", "SUB-QUEUE-1", "SUB-QUEUE-2",
    "SUB-QUEUE-3", "SUBTRACT", "SUM", "SUPER", "SUPPRESS", "SYMBOLIC",
    "SYNC", "SYNCHRONIZED", "SYSTEM-DEFAULT",

    # T
    "TABLE", "TALLY", "TALLYING", "TAPE", "TERMINAL", "TERMINATE", "TEST",
    "TEXT", "THAN", "THEN", "THROUGH", "THRU", "TIME", "TIMES", "TITLE",
    "TO", "TOP", "TRACE", "TRAILING", "TRUE", "TYPE", "TYPEDEF",

    # U
    "UNBOUNDED", "UNIT", "UNIVERSAL", "UNLOCK", "UNSTRING", "UNTIL", "UP",
    "UPON", "USAGE", "USE", "USER-DEFAULT", "USING",

    # V
    "VALIDATE", "VALIDATING", "VALUE", "VALUES", "VARYING",

    # W
    "WHEN", "WHEN-COMPILED", "WITH", "WORDS", "WORKING-STORAGE", "WRITE",

    # X, Y, Z
    "XML", "XML-CODE", "XML-EVENT", "XML-INFORMATION", "XML-NAMESPACE",
    "XML-NAMESPACE-PREFIX", "XML-NNAMESPACE", "XML-NNAMESPACE-PREFIX",
    "XML-NTEXT", "XML-SCHEMA", "XML-TEXT",
    "ZERO", "ZEROES", "ZEROS",

    # Special IBM/MF extensions
    "GOBACK", "SERVICE", "EXEC", "SQL", "END-EXEC", "CICS",
    "DFHCOMMAREA", "DFHEIBLK", "DFHRESP", "EIBCALEN", "EIBRESP",

    # Figurative constants (handled as reserved)
    "SPACE", "SPACES", "ZERO", "ZEROS", "ZEROES", "HIGH-VALUE",
    "HIGH-VALUES", "LOW-VALUE", "LOW-VALUES", "QUOTE", "QUOTES",
    "NULL", "NULLS", "ALL",
}

# Create a frozenset for faster lookup (immutable)
_RESERVED_WORDS_UPPER: frozenset = frozenset(RESERVED_WORDS)


def is_reserved_word(word: str) -> bool:
    """
    Check if a word is a COBOL reserved word.

    The check is case-insensitive.

    Args:
        word: The word to check

    Returns:
        True if the word is a COBOL reserved word
    """
    return word.upper() in _RESERVED_WORDS_UPPER


def is_figurative_constant(word: str) -> bool:
    """
    Check if a word is a COBOL figurative constant.

    Figurative constants are special reserved words that represent
    predefined values.

    Args:
        word: The word to check

    Returns:
        True if the word is a figurative constant
    """
    figurative_constants = {
        "SPACE", "SPACES",
        "ZERO", "ZEROS", "ZEROES",
        "HIGH-VALUE", "HIGH-VALUES",
        "LOW-VALUE", "LOW-VALUES",
        "QUOTE", "QUOTES",
        "NULL", "NULLS",
    }
    return word.upper() in figurative_constants


def is_special_register(word: str) -> bool:
    """
    Check if a word is a COBOL special register.

    Special registers are system-defined data items.

    Args:
        word: The word to check

    Returns:
        True if the word is a special register
    """
    special_registers = {
        "ADDRESS",
        "DEBUG-ITEM",
        "LENGTH",
        "LINAGE-COUNTER",
        "LINE-COUNTER",
        "PAGE-COUNTER",
        "RETURN-CODE",
        "SHIFT-IN",
        "SHIFT-OUT",
        "SORT-CONTROL",
        "SORT-CORE-SIZE",
        "SORT-FILE-SIZE",
        "SORT-MESSAGE",
        "SORT-MODE-SIZE",
        "SORT-RETURN",
        "TALLY",
        "WHEN-COMPILED",
        "XML-CODE",
        "XML-EVENT",
        "XML-INFORMATION",
        "XML-NAMESPACE",
        "XML-NAMESPACE-PREFIX",
        "XML-NNAMESPACE",
        "XML-NNAMESPACE-PREFIX",
        "XML-NTEXT",
        "XML-TEXT",
    }
    return word.upper() in special_registers


def get_reserved_word_category(word: str) -> str:
    """
    Get the category of a reserved word.

    Args:
        word: The word to categorize

    Returns:
        Category string: "figurative_constant", "special_register",
        "reserved_word", or "user_defined"
    """
    upper_word = word.upper()

    if is_figurative_constant(word):
        return "figurative_constant"
    elif is_special_register(word):
        return "special_register"
    elif upper_word in _RESERVED_WORDS_UPPER:
        return "reserved_word"
    else:
        return "user_defined"


# Common prefixes that indicate system-generated or special identifiers
# These should generally not be anonymized
SYSTEM_PREFIXES = {
    "DFHCOMMAREA",
    "DFHEIBLK",
    "DFHRESP",
    "DFHVALUE",
    "EIBAID",
    "EIBCALEN",
    "EIBCPOSN",
    "EIBDATE",
    "EIBDS",
    "EIBFN",
    "EIBFREE",
    "EIBRCODE",
    "EIBREQID",
    "EIBRESP",
    "EIBRESP2",
    "EIBRSRCE",
    "EIBSYNC",
    "EIBTASKN",
    "EIBTIME",
    "EIBTRMID",
    "EIBTRNID",
    "SQLCA",
    "SQLCODE",
    "SQLERRMC",
    "SQLERRML",
    "SQLERRD",
    "SQLSTATE",
    "SQLWARN",
}


def is_system_identifier(word: str) -> bool:
    """
    Check if an identifier is a system-generated name.

    These include CICS and DB2 interface areas that should not be anonymized.

    Args:
        word: The identifier to check

    Returns:
        True if this is a system identifier
    """
    upper_word = word.upper()
    return upper_word in SYSTEM_PREFIXES or upper_word.startswith("EIB")
