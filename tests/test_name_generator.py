"""
Tests for Phase 5: Name Generator and Mapper.

Tests for name generation and mapping functionality.
"""

import pytest
import tempfile
from pathlib import Path

from cobol_anonymizer.core.classifier import IdentifierType
from cobol_anonymizer.generators.name_generator import (
    NAME_PREFIXES,
    NameGenerator,
    NameGeneratorConfig,
    NamingScheme,
    generate_anonymized_name,
    validate_generated_name,
)
from cobol_anonymizer.core.mapper import (
    MappingEntry,
    MappingTable,
    create_mapping_report,
)
from cobol_anonymizer.exceptions import IdentifierLengthError, ReservedWordCollisionError


class TestNamePrefixes:
    """Tests for name prefix configuration."""

    def test_all_types_have_prefixes(self):
        """All identifier types have prefix mappings."""
        for id_type in IdentifierType:
            assert id_type in NAME_PREFIXES

    def test_prefixes_are_short(self):
        """Prefixes are short to maximize counter digits."""
        for prefix in NAME_PREFIXES.values():
            assert len(prefix) <= 2


class TestNameGenerator:
    """Tests for NameGenerator class."""

    def test_generate_data_name(self):
        """Generate data name with correct prefix (numeric scheme)."""
        config = NameGeneratorConfig(naming_scheme=NamingScheme.NUMERIC)
        gen = NameGenerator(config=config)
        name = gen.generate("WS-CUSTOMER-NAME", IdentifierType.DATA_NAME)
        assert name.startswith("D")
        assert len(name) == len("WS-CUSTOMER-NAME")

    def test_generate_program_name(self):
        """Generate program name with PG prefix (numeric scheme)."""
        config = NameGeneratorConfig(naming_scheme=NamingScheme.NUMERIC)
        gen = NameGenerator(config=config)
        name = gen.generate("TESTPROG", IdentifierType.PROGRAM_NAME)
        assert name.startswith("PG")

    def test_generate_copybook_name(self):
        """Generate copybook name with CP prefix (numeric scheme)."""
        config = NameGeneratorConfig(naming_scheme=NamingScheme.NUMERIC)
        gen = NameGenerator(config=config)
        name = gen.generate("COPYBOOK", IdentifierType.COPYBOOK_NAME)
        assert name.startswith("CP")

    def test_generate_paragraph_name(self):
        """Generate paragraph name with PA prefix (numeric scheme)."""
        config = NameGeneratorConfig(naming_scheme=NamingScheme.NUMERIC)
        gen = NameGenerator(config=config)
        name = gen.generate("A001-INIT", IdentifierType.PARAGRAPH_NAME)
        assert name.startswith("PA")

    def test_name_generation_uniqueness(self):
        """Each call generates unique name."""
        gen = NameGenerator()
        names = set()
        for _ in range(100):
            name = gen.generate("WS-FIELD", IdentifierType.DATA_NAME)
            assert name not in names
            names.add(name)

    def test_length_preservation(self):
        """Generated name matches original length (up to 30) with numeric scheme."""
        config = NameGeneratorConfig(naming_scheme=NamingScheme.NUMERIC)
        gen = NameGenerator(config=config)

        # Short name
        short_name = gen.generate("ABC", IdentifierType.DATA_NAME)
        assert len(short_name) >= 3

        # Long name
        long_name = gen.generate("WS-VERY-LONG-IDENTIFIER-NAME", IdentifierType.DATA_NAME)
        assert len(long_name) == len("WS-VERY-LONG-IDENTIFIER-NAME")

        # Name over 30 chars truncated
        over_30 = "A" * 35
        truncated = gen.generate(over_30, IdentifierType.DATA_NAME)
        assert len(truncated) <= 30

    def test_no_trailing_hyphens(self):
        """Generated names do not have trailing hyphens."""
        gen = NameGenerator()
        for _ in range(50):
            name = gen.generate("WS-FIELD", IdentifierType.DATA_NAME)
            assert not name.endswith("-")
            assert not name.startswith("-")

    def test_zero_padded_counter(self):
        """Counter is zero-padded in generated names (numeric scheme)."""
        config = NameGeneratorConfig(naming_scheme=NamingScheme.NUMERIC)
        gen = NameGenerator(config=config)
        name = gen.generate("WS-FIELD", IdentifierType.DATA_NAME)
        # Name should be like "D0000001" not "D1"
        assert "0" in name

    def test_deterministic_with_seed(self):
        """Generation is deterministic with seed."""
        config = NameGeneratorConfig(seed=42)
        gen1 = NameGenerator(config=config)
        gen2 = NameGenerator(config=NameGeneratorConfig(seed=42))

        # Same seed should produce same sequence
        for _ in range(10):
            name1 = gen1.generate("FIELD", IdentifierType.DATA_NAME)
            name2 = gen2.generate("FIELD", IdentifierType.DATA_NAME)
            assert name1 == name2

    def test_get_counter_state(self):
        """Counter state can be retrieved."""
        gen = NameGenerator()
        gen.generate("A", IdentifierType.DATA_NAME)
        gen.generate("B", IdentifierType.PROGRAM_NAME)

        state = gen.get_counter_state()
        assert IdentifierType.DATA_NAME in state
        assert IdentifierType.PROGRAM_NAME in state

    def test_set_counter_state(self):
        """Counter state can be set for resuming."""
        gen = NameGenerator()
        state = {IdentifierType.DATA_NAME: 100}
        gen.set_counter_state(state)

        # Next name should use counter > 100
        name = gen.generate("FIELD", IdentifierType.DATA_NAME)
        # D0000101 for an 8-char name
        assert "101" in name

    def test_reset(self):
        """Reset clears counters and generated names."""
        gen = NameGenerator()
        gen.generate("FIELD1", IdentifierType.DATA_NAME)
        gen.generate("FIELD2", IdentifierType.DATA_NAME)
        gen.reset()

        # After reset, counter starts from 1
        name = gen.generate("FIELD", IdentifierType.DATA_NAME)
        assert "1" in name  # First generated name


class TestGenerateAnonymizedName:
    """Tests for standalone generate function."""

    def test_generate_simple(self):
        """Generate with standalone function."""
        name = generate_anonymized_name("FIELD", IdentifierType.DATA_NAME, 1)
        assert name.startswith("D")
        assert "1" in name

    def test_generate_with_counter(self):
        """Counter value is used in name."""
        name1 = generate_anonymized_name("FIELD", IdentifierType.DATA_NAME, 1)
        name2 = generate_anonymized_name("FIELD", IdentifierType.DATA_NAME, 42)
        assert name1 != name2


class TestValidateGeneratedName:
    """Tests for name validation."""

    def test_validate_valid_name(self):
        """Valid name passes validation."""
        # Should not raise
        validate_generated_name("D0000001")
        validate_generated_name("PG000001")

    def test_validate_too_long(self):
        """Name over 30 chars raises error."""
        long_name = "A" * 31
        with pytest.raises(IdentifierLengthError):
            validate_generated_name(long_name)

    def test_validate_reserved_word(self):
        """Reserved word raises error."""
        with pytest.raises(ReservedWordCollisionError):
            validate_generated_name("MOVE")


class TestMappingEntry:
    """Tests for MappingEntry dataclass."""

    def test_entry_creation(self):
        """MappingEntry can be created."""
        entry = MappingEntry(
            original_name="WS-FIELD",
            anonymized_name="D0000001",
            id_type=IdentifierType.DATA_NAME,
        )
        assert entry.original_name == "WS-FIELD"
        assert entry.occurrence_count == 1

    def test_entry_to_dict(self):
        """MappingEntry converts to dict."""
        entry = MappingEntry(
            original_name="WS-FIELD",
            anonymized_name="D0000001",
            id_type=IdentifierType.DATA_NAME,
        )
        data = entry.to_dict()
        assert data["original_name"] == "WS-FIELD"
        assert data["id_type"] == "DATA_NAME"

    def test_entry_from_dict(self):
        """MappingEntry loads from dict."""
        data = {
            "original_name": "WS-FIELD",
            "anonymized_name": "D0000001",
            "id_type": "DATA_NAME",
            "is_external": False,
        }
        entry = MappingEntry.from_dict(data)
        assert entry.original_name == "WS-FIELD"
        assert entry.id_type == IdentifierType.DATA_NAME


class TestMappingTable:
    """Tests for MappingTable class."""

    def test_get_or_create_new(self):
        """get_or_create creates new mapping."""
        table = MappingTable()
        name = table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        assert name is not None
        assert name != "WS-FIELD"

    def test_get_or_create_existing(self):
        """get_or_create returns existing mapping."""
        table = MappingTable()
        name1 = table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        name2 = table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        assert name1 == name2

    def test_case_insensitive_lookup(self):
        """Lookup is case-insensitive."""
        table = MappingTable()
        name1 = table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        name2 = table.get_or_create("ws-field", IdentifierType.DATA_NAME)
        name3 = table.get_or_create("Ws-Field", IdentifierType.DATA_NAME)
        assert name1 == name2 == name3

    def test_external_item_preserved(self):
        """EXTERNAL items keep original names."""
        table = MappingTable()
        name = table.get_or_create(
            "SHARED-AREA",
            IdentifierType.EXTERNAL_NAME,
            is_external=True,
        )
        assert name == "SHARED-AREA"

    def test_is_external(self):
        """is_external returns correct value."""
        table = MappingTable()
        table.get_or_create("SHARED-AREA", IdentifierType.EXTERNAL_NAME, is_external=True)
        assert table.is_external("SHARED-AREA")
        assert not table.is_external("WS-FIELD")

    def test_get_mapping(self):
        """get_mapping returns entry."""
        table = MappingTable()
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        entry = table.get_mapping("WS-FIELD")
        assert entry is not None
        assert entry.original_name == "WS-FIELD"

    def test_get_anonymized_name(self):
        """get_anonymized_name returns correct name."""
        table = MappingTable()
        anon = table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        retrieved = table.get_anonymized_name("WS-FIELD")
        assert retrieved == anon

    def test_get_original_name(self):
        """Reverse lookup works."""
        table = MappingTable()
        anon = table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        original = table.get_original_name(anon)
        assert original == "WS-FIELD"

    def test_occurrence_count(self):
        """Occurrence count increments."""
        table = MappingTable()
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        entry = table.get_mapping("WS-FIELD")
        assert entry.occurrence_count == 3

    def test_get_all_mappings(self):
        """get_all_mappings returns all entries."""
        table = MappingTable()
        table.get_or_create("A", IdentifierType.DATA_NAME)
        table.get_or_create("B", IdentifierType.DATA_NAME)
        table.get_or_create("C", IdentifierType.PROGRAM_NAME)

        mappings = table.get_all_mappings()
        assert len(mappings) == 3

    def test_get_mappings_by_type(self):
        """get_mappings_by_type filters correctly."""
        table = MappingTable()
        table.get_or_create("A", IdentifierType.DATA_NAME)
        table.get_or_create("B", IdentifierType.DATA_NAME)
        table.get_or_create("C", IdentifierType.PROGRAM_NAME)

        data_names = table.get_mappings_by_type(IdentifierType.DATA_NAME)
        assert len(data_names) == 2

    def test_get_statistics(self):
        """get_statistics returns correct counts."""
        table = MappingTable()
        table.get_or_create("A", IdentifierType.DATA_NAME)
        table.get_or_create("B", IdentifierType.DATA_NAME)
        table.get_or_create("PROG", IdentifierType.PROGRAM_NAME)
        table.get_or_create("EXT", IdentifierType.EXTERNAL_NAME, is_external=True)

        stats = table.get_statistics()
        assert stats["total_mappings"] == 4
        assert stats["external_count"] == 1


class TestMappingTablePersistence:
    """Tests for mapping table save/load."""

    def test_save_and_load(self, tmp_path):
        """Mapping table can be saved and loaded."""
        table = MappingTable()
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        table.get_or_create("TESTPROG", IdentifierType.PROGRAM_NAME)
        table.get_or_create("SHARED", IdentifierType.EXTERNAL_NAME, is_external=True)

        # Save
        save_path = tmp_path / "mappings.json"
        table.save_to_file(save_path)

        # Load
        loaded = MappingTable.load_from_file(save_path)

        # Verify
        assert loaded.get_anonymized_name("WS-FIELD") is not None
        assert loaded.is_external("SHARED")
        assert len(loaded.get_all_mappings()) == 3

    def test_to_dict(self):
        """to_dict produces valid structure."""
        table = MappingTable()
        table.get_or_create("FIELD", IdentifierType.DATA_NAME)

        data = table.to_dict()
        assert "mappings" in data
        assert "external_names" in data
        assert "generated_at" in data


class TestCreateMappingReport:
    """Tests for mapping report generation."""

    def test_create_report(self):
        """create_mapping_report produces output."""
        table = MappingTable()
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        table.get_or_create("TESTPROG", IdentifierType.PROGRAM_NAME)

        report = create_mapping_report(table)
        assert "WS-FIELD" in report
        assert "TESTPROG" in report
        assert "DATA_NAME" in report
        assert "PROGRAM_NAME" in report

    def test_report_shows_external(self):
        """Report shows EXTERNAL markers."""
        table = MappingTable()
        table.get_or_create("SHARED", IdentifierType.EXTERNAL_NAME, is_external=True)

        report = create_mapping_report(table)
        assert "[EXTERNAL]" in report
