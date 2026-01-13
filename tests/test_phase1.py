"""
Tests for Phase 1: Project Foundation.

Tests for exceptions, logging, and utility functions.
"""

import pytest
import logging

from cobol_anonymizer.exceptions import (
    AnonymizerError,
    ParseError,
    MappingError,
    ValidationError,
    ColumnOverflowError,
    IdentifierLengthError,
    InvalidIdentifierError,
    ConfigError,
    CopyNotFoundError,
    CircularDependencyError,
    ReservedWordCollisionError,
)
from cobol_anonymizer.logging_config import setup_logging, get_logger
from cobol_anonymizer.core.utils import (
    validate_identifier,
    normalize_identifier,
    identifiers_equal,
    is_level_number,
    get_level_number,
    is_filler,
    pad_to_length,
    truncate_to_length,
    calculate_column_position,
)


class TestExceptions:
    """Tests for exception classes."""

    def test_anonymizer_error_base(self):
        """AnonymizerError is the base exception."""
        err = AnonymizerError("test error")
        assert str(err) == "test error"
        assert isinstance(err, Exception)

    def test_parse_error_includes_location(self):
        """ParseError message includes file:line."""
        err = ParseError("PROGRAM.cob", 42, "unexpected token")
        assert "PROGRAM.cob:42" in str(err)
        assert "unexpected token" in str(err)
        assert err.file == "PROGRAM.cob"
        assert err.line == 42

    def test_column_overflow_error(self):
        """ColumnOverflowError raised when code exceeds column 72."""
        err = ColumnOverflowError("TEST.cob", 10, 70, 65)
        assert "TEST.cob:10" in str(err)
        assert "70" in str(err)
        assert "65" in str(err)
        assert err.actual_length == 70
        assert err.max_length == 65

    def test_identifier_length_error(self):
        """IdentifierLengthError for identifiers over 30 chars."""
        long_name = "A" * 35
        err = IdentifierLengthError(long_name, 35)
        assert "35" in str(err)
        assert "30" in str(err)
        assert err.identifier == long_name

    def test_invalid_identifier_error(self):
        """InvalidIdentifierError for invalid identifiers."""
        err = InvalidIdentifierError("123-BAD", "must start with a letter")
        assert "123-BAD" in str(err)
        assert "must start with a letter" in str(err)

    def test_copy_not_found_error(self):
        """CopyNotFoundError for missing copybooks."""
        err = CopyNotFoundError("MISSING", "PROG.cob", 15)
        assert "PROG.cob:15" in str(err)
        assert "MISSING" in str(err)
        assert err.copybook == "MISSING"

    def test_circular_dependency_error(self):
        """CircularDependencyError shows the cycle."""
        cycle = ["COPY1", "COPY2", "COPY3", "COPY1"]
        err = CircularDependencyError(cycle)
        assert "COPY1 -> COPY2 -> COPY3 -> COPY1" in str(err)
        assert err.cycle == cycle

    def test_reserved_word_collision_error(self):
        """ReservedWordCollisionError for reserved word collision."""
        err = ReservedWordCollisionError("MOVE0001", "MOVE")
        assert "MOVE0001" in str(err)
        assert "MOVE" in str(err)

    def test_exception_hierarchy(self):
        """All exceptions inherit from AnonymizerError."""
        assert issubclass(ParseError, AnonymizerError)
        assert issubclass(MappingError, AnonymizerError)
        assert issubclass(ValidationError, AnonymizerError)
        assert issubclass(ConfigError, AnonymizerError)
        assert issubclass(CopyNotFoundError, AnonymizerError)
        assert issubclass(CircularDependencyError, AnonymizerError)

    def test_validation_error_hierarchy(self):
        """Validation errors inherit from ValidationError."""
        assert issubclass(ColumnOverflowError, ValidationError)
        assert issubclass(IdentifierLengthError, ValidationError)
        assert issubclass(InvalidIdentifierError, ValidationError)


class TestLogging:
    """Tests for logging configuration."""

    def test_setup_logging_returns_logger(self):
        """setup_logging returns a logger instance."""
        logger = setup_logging(level="DEBUG")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "cobol_anonymizer"

    def test_get_logger_returns_logger(self):
        """get_logger returns a logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert "test_module" in logger.name

    def test_log_levels(self):
        """Log levels are set correctly."""
        logger = setup_logging(level="WARNING")
        assert logger.level == logging.WARNING


class TestIdentifierValidation:
    """Tests for identifier validation utilities."""

    def test_validate_identifier_valid(self):
        """Valid identifiers pass validation."""
        valid_names = [
            "A",
            "WS-FIELD",
            "CUSTOMER-NAME",
            "X123",
            "ABC-DEF-GHI",
            "A1B2C3",
        ]
        for name in valid_names:
            is_valid, error = validate_identifier(name, raise_on_error=False)
            assert is_valid, f"{name} should be valid: {error}"

    def test_validate_identifier_max_length(self):
        """Reject identifiers over 30 characters."""
        long_name = "A" * 31
        with pytest.raises(IdentifierLengthError):
            validate_identifier(long_name)

    def test_validate_identifier_max_length_exact(self):
        """Accept identifiers exactly 30 characters."""
        exact_name = "A" * 30
        is_valid, _ = validate_identifier(exact_name, raise_on_error=False)
        assert is_valid

    def test_validate_identifier_no_trailing_hyphen(self):
        """Reject identifiers ending with hyphen."""
        with pytest.raises(InvalidIdentifierError) as exc_info:
            validate_identifier("WS-FIELD-")
        assert "cannot end with hyphen" in str(exc_info.value)

    def test_validate_identifier_no_leading_hyphen(self):
        """Reject identifiers starting with hyphen."""
        with pytest.raises(InvalidIdentifierError) as exc_info:
            validate_identifier("-WS-FIELD")
        assert "must start with a letter" in str(exc_info.value)

    def test_validate_identifier_must_start_with_letter(self):
        """Reject identifiers starting with digit."""
        with pytest.raises(InvalidIdentifierError) as exc_info:
            validate_identifier("123-FIELD")
        assert "must start with a letter" in str(exc_info.value)

    def test_validate_identifier_empty(self):
        """Reject empty identifiers."""
        with pytest.raises(InvalidIdentifierError):
            validate_identifier("")

    def test_validate_identifier_invalid_chars(self):
        """Reject identifiers with invalid characters."""
        invalid_names = ["WS_FIELD", "WS.FIELD", "WS FIELD", "WS@FIELD"]
        for name in invalid_names:
            is_valid, error = validate_identifier(name, raise_on_error=False)
            assert not is_valid, f"{name} should be invalid"


class TestIdentifierComparison:
    """Tests for identifier comparison utilities."""

    def test_normalize_identifier(self):
        """normalize_identifier returns uppercase."""
        assert normalize_identifier("ws-field") == "WS-FIELD"
        assert normalize_identifier("WS-FIELD") == "WS-FIELD"
        assert normalize_identifier("Ws-Field") == "WS-FIELD"

    def test_identifiers_equal_case_insensitive(self):
        """identifiers_equal is case-insensitive."""
        assert identifiers_equal("WS-FIELD", "ws-field")
        assert identifiers_equal("ws-field", "WS-FIELD")
        assert identifiers_equal("Ws-Field", "wS-fIELD")

    def test_identifiers_equal_different(self):
        """Different identifiers are not equal."""
        assert not identifiers_equal("WS-FIELD-A", "WS-FIELD-B")


class TestLevelNumbers:
    """Tests for level number utilities."""

    def test_is_level_number_valid(self):
        """Valid level numbers are recognized."""
        valid = ["01", "1", "05", "5", "10", "49", "66", "77", "88"]
        for level in valid:
            assert is_level_number(level), f"{level} should be valid"

    def test_is_level_number_invalid(self):
        """Invalid level numbers are rejected."""
        invalid = ["00", "50", "65", "78", "89", "99", "AB", ""]
        for level in invalid:
            assert not is_level_number(level), f"{level} should be invalid"

    def test_get_level_number(self):
        """get_level_number parses correctly."""
        assert get_level_number("01") == 1
        assert get_level_number("05") == 5
        assert get_level_number("88") == 88
        assert get_level_number(" 77 ") == 77

    def test_get_level_number_invalid(self):
        """get_level_number raises for invalid."""
        with pytest.raises(ValueError):
            get_level_number("50")


class TestFiller:
    """Tests for FILLER detection."""

    def test_is_filler_true(self):
        """FILLER is detected."""
        assert is_filler("FILLER")
        assert is_filler("filler")
        assert is_filler("Filler")

    def test_is_filler_false(self):
        """Non-FILLER names are not detected."""
        assert not is_filler("WS-FILLER")
        assert not is_filler("FILLER-X")


class TestStringUtilities:
    """Tests for string utilities."""

    def test_pad_to_length(self):
        """pad_to_length pads correctly."""
        assert pad_to_length("ABC", 6) == "ABC   "
        assert pad_to_length("ABC", 3) == "ABC"
        assert pad_to_length("ABC", 2) == "ABC"
        assert pad_to_length("ABC", 6, "X") == "ABCXXX"

    def test_truncate_to_length(self):
        """truncate_to_length truncates correctly."""
        assert truncate_to_length("ABCDEF", 3) == "ABC"
        assert truncate_to_length("ABC", 6) == "ABC"
        assert truncate_to_length("ABC", 3) == "ABC"


class TestColumnPosition:
    """Tests for column position calculations."""

    def test_calculate_column_position(self):
        """calculate_column_position returns correct column."""
        assert calculate_column_position("sequence", 0) == 1
        assert calculate_column_position("indicator", 0) == 7
        assert calculate_column_position("A", 0) == 8
        assert calculate_column_position("B", 0) == 12
        assert calculate_column_position("identification", 0) == 73
