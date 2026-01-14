"""
Tests for COBOL naming schemes.

This module tests the naming scheme strategies for identifier anonymization.
"""

import pytest

from cobol_anonymizer.core.classifier import IdentifierType
from cobol_anonymizer.generators.naming_schemes import (
    NAME_PREFIXES,
    AnimalNamingStrategy,
    CorporateNamingStrategy,
    FantasyNamingStrategy,
    FoodNamingStrategy,
    NamingScheme,
    NumericNamingStrategy,
    get_naming_strategy,
)


class TestNamingSchemeEnum:
    """Tests for NamingScheme enum."""

    def test_all_schemes_defined(self):
        """All expected schemes are defined."""
        expected = {"numeric", "animals", "food", "fantasy", "corporate"}
        actual = {s.value for s in NamingScheme}
        assert actual == expected

    def test_scheme_string_values(self):
        """Schemes are string enums."""
        assert NamingScheme.NUMERIC == "numeric"
        assert NamingScheme.ANIMALS == "animals"
        assert NamingScheme.FOOD == "food"
        assert NamingScheme.FANTASY == "fantasy"
        assert NamingScheme.CORPORATE == "corporate"


class TestFactoryFunction:
    """Tests for get_naming_strategy factory."""

    def test_factory_returns_correct_strategy_types(self):
        """Factory returns correct strategy type for each scheme."""
        assert isinstance(get_naming_strategy(NamingScheme.NUMERIC), NumericNamingStrategy)
        assert isinstance(get_naming_strategy(NamingScheme.ANIMALS), AnimalNamingStrategy)
        assert isinstance(get_naming_strategy(NamingScheme.FOOD), FoodNamingStrategy)
        assert isinstance(get_naming_strategy(NamingScheme.FANTASY), FantasyNamingStrategy)
        assert isinstance(get_naming_strategy(NamingScheme.CORPORATE), CorporateNamingStrategy)

    def test_factory_error_on_invalid_string(self):
        """Factory raises ValueError for invalid string input."""
        with pytest.raises(ValueError) as excinfo:
            get_naming_strategy("invalid_scheme")
        assert "Invalid naming scheme" in str(excinfo.value)

    def test_factory_error_on_none(self):
        """Factory raises ValueError for None input."""
        with pytest.raises(ValueError) as excinfo:
            get_naming_strategy(None)
        assert "Invalid naming scheme" in str(excinfo.value)

    def test_factory_error_on_wrong_type(self):
        """Factory raises ValueError for wrong type input."""
        with pytest.raises(ValueError) as excinfo:
            get_naming_strategy(123)
        assert "Invalid naming scheme" in str(excinfo.value)


class TestNumericNamingStrategy:
    """Tests for NumericNamingStrategy."""

    @pytest.fixture
    def strategy(self):
        return get_naming_strategy(NamingScheme.NUMERIC)

    def test_format_with_prefix(self, strategy):
        """Numeric names start with correct prefix."""
        name = strategy.generate_name("WS-FIELD", IdentifierType.DATA_NAME, 1, 10)
        assert name.startswith("D")

    def test_format_zero_padded(self, strategy):
        """Counter is zero-padded to fill available space."""
        name = strategy.generate_name("WS-FIELD", IdentifierType.DATA_NAME, 1, 10)
        # D + 9 digits = 10 chars
        assert name == "D000000001"

    def test_different_prefixes_for_types(self, strategy):
        """Different identifier types get different prefixes."""
        assert strategy.generate_name("X", IdentifierType.DATA_NAME, 1, 5).startswith("D")
        assert strategy.generate_name("X", IdentifierType.SECTION_NAME, 1, 5).startswith("SC")
        assert strategy.generate_name("X", IdentifierType.PARAGRAPH_NAME, 1, 5).startswith("PA")
        assert strategy.generate_name("X", IdentifierType.PROGRAM_NAME, 1, 5).startswith("PG")
        assert strategy.generate_name("X", IdentifierType.COPYBOOK_NAME, 1, 5).startswith("CP")

    def test_counter_overflow(self, strategy):
        """Large counters that overflow available space work correctly."""
        name = strategy.generate_name("X", IdentifierType.DATA_NAME, 999999999, 5)
        # Can't fit zero-padded, so just uses counter as-is
        assert name == "D999999999"

    def test_get_scheme(self, strategy):
        """Returns correct scheme identifier."""
        assert strategy.get_scheme() == NamingScheme.NUMERIC


class TestAnimalNamingStrategy:
    """Tests for AnimalNamingStrategy."""

    @pytest.fixture
    def strategy(self):
        return get_naming_strategy(NamingScheme.ANIMALS)

    def test_format_adjective_noun_counter(self, strategy):
        """Animal names follow ADJECTIVE-NOUN-counter format."""
        name = strategy.generate_name("WS-FIELD", IdentifierType.DATA_NAME, 1, 30)
        parts = name.split("-")
        assert len(parts) == 3
        assert parts[2].isdigit()

    def test_uses_word_lists(self, strategy):
        """Generated adjectives and nouns come from word lists."""
        name = strategy.generate_name("WS-FIELD", IdentifierType.DATA_NAME, 1, 30)
        parts = name.split("-")
        assert parts[0] in AnimalNamingStrategy.ADJECTIVES
        assert parts[1] in AnimalNamingStrategy.NOUNS

    def test_get_scheme(self, strategy):
        """Returns correct scheme identifier."""
        assert strategy.get_scheme() == NamingScheme.ANIMALS


class TestFoodNamingStrategy:
    """Tests for FoodNamingStrategy."""

    @pytest.fixture
    def strategy(self):
        return get_naming_strategy(NamingScheme.FOOD)

    def test_format_adjective_noun_counter(self, strategy):
        """Food names follow ADJECTIVE-NOUN-counter format."""
        name = strategy.generate_name("WS-FIELD", IdentifierType.DATA_NAME, 1, 30)
        parts = name.split("-")
        assert len(parts) == 3
        assert parts[2].isdigit()

    def test_uses_word_lists(self, strategy):
        """Generated adjectives and nouns come from word lists."""
        name = strategy.generate_name("WS-FIELD", IdentifierType.DATA_NAME, 1, 30)
        parts = name.split("-")
        assert parts[0] in FoodNamingStrategy.ADJECTIVES
        assert parts[1] in FoodNamingStrategy.NOUNS

    def test_get_scheme(self, strategy):
        """Returns correct scheme identifier."""
        assert strategy.get_scheme() == NamingScheme.FOOD


class TestFantasyNamingStrategy:
    """Tests for FantasyNamingStrategy."""

    @pytest.fixture
    def strategy(self):
        return get_naming_strategy(NamingScheme.FANTASY)

    def test_format_adjective_noun_counter(self, strategy):
        """Fantasy names follow ADJECTIVE-NOUN-counter format."""
        name = strategy.generate_name("WS-FIELD", IdentifierType.DATA_NAME, 1, 30)
        parts = name.split("-")
        assert len(parts) == 3
        assert parts[2].isdigit()

    def test_get_scheme(self, strategy):
        """Returns correct scheme identifier."""
        assert strategy.get_scheme() == NamingScheme.FANTASY


class TestCorporateNamingStrategy:
    """Tests for CorporateNamingStrategy."""

    @pytest.fixture
    def strategy(self):
        return get_naming_strategy(NamingScheme.CORPORATE)

    def test_format_adjective_noun_counter(self, strategy):
        """Corporate names follow ADJECTIVE-NOUN-counter format."""
        name = strategy.generate_name("WS-FIELD", IdentifierType.DATA_NAME, 1, 30)
        parts = name.split("-")
        assert len(parts) == 3
        assert parts[2].isdigit()

    def test_get_scheme(self, strategy):
        """Returns correct scheme identifier."""
        assert strategy.get_scheme() == NamingScheme.CORPORATE


class TestDeterminism:
    """Tests for deterministic name generation."""

    def test_same_input_same_output(self):
        """Same original name always produces same adjective-noun combination."""
        strategy = get_naming_strategy(NamingScheme.ANIMALS)
        name1 = strategy.generate_name("CUSTOMER-NAME", IdentifierType.DATA_NAME, 1, 30)
        name2 = strategy.generate_name("CUSTOMER-NAME", IdentifierType.DATA_NAME, 1, 30)
        assert name1 == name2

    def test_different_inputs_different_combinations(self):
        """Different original names produce different adjective-noun combinations."""
        strategy = get_naming_strategy(NamingScheme.ANIMALS)
        name1 = strategy.generate_name("FIELD-A", IdentifierType.DATA_NAME, 1, 30)
        name2 = strategy.generate_name("FIELD-B", IdentifierType.DATA_NAME, 1, 30)
        # Extract adjective-noun (without counter)
        combo1 = "-".join(name1.split("-")[:2])
        combo2 = "-".join(name2.split("-")[:2])
        # Should be different (with high probability)
        assert combo1 != combo2

    def test_case_insensitive_hashing(self):
        """Hash is case-insensitive (COBOL standard)."""
        strategy = get_naming_strategy(NamingScheme.FOOD)
        name_upper = strategy.generate_name("MY-FIELD", IdentifierType.DATA_NAME, 1, 30)
        name_lower = strategy.generate_name("my-field", IdentifierType.DATA_NAME, 1, 30)
        name_mixed = strategy.generate_name("My-FiElD", IdentifierType.DATA_NAME, 1, 30)
        assert name_upper == name_lower == name_mixed


class TestLengthConstraints:
    """Tests for length constraint handling."""

    def test_max_length_30_respected(self):
        """Generated names never exceed 30 characters (COBOL limit)."""
        for scheme in NamingScheme:
            strategy = get_naming_strategy(scheme)
            for counter in [1, 100, 10000, 99999]:
                name = strategy.generate_name("TEST", IdentifierType.DATA_NAME, counter, 30)
                assert len(name) <= 30, f"Scheme {scheme}: {name} exceeds 30 chars"

    def test_truncation_works(self):
        """Names are truncated when they exceed target length."""
        strategy = get_naming_strategy(NamingScheme.ANIMALS)
        # With a 15-char limit and counter 999999
        name = strategy.generate_name("TEST", IdentifierType.DATA_NAME, 999999, 15)
        assert len(name) <= 15

    def test_minimum_length_fallback_to_numeric(self):
        """Word-based schemes fall back to numeric for very short lengths."""
        strategy = get_naming_strategy(NamingScheme.ANIMALS)
        # target_length=4 cannot fit "A-B-1" (5 chars min)
        name = strategy.generate_name("TEST", IdentifierType.DATA_NAME, 1, 4)
        # Should fall back to numeric format (starts with D)
        assert name.startswith("D")


class TestCOBOLIdentifierValidity:
    """Tests for COBOL identifier validity."""

    def test_starts_with_letter(self):
        """Generated names always start with a letter."""
        for scheme in NamingScheme:
            strategy = get_naming_strategy(scheme)
            name = strategy.generate_name("TEST", IdentifierType.DATA_NAME, 1, 30)
            assert name[0].isalpha(), f"Scheme {scheme}: {name} doesn't start with letter"

    def test_no_trailing_hyphen(self):
        """Generated names never end with a hyphen."""
        for scheme in NamingScheme:
            strategy = get_naming_strategy(scheme)
            name = strategy.generate_name("TEST", IdentifierType.DATA_NAME, 1, 30)
            assert not name.endswith("-"), f"Scheme {scheme}: {name} ends with hyphen"

    def test_only_alphanumeric_and_hyphens(self):
        """Generated names contain only alphanumeric chars and hyphens."""
        for scheme in NamingScheme:
            strategy = get_naming_strategy(scheme)
            name = strategy.generate_name("TEST", IdentifierType.DATA_NAME, 1, 30)
            for char in name:
                assert (
                    char.isalnum() or char == "-"
                ), f"Scheme {scheme}: {name} contains invalid char '{char}'"

    def test_no_double_hyphens(self):
        """Generated names never contain double hyphens."""
        for scheme in NamingScheme:
            strategy = get_naming_strategy(scheme)
            for counter in [1, 100, 10000]:
                name = strategy.generate_name("TEST", IdentifierType.DATA_NAME, counter, 30)
                assert "--" not in name, f"Scheme {scheme}: {name} contains double hyphen"


class TestEdgeCases:
    """Tests for edge cases."""

    def test_counter_overflow_with_truncation(self):
        """Large counters are handled during truncation."""
        strategy = get_naming_strategy(NamingScheme.ANIMALS)
        # Very large counter with limited length
        name = strategy.generate_name("TEST", IdentifierType.DATA_NAME, 123456789, 15)
        assert len(name) <= 15
        # Should still end with the counter
        assert "123456789" in name or name.startswith("D")  # Either truncated or fell back

    def test_all_schemes_available_and_functional(self):
        """All defined schemes can be instantiated and generate names."""
        for scheme in NamingScheme:
            strategy = get_naming_strategy(scheme)
            assert strategy is not None
            assert strategy.get_scheme() == scheme
            name = strategy.generate_name("TEST-FIELD", IdentifierType.DATA_NAME, 1, 20)
            assert len(name) > 0
            assert len(name) <= 20

    def test_empty_original_name(self):
        """Empty original names still produce valid output."""
        for scheme in NamingScheme:
            strategy = get_naming_strategy(scheme)
            name = strategy.generate_name("", IdentifierType.DATA_NAME, 1, 20)
            assert len(name) > 0
            assert len(name) <= 20

    def test_very_long_original_name(self):
        """Very long original names still produce valid output."""
        strategy = get_naming_strategy(NamingScheme.ANIMALS)
        long_name = "A" * 100
        name = strategy.generate_name(long_name, IdentifierType.DATA_NAME, 1, 30)
        assert len(name) <= 30


class TestNamePrefixes:
    """Tests for NAME_PREFIXES constant."""

    def test_all_identifier_types_have_prefix(self):
        """All identifier types have a defined prefix."""
        for id_type in IdentifierType:
            assert id_type in NAME_PREFIXES, f"Missing prefix for {id_type}"

    def test_prefix_lengths(self):
        """Prefixes are reasonably short."""
        for id_type, prefix in NAME_PREFIXES.items():
            assert len(prefix) <= 2, f"Prefix '{prefix}' for {id_type} is too long"


class TestIntegrationWithNameGenerator:
    """Integration tests with NameGenerator."""

    def test_name_generator_uses_strategy(self):
        """NameGenerator correctly uses the configured strategy."""
        from cobol_anonymizer.generators.name_generator import (
            NameGenerator,
            NameGeneratorConfig,
        )

        # Numeric scheme
        config_numeric = NameGeneratorConfig(naming_scheme=NamingScheme.NUMERIC)
        gen_numeric = NameGenerator(config=config_numeric)
        name_numeric = gen_numeric.generate("TEST-FIELD", IdentifierType.DATA_NAME)
        assert name_numeric.startswith("D")
        assert name_numeric[1:].isdigit()

        # Animals scheme
        config_animals = NameGeneratorConfig(naming_scheme=NamingScheme.ANIMALS)
        gen_animals = NameGenerator(config=config_animals)
        name_animals = gen_animals.generate("TEST-FIELD", IdentifierType.DATA_NAME)
        # Should be ADJECTIVE-NOUN-counter format
        parts = name_animals.split("-")
        assert len(parts) == 3


class TestIntegrationWithMappingTable:
    """Integration tests with MappingTable."""

    def test_mapping_table_uses_scheme(self):
        """MappingTable correctly uses the configured naming scheme."""
        from cobol_anonymizer.core.mapper import MappingTable

        # Numeric scheme
        table_numeric = MappingTable(_naming_scheme=NamingScheme.NUMERIC)
        name_numeric = table_numeric.get_or_create("TEST-FIELD", IdentifierType.DATA_NAME)
        assert name_numeric.startswith("D")

        # Animals scheme
        table_animals = MappingTable(_naming_scheme=NamingScheme.ANIMALS)
        name_animals = table_animals.get_or_create("TEST-FIELD", IdentifierType.DATA_NAME)
        parts = name_animals.split("-")
        assert len(parts) == 3

    def test_mapping_table_serialization_preserves_scheme(self):
        """MappingTable to_dict includes naming scheme."""
        from cobol_anonymizer.core.mapper import MappingTable

        table = MappingTable(_naming_scheme=NamingScheme.FOOD)
        table.get_or_create("TEST-FIELD", IdentifierType.DATA_NAME)
        data = table.to_dict()
        assert data["naming_scheme"] == "food"

    def test_mapping_table_load_restores_scheme(self, tmp_path):
        """MappingTable load_from_file restores naming scheme."""
        from cobol_anonymizer.core.mapper import MappingTable

        # Create and save
        table = MappingTable(_naming_scheme=NamingScheme.FANTASY)
        table.get_or_create("TEST-FIELD", IdentifierType.DATA_NAME)
        path = tmp_path / "mappings.json"
        table.save_to_file(path)

        # Load and verify
        loaded_table = MappingTable.load_from_file(path)
        assert loaded_table._naming_scheme == NamingScheme.FANTASY


class TestIntegrationWithConfig:
    """Integration tests with Config."""

    def test_config_has_naming_scheme_field(self):
        """Config has naming_scheme field with correct default."""
        from cobol_anonymizer.config import Config

        config = Config()
        assert config.naming_scheme == NamingScheme.CORPORATE

    def test_config_serialization(self):
        """Config to_dict correctly serializes naming_scheme."""
        from cobol_anonymizer.config import Config

        config = Config(naming_scheme=NamingScheme.CORPORATE)
        data = config.to_dict()
        assert data["naming_scheme"] == "corporate"

    def test_config_deserialization(self):
        """Config from_dict correctly deserializes naming_scheme."""
        from cobol_anonymizer.config import Config

        data = {"naming_scheme": "animals"}
        config = Config.from_dict(data)
        assert config.naming_scheme == NamingScheme.ANIMALS

    def test_config_invalid_scheme_defaults_to_numeric(self):
        """Config from_dict defaults to NUMERIC for invalid scheme."""
        from cobol_anonymizer.config import Config

        data = {"naming_scheme": "invalid_scheme_xyz"}
        config = Config.from_dict(data)
        assert config.naming_scheme == NamingScheme.NUMERIC
