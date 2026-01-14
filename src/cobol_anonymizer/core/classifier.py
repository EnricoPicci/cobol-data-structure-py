"""
COBOL Identifier Classifier - Classifies identifiers by their role.

This module analyzes COBOL source to classify identifiers:
- PROGRAM_NAME: Program identifiers from PROGRAM-ID
- COPYBOOK_NAME: Copybook names from COPY statements
- SECTION_NAME: Section names in PROCEDURE DIVISION
- PARAGRAPH_NAME: Paragraph names in PROCEDURE DIVISION
- DATA_NAME: Data item names (01-49, 66, 77 levels)
- CONDITION_NAME: 88-level condition names
- FILE_NAME: File names from FD/SD declarations
- INDEX_NAME: Index names from INDEXED BY clauses

Classification requires context tracking to properly identify
identifier types based on their location in the source.
"""

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Set, Dict, Tuple

from cobol_anonymizer.core.tokenizer import (
    Token,
    TokenType,
    tokenize_line,
    get_identifiers,
)
from cobol_anonymizer.cobol.pic_parser import has_external_clause
from cobol_anonymizer.cobol.reserved_words import is_reserved_word, is_system_identifier


class IdentifierType(Enum):
    """Types of identifiers in COBOL."""
    PROGRAM_NAME = auto()      # PROGRAM-ID
    COPYBOOK_NAME = auto()     # COPY statement
    SECTION_NAME = auto()      # PROCEDURE DIVISION section
    PARAGRAPH_NAME = auto()    # PROCEDURE DIVISION paragraph
    DATA_NAME = auto()         # Data item (01-49, 66, 77)
    CONDITION_NAME = auto()    # 88-level condition
    FILE_NAME = auto()         # FD/SD file
    INDEX_NAME = auto()        # INDEXED BY
    EXTERNAL_NAME = auto()     # EXTERNAL data items (do not anonymize)
    UNKNOWN = auto()           # Cannot determine type


class Division(Enum):
    """COBOL division types."""
    IDENTIFICATION = "IDENTIFICATION"
    ENVIRONMENT = "ENVIRONMENT"
    DATA = "DATA"
    PROCEDURE = "PROCEDURE"
    NONE = "NONE"


class DataSection(Enum):
    """COBOL data division sections."""
    FILE = "FILE"
    WORKING_STORAGE = "WORKING-STORAGE"
    LOCAL_STORAGE = "LOCAL-STORAGE"
    LINKAGE = "LINKAGE"
    SCREEN = "SCREEN"
    REPORT = "REPORT"
    NONE = "NONE"


@dataclass
class ClassifiedIdentifier:
    """
    An identifier with its classification.

    Attributes:
        name: The identifier name
        type: The identifier type classification
        line_number: Line where it was found
        context: Additional context info
        is_definition: True if this is the defining occurrence
        is_external: True if marked as EXTERNAL
        level_number: Level number for data items
        parent_name: Name of parent group item
    """
    name: str
    type: IdentifierType
    line_number: int
    context: str = ""
    is_definition: bool = False
    is_external: bool = False
    level_number: Optional[int] = None
    parent_name: Optional[str] = None


@dataclass
class FileContext:
    """
    Tracks context while parsing a COBOL file.

    This context is essential for proper identifier classification.
    """
    filename: str
    current_division: Division = Division.NONE
    current_section: DataSection = DataSection.NONE
    in_procedure_division: bool = False
    current_level: int = 0
    level_stack: List[Tuple[int, str]] = field(default_factory=list)
    is_external_block: bool = False
    last_paragraph: Optional[str] = None
    last_section: Optional[str] = None
    in_copy_statement: bool = False
    in_fd_declaration: bool = False
    current_fd_name: Optional[str] = None

    def enter_division(self, division: Division) -> None:
        """Enter a new division."""
        self.current_division = division
        self.current_section = DataSection.NONE
        self.in_procedure_division = (division == Division.PROCEDURE)
        if division != Division.DATA:
            self.level_stack.clear()
            self.is_external_block = False

    def enter_section(self, section: DataSection) -> None:
        """Enter a data division section."""
        self.current_section = section
        self.level_stack.clear()
        self.is_external_block = False

    def push_level(self, level: int, name: str) -> None:
        """Push a level onto the stack."""
        # Pop items with same or higher level number
        while self.level_stack and self.level_stack[-1][0] >= level:
            self.level_stack.pop()
        self.level_stack.append((level, name))
        self.current_level = level

    def get_parent_name(self) -> Optional[str]:
        """Get the parent group item name."""
        if len(self.level_stack) >= 2:
            return self.level_stack[-2][1]
        return None


class IdentifierClassifier:
    """
    Classifies COBOL identifiers based on context.

    Usage:
        classifier = IdentifierClassifier("PROGRAM.cob")
        for line_num, line in enumerate(lines, 1):
            identifiers = classifier.classify_line(line, line_num)
    """

    def __init__(self, filename: str):
        """
        Initialize the classifier.

        Args:
            filename: Name of the file being processed
        """
        self.context = FileContext(filename=filename)
        self.identifiers: List[ClassifiedIdentifier] = []
        self.seen_definitions: Set[str] = set()

    def _get_first_non_whitespace(self, tokens: List[Token]) -> Optional[Token]:
        """Get the first non-whitespace token from a token list."""
        for token in tokens:
            if token.type != TokenType.WHITESPACE:
                return token
        return None

    def _find_token_after_keyword(
        self,
        tokens: List[Token],
        keywords: Set[str],
        expected_types: Optional[Set[TokenType]] = None,
        substring_match: bool = False,
    ) -> Optional[Token]:
        """
        Find the first matching token after a keyword.

        Args:
            tokens: List of tokens to search
            keywords: Set of keyword values to look for (uppercase)
            expected_types: Optional set of expected token types after keyword
            substring_match: If True, check if any keyword is contained in token value

        Returns:
            The token found after the keyword, or None
        """
        if expected_types is None:
            expected_types = {TokenType.IDENTIFIER, TokenType.RESERVED}

        found_keyword = False
        for token in tokens:
            if token.type == TokenType.WHITESPACE:
                continue
            if found_keyword:
                if token.type in expected_types:
                    return token
                # Skip punctuation (like periods after keywords) and continue looking
                if token.type == TokenType.PUNCTUATION:
                    continue
                return None  # Found non-matching, non-punctuation token after keyword
            # Check if this token is the keyword
            if token.type in (TokenType.RESERVED, TokenType.IDENTIFIER):
                token_upper = token.value.upper()
                if substring_match:
                    if any(kw in token_upper for kw in keywords):
                        found_keyword = True
                else:
                    if token_upper in keywords:
                        found_keyword = True
        return None

    def classify_line(
        self,
        line: str,
        line_number: int,
        is_comment: bool = False,
    ) -> List[ClassifiedIdentifier]:
        """
        Classify identifiers in a single line.

        Args:
            line: The code area content
            line_number: Line number in the file
            is_comment: Whether this is a comment line

        Returns:
            List of classified identifiers found
        """
        if is_comment:
            return []

        classified = []
        upper_line = line.upper()

        # Update context based on division/section headers
        self._update_context(upper_line)

        # Check for EXTERNAL clause
        is_external = has_external_clause(line)
        if is_external:
            self.context.is_external_block = True

        # Tokenize the line
        tokens = tokenize_line(line, line_number)

        # Check for specific patterns
        if "PROGRAM-ID" in upper_line:
            id_result = self._classify_program_id(tokens, line_number)
            if id_result:
                classified.append(id_result)

        elif self._is_copy_statement(upper_line):
            id_result = self._classify_copy_statement(tokens, line_number)
            if id_result:
                classified.append(id_result)

        elif self._is_fd_sd_declaration(upper_line):
            id_result = self._classify_fd_declaration(tokens, line_number)
            if id_result:
                classified.append(id_result)

        elif self._is_section_header(tokens, upper_line):
            id_result = self._classify_section_header(tokens, line_number)
            if id_result:
                classified.append(id_result)

        elif self._is_paragraph_definition(tokens, upper_line):
            id_result = self._classify_paragraph(tokens, line_number)
            if id_result:
                classified.append(id_result)

        elif self._is_data_definition(tokens):
            id_results = self._classify_data_definition(tokens, line_number, is_external)
            classified.extend(id_results)

        else:
            # Classify identifiers in procedural code
            id_results = self._classify_references(tokens, line_number)
            classified.extend(id_results)

        self.identifiers.extend(classified)
        return classified

    def _update_context(self, upper_line: str) -> None:
        """Update parsing context based on line content."""
        # Check for division headers
        if "IDENTIFICATION DIVISION" in upper_line:
            self.context.enter_division(Division.IDENTIFICATION)
        elif "ENVIRONMENT DIVISION" in upper_line:
            self.context.enter_division(Division.ENVIRONMENT)
        elif "DATA DIVISION" in upper_line:
            self.context.enter_division(Division.DATA)
        elif "PROCEDURE DIVISION" in upper_line:
            self.context.enter_division(Division.PROCEDURE)

        # Check for data section headers
        if self.context.current_division == Division.DATA:
            if "FILE SECTION" in upper_line:
                self.context.enter_section(DataSection.FILE)
            elif "WORKING-STORAGE SECTION" in upper_line:
                self.context.enter_section(DataSection.WORKING_STORAGE)
            elif "LOCAL-STORAGE SECTION" in upper_line:
                self.context.enter_section(DataSection.LOCAL_STORAGE)
            elif "LINKAGE SECTION" in upper_line:
                self.context.enter_section(DataSection.LINKAGE)

    def _is_copy_statement(self, upper_line: str) -> bool:
        """Check if line is a COPY statement."""
        return bool(re.search(r'\bCOPY\s+', upper_line))

    def _is_fd_sd_declaration(self, upper_line: str) -> bool:
        """Check if line is an FD or SD declaration."""
        return bool(re.search(r'^\s*(FD|SD)\s+', upper_line))

    def _is_section_header(self, tokens: List[Token], upper_line: str) -> bool:
        """Check if line is a section header in PROCEDURE DIVISION."""
        if not self.context.in_procedure_division:
            return False
        # Section headers: identifier SECTION.
        return bool(re.search(r'\bSECTION\s*\.', upper_line))

    def _is_paragraph_definition(self, tokens: List[Token], upper_line: str) -> bool:
        """Check if line is a paragraph definition."""
        if not self.context.in_procedure_division:
            return False
        # Paragraph: identifier starting in Area A, ending with period
        # Skip lines starting with reserved words
        stripped = upper_line.strip()
        if not stripped:
            return False

        # Get first token that's not whitespace
        for token in tokens:
            if token.type == TokenType.WHITESPACE:
                continue
            if token.type == TokenType.IDENTIFIER:
                # Check if line ends with period and has no other significant content
                remaining = stripped[len(token.value):].strip()
                return remaining == "." or remaining == ""
            return False
        return False

    def _is_data_definition(self, tokens: List[Token]) -> bool:
        """Check if line is a data definition."""
        first_token = self._get_first_non_whitespace(tokens)
        return first_token is not None and first_token.type == TokenType.LEVEL_NUMBER

    def _classify_program_id(
        self,
        tokens: List[Token],
        line_number: int,
    ) -> Optional[ClassifiedIdentifier]:
        """Classify PROGRAM-ID identifier."""
        # PROGRAM-ID can be tokenized as one token or split, so use substring match
        token = self._find_token_after_keyword(tokens, {"PROGRAM-ID"}, substring_match=True)
        if token:
            self.seen_definitions.add(token.value.upper())
            return ClassifiedIdentifier(
                name=token.value,
                type=IdentifierType.PROGRAM_NAME,
                line_number=line_number,
                context="PROGRAM-ID declaration",
                is_definition=True,
            )
        return None

    def _classify_copy_statement(
        self,
        tokens: List[Token],
        line_number: int,
    ) -> Optional[ClassifiedIdentifier]:
        """Classify COPY statement copybook name."""
        token = self._find_token_after_keyword(tokens, {"COPY"})
        if token:
            return ClassifiedIdentifier(
                name=token.value,
                type=IdentifierType.COPYBOOK_NAME,
                line_number=line_number,
                context="COPY statement",
                is_definition=False,
            )
        return None

    def _classify_fd_declaration(
        self,
        tokens: List[Token],
        line_number: int,
    ) -> Optional[ClassifiedIdentifier]:
        """Classify FD/SD file name."""
        token = self._find_token_after_keyword(
            tokens, {"FD", "SD"}, expected_types={TokenType.IDENTIFIER}
        )
        if token:
            self.context.current_fd_name = token.value
            self.seen_definitions.add(token.value.upper())
            return ClassifiedIdentifier(
                name=token.value,
                type=IdentifierType.FILE_NAME,
                line_number=line_number,
                context="FD/SD declaration",
                is_definition=True,
            )
        return None

    def _classify_section_header(
        self,
        tokens: List[Token],
        line_number: int,
    ) -> Optional[ClassifiedIdentifier]:
        """Classify SECTION name."""
        first_token = self._get_first_non_whitespace(tokens)
        if first_token and first_token.type == TokenType.IDENTIFIER:
            self.context.last_section = first_token.value
            self.seen_definitions.add(first_token.value.upper())
            return ClassifiedIdentifier(
                name=first_token.value,
                type=IdentifierType.SECTION_NAME,
                line_number=line_number,
                context="PROCEDURE DIVISION section",
                is_definition=True,
            )
        return None

    def _classify_paragraph(
        self,
        tokens: List[Token],
        line_number: int,
    ) -> Optional[ClassifiedIdentifier]:
        """Classify paragraph name."""
        first_token = self._get_first_non_whitespace(tokens)
        if first_token and first_token.type == TokenType.IDENTIFIER:
            self.context.last_paragraph = first_token.value
            self.seen_definitions.add(first_token.value.upper())
            return ClassifiedIdentifier(
                name=first_token.value,
                type=IdentifierType.PARAGRAPH_NAME,
                line_number=line_number,
                context="PROCEDURE DIVISION paragraph",
                is_definition=True,
            )
        return None

    def _classify_data_definition(
        self,
        tokens: List[Token],
        line_number: int,
        is_external: bool = False,
    ) -> List[ClassifiedIdentifier]:
        """Classify data definition identifiers."""
        classified = []

        level_number = None
        data_name = None
        in_indexed_by = False

        for i, token in enumerate(tokens):
            if token.type == TokenType.LEVEL_NUMBER:
                level_number = int(token.value)

            elif token.type == TokenType.IDENTIFIER:
                if data_name is None and not in_indexed_by:
                    # This is the data item name
                    data_name = token.value

                    # Determine type
                    if level_number == 88:
                        id_type = IdentifierType.CONDITION_NAME
                    elif is_external or self.context.is_external_block:
                        id_type = IdentifierType.EXTERNAL_NAME
                    else:
                        id_type = IdentifierType.DATA_NAME

                    # Update level stack for non-88 levels
                    if level_number and level_number != 88:
                        self.context.push_level(level_number, data_name)

                    self.seen_definitions.add(data_name.upper())
                    classified.append(ClassifiedIdentifier(
                        name=data_name,
                        type=id_type,
                        line_number=line_number,
                        context=f"Level {level_number} data item",
                        is_definition=True,
                        is_external=is_external,
                        level_number=level_number,
                        parent_name=self.context.get_parent_name(),
                    ))

                elif in_indexed_by:
                    # Index name
                    self.seen_definitions.add(token.value.upper())
                    classified.append(ClassifiedIdentifier(
                        name=token.value,
                        type=IdentifierType.INDEX_NAME,
                        line_number=line_number,
                        context="INDEXED BY",
                        is_definition=True,
                    ))

            elif token.type == TokenType.RESERVED:
                if token.value.upper() == "INDEXED":
                    # Check if next non-whitespace is BY
                    for j in range(i + 1, len(tokens)):
                        if tokens[j].type == TokenType.WHITESPACE:
                            continue
                        if tokens[j].type == TokenType.RESERVED and tokens[j].value.upper() == "BY":
                            in_indexed_by = True
                        break

        return classified

    def _classify_references(
        self,
        tokens: List[Token],
        line_number: int,
    ) -> List[ClassifiedIdentifier]:
        """Classify identifier references in procedural code."""
        classified = []

        for token in tokens:
            if token.type == TokenType.IDENTIFIER:
                # Skip if it's a reserved word or system identifier
                if is_reserved_word(token.value) or is_system_identifier(token.value):
                    continue

                # This is a reference to an identifier
                # Try to determine type from previous definitions
                upper_name = token.value.upper()
                if upper_name in self.seen_definitions:
                    id_type = IdentifierType.DATA_NAME  # Most likely
                else:
                    id_type = IdentifierType.UNKNOWN

                classified.append(ClassifiedIdentifier(
                    name=token.value,
                    type=id_type,
                    line_number=line_number,
                    context="Reference",
                    is_definition=False,
                ))

        return classified

    def get_all_identifiers(self) -> List[ClassifiedIdentifier]:
        """Get all classified identifiers."""
        return self.identifiers

    def get_definitions(self) -> List[ClassifiedIdentifier]:
        """Get only definition occurrences."""
        return [i for i in self.identifiers if i.is_definition]

    def get_external_identifiers(self) -> List[ClassifiedIdentifier]:
        """Get identifiers marked as EXTERNAL."""
        return [i for i in self.identifiers if i.is_external or i.type == IdentifierType.EXTERNAL_NAME]

    def get_identifiers_by_type(self, id_type: IdentifierType) -> List[ClassifiedIdentifier]:
        """Get identifiers of a specific type."""
        return [i for i in self.identifiers if i.type == id_type]


def classify_cobol_file(
    lines: List[str],
    filename: str,
    comment_indicators: Set[str] = None,
) -> List[ClassifiedIdentifier]:
    """
    Classify all identifiers in a COBOL file.

    Args:
        lines: List of code area content (columns 8-72)
        filename: Name of the file
        comment_indicators: Set of indicators that mark comment lines

    Returns:
        List of all classified identifiers
    """
    if comment_indicators is None:
        comment_indicators = {"*", "/"}

    classifier = IdentifierClassifier(filename)

    for line_num, line in enumerate(lines, 1):
        # Determine if comment (would need indicator from caller)
        is_comment = False
        classifier.classify_line(line, line_num, is_comment)

    return classifier.get_all_identifiers()
