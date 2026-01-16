"""Tests for the literal anonymizer module."""

import pytest

from cobol_anonymizer.core.literal_anonymizer import (
    LiteralAnonymizer,
    select_literal_scheme,
    transform_literals,
)
from cobol_anonymizer.generators.naming_schemes import NamingScheme


class TestLiteralAnonymizer:
    """Tests for the LiteralAnonymizer class."""

    def test_create_anonymizer(self):
        """Create a literal anonymizer."""
        anon = LiteralAnonymizer(NamingScheme.ANIMALS)
        assert anon.scheme == NamingScheme.ANIMALS

    def test_anonymize_preserves_length(self):
        """Anonymized literal has same length as original."""
        anon = LiteralAnonymizer(NamingScheme.ANIMALS, seed=42)
        original = "CUSTOMER ACCOUNT BALANCE"
        result = anon.anonymize_literal(original)
        assert len(result) == len(original)

    def test_anonymize_short_string(self):
        """Short strings are anonymized correctly."""
        anon = LiteralAnonymizer(NamingScheme.ANIMALS, seed=42)
        assert len(anon.anonymize_literal("AB")) == 2
        assert len(anon.anonymize_literal("ABC")) == 3

    def test_anonymize_single_char(self):
        """Single character is anonymized to single character."""
        anon = LiteralAnonymizer(NamingScheme.ANIMALS, seed=42)
        result = anon.anonymize_literal("X")
        assert len(result) == 1
        assert result.isalpha()

    def test_anonymize_empty_string(self):
        """Empty string returns empty string."""
        anon = LiteralAnonymizer(NamingScheme.ANIMALS, seed=42)
        assert anon.anonymize_literal("") == ""

    def test_deterministic_with_seed(self):
        """Same seed produces same result."""
        anon1 = LiteralAnonymizer(NamingScheme.ANIMALS, seed=42)
        anon2 = LiteralAnonymizer(NamingScheme.ANIMALS, seed=42)
        original = "TEST STRING"
        assert anon1.anonymize_literal(original) == anon2.anonymize_literal(original)

    def test_different_without_seed(self):
        """Different seeds produce different results."""
        anon1 = LiteralAnonymizer(NamingScheme.ANIMALS, seed=42)
        anon2 = LiteralAnonymizer(NamingScheme.ANIMALS, seed=123)
        original = "TEST STRING"
        # While not guaranteed, different seeds should usually give different results
        # Run multiple times to account for possible collisions
        results1 = [anon1.anonymize_literal(f"TEST{i}") for i in range(10)]
        results2 = [anon2.anonymize_literal(f"TEST{i}") for i in range(10)]
        assert results1 != results2


class TestSelectLiteralScheme:
    """Tests for the select_literal_scheme function."""

    def test_selects_different_scheme(self):
        """Selected scheme is different from main scheme."""
        for main_scheme in NamingScheme:
            selected = select_literal_scheme(main_scheme, seed=42)
            assert selected != main_scheme

    def test_deterministic_with_seed(self):
        """Same seed produces same selection."""
        result1 = select_literal_scheme(NamingScheme.NUMERIC, seed=42)
        result2 = select_literal_scheme(NamingScheme.NUMERIC, seed=42)
        assert result1 == result2


class TestTransformLiterals:
    """Tests for the transform_literals function."""

    def test_transform_single_quoted_literal(self):
        """Transform single-quoted string literal."""
        anon = LiteralAnonymizer(NamingScheme.ANIMALS, seed=42)
        line = "           MOVE 'CUSTOMER NAME' TO WS-NAME."
        result = transform_literals(line, anon)
        # Should have transformed the literal
        assert "'CUSTOMER NAME'" not in result
        # Should preserve structure
        assert "MOVE" in result
        assert "TO WS-NAME" in result

    def test_transform_double_quoted_literal(self):
        """Transform double-quoted string literal."""
        anon = LiteralAnonymizer(NamingScheme.ANIMALS, seed=42)
        line = '           DISPLAY "HELLO WORLD".'
        result = transform_literals(line, anon)
        # Should have transformed the literal
        assert '"HELLO WORLD"' not in result
        # Should preserve structure
        assert "DISPLAY" in result

    def test_preserves_length(self):
        """Transformed line preserves literal length."""
        anon = LiteralAnonymizer(NamingScheme.ANIMALS, seed=42)
        original_literal = "CUSTOMER ACCOUNT BALANCE"
        line = f"           MOVE '{original_literal}' TO WS-DESC."
        result = transform_literals(line, anon)
        # Extract the new literal
        import re

        match = re.search(r"'([^']*)'", result)
        assert match
        assert len(match.group(1)) == len(original_literal)

    def test_disabled_returns_unchanged(self):
        """When disabled, returns line unchanged."""
        anon = LiteralAnonymizer(NamingScheme.ANIMALS, seed=42)
        line = "           MOVE 'CUSTOMER NAME' TO WS-NAME."
        result = transform_literals(line, anon, enabled=False)
        assert result == line

    def test_no_literal_unchanged(self):
        """Line without literals is unchanged."""
        anon = LiteralAnonymizer(NamingScheme.ANIMALS, seed=42)
        line = "           MOVE WS-A TO WS-B."
        result = transform_literals(line, anon)
        assert result == line

    def test_multiple_literals(self):
        """Multiple literals in one line are all transformed."""
        anon = LiteralAnonymizer(NamingScheme.ANIMALS, seed=42)
        line = "           IF WS-A = 'YES' OR WS-B = 'NO'."
        result = transform_literals(line, anon)
        assert "'YES'" not in result
        assert "'NO'" not in result


class TestLiteralSchemes:
    """Test that different schemes work for literals."""

    @pytest.mark.parametrize(
        "scheme",
        [
            NamingScheme.ANIMALS,
            NamingScheme.FOOD,
            NamingScheme.FANTASY,
            NamingScheme.CORPORATE,
            NamingScheme.NUMERIC,
        ],
    )
    def test_all_schemes_work(self, scheme):
        """All naming schemes can be used for literals."""
        anon = LiteralAnonymizer(scheme, seed=42)
        original = "TEST STRING HERE"
        result = anon.anonymize_literal(original)
        assert len(result) == len(original)
        assert result != original
