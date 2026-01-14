"""
COBOL Tokenizer - Breaks COBOL source lines into tokens.

The tokenizer produces tokens that can be classified and potentially
anonymized. It preserves whitespace and positioning information
to allow exact reconstruction of the line.

Token types:
- IDENTIFIER: User-defined names (data items, paragraphs, etc.)
- RESERVED: COBOL reserved words
- LITERAL: String or numeric literals
- LEVEL_NUMBER: Level numbers (01, 05, 77, 88, etc.)
- OPERATOR: Arithmetic and comparison operators
- PUNCTUATION: Periods, commas, parentheses
- WHITESPACE: Spaces and tabs
- COMMENT: Comment text (for comment lines)
- PIC_CLAUSE: PIC/PICTURE clause
- UNKNOWN: Unrecognized token
"""

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Iterator

from cobol_anonymizer.cobol.reserved_words import (
    is_reserved_word,
    is_figurative_constant,
    is_system_identifier,
)
from cobol_anonymizer.cobol.pic_parser import (
    find_pic_clauses,
    find_usage_clauses,
    PICClause,
)
from cobol_anonymizer.core.utils import is_level_number


class TokenType(Enum):
    """Types of tokens in COBOL source."""
    IDENTIFIER = auto()      # User-defined names
    RESERVED = auto()        # COBOL reserved words
    LITERAL_STRING = auto()  # String literals 'text' or "text"
    LITERAL_NUMERIC = auto() # Numeric literals
    LEVEL_NUMBER = auto()    # Level numbers (01, 05, etc.)
    OPERATOR = auto()        # +, -, *, /, **, =, etc.
    PUNCTUATION = auto()     # . , ( ) :
    WHITESPACE = auto()      # Spaces and tabs
    COMMENT = auto()         # Comment text
    PIC_CLAUSE = auto()      # PIC X(30) etc.
    USAGE_CLAUSE = auto()    # COMP, COMP-3, etc.
    CONTINUATION = auto()    # Continuation marker
    COPY_NAME = auto()       # Copybook name in COPY statement
    UNKNOWN = auto()         # Unrecognized


@dataclass
class Token:
    """
    Represents a token from the COBOL source.

    Attributes:
        type: The TokenType classification
        value: The actual text of the token
        start_pos: Starting position in the line (0-indexed)
        end_pos: Ending position (exclusive)
        line_number: Line number in the source file
        original_value: Original value (for tracking changes)
        metadata: Additional token-specific data
    """
    type: TokenType
    value: str
    start_pos: int
    end_pos: int
    line_number: int = 1
    original_value: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.original_value is None:
            self.original_value = self.value

    @property
    def length(self) -> int:
        """Length of the token."""
        return self.end_pos - self.start_pos

    @property
    def was_modified(self) -> bool:
        """Check if the token was modified."""
        return self.value != self.original_value

    def upper_value(self) -> str:
        """Get uppercase version of the value."""
        return self.value.upper()


# Regex patterns for tokenization
# Order matters - more specific patterns should come first

# String literals (single or double quoted)
STRING_LITERAL_PATTERN = re.compile(r"'[^']*'|\"[^\"]*\"")

# Numeric literals (including signed and decimal)
NUMERIC_LITERAL_PATTERN = re.compile(r'[+-]?\d+(?:\.\d+)?')

# COBOL identifier pattern (allows hyphens, no leading/trailing hyphens)
# Must start with letter, can contain letters, digits, hyphens
IDENTIFIER_PATTERN = re.compile(r'[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9]|[A-Za-z]')

# Whitespace
WHITESPACE_PATTERN = re.compile(r'[ \t]+')

# Operators
OPERATOR_PATTERN = re.compile(r'\*\*|[+\-*/=<>]')

# Punctuation
PUNCTUATION_PATTERN = re.compile(r'[.,():;]')


def tokenize_line(
    line: str,
    line_number: int = 1,
    is_comment: bool = False,
) -> List[Token]:
    """
    Tokenize a COBOL source line.

    Args:
        line: The code area content to tokenize (columns 8-72)
        line_number: The line number for context
        is_comment: Whether this is a comment line

    Returns:
        List of Token objects
    """
    tokens = []

    if is_comment:
        # Entire line is a comment
        tokens.append(Token(
            type=TokenType.COMMENT,
            value=line,
            start_pos=0,
            end_pos=len(line),
            line_number=line_number,
        ))
        return tokens

    # Find protected ranges (PIC and USAGE clauses)
    pic_clauses = find_pic_clauses(line)
    usage_clauses = find_usage_clauses(line)

    # Build a map of protected ranges
    protected_ranges = []
    for pic in pic_clauses:
        protected_ranges.append((pic.start_pos, pic.end_pos, TokenType.PIC_CLAUSE, pic.raw))
    for usage in usage_clauses:
        protected_ranges.append((usage.start_pos, usage.end_pos, TokenType.USAGE_CLAUSE, usage.raw))
    protected_ranges.sort(key=lambda x: x[0])

    pos = 0
    while pos < len(line):
        # Check if we're in a protected range
        in_protected = False
        for start, end, token_type, raw in protected_ranges:
            if start <= pos < end:
                # Create token for the entire protected range
                tokens.append(Token(
                    type=token_type,
                    value=raw,
                    start_pos=start,
                    end_pos=end,
                    line_number=line_number,
                ))
                pos = end
                in_protected = True
                break

        if in_protected:
            continue

        # Try to match patterns in order of specificity

        # Whitespace
        match = WHITESPACE_PATTERN.match(line, pos)
        if match:
            tokens.append(Token(
                type=TokenType.WHITESPACE,
                value=match.group(),
                start_pos=pos,
                end_pos=match.end(),
                line_number=line_number,
            ))
            pos = match.end()
            continue

        # String literals
        match = STRING_LITERAL_PATTERN.match(line, pos)
        if match:
            tokens.append(Token(
                type=TokenType.LITERAL_STRING,
                value=match.group(),
                start_pos=pos,
                end_pos=match.end(),
                line_number=line_number,
            ))
            pos = match.end()
            continue

        # Operators (check before numeric to handle +/- signs)
        match = OPERATOR_PATTERN.match(line, pos)
        if match:
            tokens.append(Token(
                type=TokenType.OPERATOR,
                value=match.group(),
                start_pos=pos,
                end_pos=match.end(),
                line_number=line_number,
            ))
            pos = match.end()
            continue

        # Punctuation
        match = PUNCTUATION_PATTERN.match(line, pos)
        if match:
            tokens.append(Token(
                type=TokenType.PUNCTUATION,
                value=match.group(),
                start_pos=pos,
                end_pos=match.end(),
                line_number=line_number,
            ))
            pos = match.end()
            continue

        # Level numbers - check before identifiers and numeric literals
        # Level numbers are at the start of data definitions
        match = NUMERIC_LITERAL_PATTERN.match(line, pos)
        if match:
            value = match.group()
            # Check if this could be a level number (first non-whitespace on line)
            preceding_tokens = [t for t in tokens if t.type != TokenType.WHITESPACE]
            if not preceding_tokens and is_level_number(value):
                tokens.append(Token(
                    type=TokenType.LEVEL_NUMBER,
                    value=value,
                    start_pos=pos,
                    end_pos=match.end(),
                    line_number=line_number,
                ))
                pos = match.end()
                continue

        # Identifiers and reserved words
        match = IDENTIFIER_PATTERN.match(line, pos)
        if match:
            value = match.group()
            upper_value = value.upper()

            # Determine token type
            if is_level_number(value):
                token_type = TokenType.LEVEL_NUMBER
            elif is_reserved_word(value):
                token_type = TokenType.RESERVED
            elif is_figurative_constant(value):
                token_type = TokenType.RESERVED
            elif is_system_identifier(value):
                token_type = TokenType.IDENTIFIER
                # Mark as system identifier in metadata
                metadata = {"is_system": True}
            else:
                token_type = TokenType.IDENTIFIER
                metadata = {}

            tokens.append(Token(
                type=token_type,
                value=value,
                start_pos=pos,
                end_pos=match.end(),
                line_number=line_number,
                metadata=metadata if 'metadata' in dir() else {},
            ))
            pos = match.end()
            continue

        # Numeric literals (standalone numbers after identifiers have been checked)
        match = NUMERIC_LITERAL_PATTERN.match(line, pos)
        if match:
            tokens.append(Token(
                type=TokenType.LITERAL_NUMERIC,
                value=match.group(),
                start_pos=pos,
                end_pos=match.end(),
                line_number=line_number,
            ))
            pos = match.end()
            continue

        # Unknown character - advance by one
        tokens.append(Token(
            type=TokenType.UNKNOWN,
            value=line[pos],
            start_pos=pos,
            end_pos=pos + 1,
            line_number=line_number,
        ))
        pos += 1

    return tokens


def reconstruct_from_tokens(tokens: List[Token]) -> str:
    """
    Reconstruct a line from its tokens.

    Args:
        tokens: List of tokens (may have modified values)

    Returns:
        The reconstructed line string
    """
    if not tokens:
        return ""

    # Sort tokens by start position
    sorted_tokens = sorted(tokens, key=lambda t: t.start_pos)

    # Build the string
    result = []
    last_end = 0

    for token in sorted_tokens:
        # Fill any gap with spaces
        if token.start_pos > last_end:
            result.append(" " * (token.start_pos - last_end))

        result.append(token.value)
        last_end = token.start_pos + len(token.value)

    return "".join(result)


def get_identifiers(tokens: List[Token]) -> List[Token]:
    """
    Extract all identifier tokens from a token list.

    Args:
        tokens: List of tokens

    Returns:
        List of identifier tokens only
    """
    return [t for t in tokens if t.type == TokenType.IDENTIFIER]


def get_literals(tokens: List[Token]) -> List[Token]:
    """
    Extract all literal tokens from a token list.

    Args:
        tokens: List of tokens

    Returns:
        List of literal tokens (string and numeric)
    """
    return [t for t in tokens
            if t.type in (TokenType.LITERAL_STRING, TokenType.LITERAL_NUMERIC)]


def find_token_by_value(tokens: List[Token], value: str, case_insensitive: bool = True) -> Optional[Token]:
    """
    Find a token by its value.

    Args:
        tokens: List of tokens
        value: The value to find
        case_insensitive: Whether to ignore case

    Returns:
        The matching token, or None
    """
    for token in tokens:
        if case_insensitive:
            if token.value.upper() == value.upper():
                return token
        else:
            if token.value == value:
                return token
    return None


def contains_copy_statement(tokens: List[Token]) -> bool:
    """
    Check if the tokens contain a COPY statement.

    Args:
        tokens: List of tokens

    Returns:
        True if COPY reserved word is present
    """
    for token in tokens:
        if token.type == TokenType.RESERVED and token.value.upper() == "COPY":
            return True
    return False


def get_copy_name(tokens: List[Token]) -> Optional[str]:
    """
    Extract the copybook name from a COPY statement.

    Args:
        tokens: List of tokens (assumed to contain COPY)

    Returns:
        The copybook name, or None if not found
    """
    found_copy = False
    for token in tokens:
        if found_copy:
            if token.type == TokenType.WHITESPACE:
                continue
            if token.type == TokenType.IDENTIFIER:
                return token.value
            # Could be a reserved word used as name
            if token.type == TokenType.RESERVED:
                return token.value
            break
        if token.type == TokenType.RESERVED and token.value.upper() == "COPY":
            found_copy = True
    return None


def is_data_definition_line(tokens: List[Token]) -> bool:
    """
    Check if the tokens represent a data definition line.

    Data definitions start with a level number.

    Args:
        tokens: List of tokens

    Returns:
        True if this is a data definition line
    """
    for token in tokens:
        if token.type == TokenType.WHITESPACE:
            continue
        if token.type == TokenType.LEVEL_NUMBER:
            return True
        return False
    return False


def is_procedure_statement(tokens: List[Token]) -> bool:
    """
    Check if the tokens represent a procedure division statement.

    Args:
        tokens: List of tokens

    Returns:
        True if this appears to be a procedure statement
    """
    # Procedure statements typically start with a verb or paragraph name
    for token in tokens:
        if token.type == TokenType.WHITESPACE:
            continue
        if token.type == TokenType.RESERVED:
            # Common procedure verbs
            verbs = {"MOVE", "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "COMPUTE",
                     "IF", "ELSE", "END-IF", "PERFORM", "CALL", "GO", "GOBACK",
                     "STOP", "EXIT", "EVALUATE", "WHEN", "END-EVALUATE",
                     "DISPLAY", "ACCEPT", "READ", "WRITE", "REWRITE", "DELETE",
                     "OPEN", "CLOSE", "INITIALIZE", "SET", "STRING", "UNSTRING",
                     "INSPECT", "SEARCH"}
            return token.value.upper() in verbs
        if token.type == TokenType.IDENTIFIER:
            # Could be a paragraph name followed by SECTION or just an identifier
            return True
        return False
    return False
