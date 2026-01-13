"""
Tests for Phase 3.3: COBOL Tokenizer.

Tests for tokenizing COBOL source lines.
"""

import pytest

from cobol_anonymizer.core.tokenizer import (
    TokenType,
    Token,
    tokenize_line,
    tokenize_code_area,
    reconstruct_from_tokens,
    get_identifiers,
    get_literals,
    find_token_by_value,
    contains_copy_statement,
    get_copy_name,
    is_data_definition_line,
    is_procedure_statement,
)


class TestTokenClass:
    """Tests for the Token dataclass."""

    def test_token_creation(self):
        """Token can be created with all fields."""
        token = Token(
            type=TokenType.IDENTIFIER,
            value="WS-FIELD",
            start_pos=0,
            end_pos=8,
            line_number=1,
        )
        assert token.type == TokenType.IDENTIFIER
        assert token.value == "WS-FIELD"
        assert token.length == 8

    def test_token_length(self):
        """Token length is calculated correctly."""
        token = Token(
            type=TokenType.IDENTIFIER,
            value="ABC",
            start_pos=10,
            end_pos=13,
        )
        assert token.length == 3

    def test_token_was_modified(self):
        """was_modified tracks changes."""
        token = Token(
            type=TokenType.IDENTIFIER,
            value="NEW-NAME",
            start_pos=0,
            end_pos=8,
            original_value="OLD-NAME",
        )
        assert token.was_modified

    def test_token_not_modified(self):
        """was_modified is False when unchanged."""
        token = Token(
            type=TokenType.IDENTIFIER,
            value="SAME",
            start_pos=0,
            end_pos=4,
        )
        assert not token.was_modified

    def test_token_upper_value(self):
        """upper_value returns uppercase."""
        token = Token(
            type=TokenType.IDENTIFIER,
            value="ws-field",
            start_pos=0,
            end_pos=8,
        )
        assert token.upper_value() == "WS-FIELD"


class TestTokenizeBasic:
    """Tests for basic tokenization."""

    def test_tokenize_single_identifier(self):
        """Tokenize a single identifier."""
        tokens = tokenize_line("WS-FIELD")
        identifiers = [t for t in tokens if t.type == TokenType.IDENTIFIER]
        assert len(identifiers) == 1
        assert identifiers[0].value == "WS-FIELD"

    def test_tokenize_reserved_word(self):
        """Tokenize a reserved word."""
        tokens = tokenize_line("MOVE")
        reserved = [t for t in tokens if t.type == TokenType.RESERVED]
        assert len(reserved) == 1
        assert reserved[0].value == "MOVE"

    def test_tokenize_level_number(self):
        """Tokenize a level number."""
        tokens = tokenize_line("05")
        levels = [t for t in tokens if t.type == TokenType.LEVEL_NUMBER]
        assert len(levels) == 1
        assert levels[0].value == "05"

    def test_tokenize_string_literal(self):
        """Tokenize a string literal."""
        tokens = tokenize_line("'HELLO'")
        literals = [t for t in tokens if t.type == TokenType.LITERAL_STRING]
        assert len(literals) == 1
        assert literals[0].value == "'HELLO'"

    def test_tokenize_numeric_literal(self):
        """Tokenize a numeric literal."""
        tokens = tokenize_line("12345")
        literals = [t for t in tokens if t.type == TokenType.LITERAL_NUMERIC]
        assert len(literals) == 1
        assert literals[0].value == "12345"

    def test_tokenize_whitespace(self):
        """Tokenize whitespace."""
        tokens = tokenize_line("   ")
        whitespace = [t for t in tokens if t.type == TokenType.WHITESPACE]
        assert len(whitespace) == 1
        assert whitespace[0].value == "   "

    def test_tokenize_punctuation(self):
        """Tokenize punctuation."""
        tokens = tokenize_line(".")
        punct = [t for t in tokens if t.type == TokenType.PUNCTUATION]
        assert len(punct) == 1
        assert punct[0].value == "."


class TestTokenizeDataDefinition:
    """Tests for tokenizing data definition lines."""

    def test_tokenize_01_level(self):
        """Tokenize 01 level definition."""
        tokens = tokenize_line("01 WS-RECORD.")
        assert any(t.type == TokenType.LEVEL_NUMBER and t.value == "01" for t in tokens)
        assert any(t.type == TokenType.IDENTIFIER and t.value == "WS-RECORD" for t in tokens)

    def test_tokenize_05_level_with_pic(self):
        """Tokenize 05 level with PIC clause."""
        tokens = tokenize_line("05 WS-FIELD PIC X(30).")
        assert any(t.type == TokenType.LEVEL_NUMBER for t in tokens)
        assert any(t.type == TokenType.IDENTIFIER for t in tokens)
        assert any(t.type == TokenType.PIC_CLAUSE for t in tokens)

    def test_tokenize_88_level(self):
        """Tokenize 88 level condition."""
        tokens = tokenize_line("88 WS-VALID VALUE 'Y'.")
        assert any(t.type == TokenType.LEVEL_NUMBER and t.value == "88" for t in tokens)
        assert any(t.type == TokenType.IDENTIFIER for t in tokens)
        assert any(t.type == TokenType.RESERVED and t.value.upper() == "VALUE" for t in tokens)

    def test_tokenize_with_redefines(self):
        """Tokenize REDEFINES clause."""
        tokens = tokenize_line("05 WS-X REDEFINES WS-Y PIC X.")
        reserved = [t for t in tokens if t.type == TokenType.RESERVED]
        assert any(t.value.upper() == "REDEFINES" for t in reserved)

    def test_tokenize_with_comp3(self):
        """Tokenize COMP-3 usage."""
        tokens = tokenize_line("05 WS-AMOUNT PIC S9(7)V99 COMP-3.")
        assert any(t.type == TokenType.PIC_CLAUSE for t in tokens)
        assert any(t.type == TokenType.USAGE_CLAUSE for t in tokens)


class TestTokenizeProcedure:
    """Tests for tokenizing procedure division statements."""

    def test_tokenize_move_statement(self):
        """Tokenize MOVE statement."""
        tokens = tokenize_line("MOVE SPACES TO WS-FIELD.")
        reserved = [t for t in tokens if t.type == TokenType.RESERVED]
        assert any(t.value.upper() == "MOVE" for t in reserved)
        assert any(t.value.upper() == "SPACES" for t in reserved)
        assert any(t.value.upper() == "TO" for t in reserved)

    def test_tokenize_perform_statement(self):
        """Tokenize PERFORM statement."""
        tokens = tokenize_line("PERFORM A001-INIT THRU A001-EXIT.")
        reserved = [t for t in tokens if t.type == TokenType.RESERVED]
        assert any(t.value.upper() == "PERFORM" for t in reserved)
        assert any(t.value.upper() == "THRU" for t in reserved)

    def test_tokenize_call_statement(self):
        """Tokenize CALL statement."""
        tokens = tokenize_line("CALL 'SUBPROG' USING WS-DATA.")
        reserved = [t for t in tokens if t.type == TokenType.RESERVED]
        assert any(t.value.upper() == "CALL" for t in reserved)
        assert any(t.value.upper() == "USING" for t in reserved)
        literals = [t for t in tokens if t.type == TokenType.LITERAL_STRING]
        assert len(literals) == 1

    def test_tokenize_if_statement(self):
        """Tokenize IF statement."""
        tokens = tokenize_line("IF WS-FLAG = 'Y'")
        reserved = [t for t in tokens if t.type == TokenType.RESERVED]
        assert any(t.value.upper() == "IF" for t in reserved)


class TestTokenizeCopyStatement:
    """Tests for tokenizing COPY statements."""

    def test_tokenize_copy_simple(self):
        """Tokenize simple COPY statement."""
        tokens = tokenize_line("COPY SAMPLE01.")
        assert contains_copy_statement(tokens)
        assert get_copy_name(tokens) == "SAMPLE01"

    def test_tokenize_copy_replacing(self):
        """Tokenize COPY REPLACING statement."""
        tokens = tokenize_line("COPY COPYBOOK REPLACING ==OLD== BY ==NEW==.")
        assert contains_copy_statement(tokens)
        assert get_copy_name(tokens) == "COPYBOOK"

    def test_no_copy_statement(self):
        """Line without COPY statement."""
        tokens = tokenize_line("MOVE X TO Y.")
        assert not contains_copy_statement(tokens)


class TestTokenizeComment:
    """Tests for tokenizing comment lines."""

    def test_tokenize_comment_line(self):
        """Tokenize a comment line."""
        tokens = tokenize_line("THIS IS A COMMENT", is_comment=True)
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.COMMENT
        assert tokens[0].value == "THIS IS A COMMENT"


class TestReconstructLine:
    """Tests for reconstructing lines from tokens."""

    def test_reconstruct_simple(self):
        """Reconstruct simple line."""
        tokens = tokenize_line("MOVE X TO Y")
        reconstructed = reconstruct_from_tokens(tokens)
        assert "MOVE" in reconstructed
        assert "TO" in reconstructed

    def test_reconstruct_preserves_spacing(self):
        """Reconstruction preserves original spacing."""
        original = "01  WS-RECORD."
        tokens = tokenize_line(original)
        reconstructed = reconstruct_from_tokens(tokens)
        assert "01" in reconstructed
        assert "WS-RECORD" in reconstructed

    def test_reconstruct_modified_token(self):
        """Reconstruction uses modified token values."""
        tokens = tokenize_line("WS-FIELD")
        # Modify the token
        for token in tokens:
            if token.type == TokenType.IDENTIFIER:
                token.value = "D0000001"
        reconstructed = reconstruct_from_tokens(tokens)
        assert "D0000001" in reconstructed
        assert "WS-FIELD" not in reconstructed


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_identifiers(self):
        """get_identifiers returns only identifiers."""
        tokens = tokenize_line("MOVE WS-A TO WS-B.")
        identifiers = get_identifiers(tokens)
        assert all(t.type == TokenType.IDENTIFIER for t in identifiers)
        values = [t.value for t in identifiers]
        assert "WS-A" in values
        assert "WS-B" in values

    def test_get_literals(self):
        """get_literals returns string and numeric literals."""
        tokens = tokenize_line("MOVE 'ABC' TO WS-F. ADD 5 TO WS-C.")
        literals = get_literals(tokens)
        assert any(t.value == "'ABC'" for t in literals)
        assert any(t.value == "5" for t in literals)

    def test_find_token_by_value(self):
        """find_token_by_value finds matching token."""
        tokens = tokenize_line("MOVE WS-FIELD TO WS-OTHER.")
        token = find_token_by_value(tokens, "WS-FIELD")
        assert token is not None
        assert token.value == "WS-FIELD"

    def test_find_token_by_value_case_insensitive(self):
        """find_token_by_value is case-insensitive by default."""
        tokens = tokenize_line("MOVE WS-FIELD TO WS-OTHER.")
        token = find_token_by_value(tokens, "ws-field")
        assert token is not None

    def test_find_token_by_value_not_found(self):
        """find_token_by_value returns None when not found."""
        tokens = tokenize_line("MOVE WS-FIELD TO WS-OTHER.")
        token = find_token_by_value(tokens, "NOT-FOUND")
        assert token is None


class TestLineTypeDetection:
    """Tests for line type detection."""

    def test_is_data_definition_line_true(self):
        """Detect data definition line."""
        tokens = tokenize_line("05 WS-FIELD PIC X.")
        assert is_data_definition_line(tokens)

    def test_is_data_definition_line_false(self):
        """Non-data definition line."""
        tokens = tokenize_line("MOVE X TO Y.")
        assert not is_data_definition_line(tokens)

    def test_is_procedure_statement_true(self):
        """Detect procedure statement."""
        tokens = tokenize_line("MOVE SPACES TO WS-FIELD.")
        assert is_procedure_statement(tokens)

    def test_is_procedure_statement_if(self):
        """Detect IF statement."""
        tokens = tokenize_line("IF WS-FLAG = 'Y'")
        assert is_procedure_statement(tokens)


class TestRealWorldLines:
    """Tests using realistic COBOL lines."""

    def test_tokenize_complex_data_item(self):
        """Tokenize complex data item definition."""
        line = "05  Q130-NUMERO-POLIZZA         PIC X(20)."
        tokens = tokenize_line(line)
        identifiers = get_identifiers(tokens)
        assert any(t.value == "Q130-NUMERO-POLIZZA" for t in identifiers)

    def test_tokenize_comp3_field(self):
        """Tokenize COMP-3 field."""
        line = "05 WS-IMPORTO         PIC S9(13)V99 COMP-3."
        tokens = tokenize_line(line)
        assert any(t.type == TokenType.PIC_CLAUSE for t in tokens)
        assert any(t.type == TokenType.USAGE_CLAUSE for t in tokens)

    def test_tokenize_occurs_depending(self):
        """Tokenize OCCURS DEPENDING clause."""
        line = "05 WS-TABLE OCCURS 1 TO 100 DEPENDING ON WS-COUNT."
        tokens = tokenize_line(line)
        reserved = [t for t in tokens if t.type == TokenType.RESERVED]
        assert any(t.value.upper() == "OCCURS" for t in reserved)
        assert any(t.value.upper() == "DEPENDING" for t in reserved)

    def test_tokenize_value_thru(self):
        """Tokenize VALUE THRU clause."""
        line = "88 WS-VALID VALUE 1 THRU 100."
        tokens = tokenize_line(line)
        reserved = [t for t in tokens if t.type == TokenType.RESERVED]
        assert any(t.value.upper() == "VALUE" for t in reserved)
        assert any(t.value.upper() == "THRU" for t in reserved)

    def test_tokenize_string_with_quotes(self):
        """Tokenize line with quoted strings."""
        line = "DISPLAY 'HELLO WORLD' 'GOODBYE'."
        tokens = tokenize_line(line)
        strings = [t for t in tokens if t.type == TokenType.LITERAL_STRING]
        assert len(strings) == 2
