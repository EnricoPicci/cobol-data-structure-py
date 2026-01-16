"""
Tests for CSV export functionality.

Tests for exporting mapping tables to CSV format.
"""

import csv

from cobol_anonymizer.core.classifier import IdentifierType
from cobol_anonymizer.core.mapper import MappingTable
from cobol_anonymizer.generators.naming_schemes import NamingScheme


class TestMappingTableCSVExport:
    """Tests for MappingTable.save_to_csv()."""

    def test_csv_export_basic(self, tmp_path):
        """Basic CSV export with sample mappings."""
        table = MappingTable(_naming_scheme=NamingScheme.NUMERIC)

        # Add some mappings
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        table.get_or_create("CUSTOMER-NAME", IdentifierType.DATA_NAME)
        table.get_or_create("MAIN-PROGRAM", IdentifierType.PROGRAM_NAME)

        # Save to CSV
        csv_path = tmp_path / "mappings.csv"
        table.save_to_csv(csv_path)

        # Verify file exists
        assert csv_path.exists()

        # Read and verify CSV content
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 3

        # Verify header columns
        expected_columns = [
            "original_name",
            "anonymized_name",
            "id_type",
            "is_external",
            "first_seen_file",
            "first_seen_line",
            "occurrence_count",
            "naming_scheme",
            "generated_at",
        ]
        assert list(rows[0].keys()) == expected_columns

        # Check that original names are present
        original_names = {row["original_name"] for row in rows}
        assert "WS-FIELD" in original_names
        assert "CUSTOMER-NAME" in original_names
        assert "MAIN-PROGRAM" in original_names

    def test_csv_export_with_external_names(self, tmp_path):
        """CSV export includes external names."""
        # With _preserve_external=True, external items keep original names
        table = MappingTable(_naming_scheme=NamingScheme.NUMERIC, _preserve_external=True)

        # Add regular mapping
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        # Add external name
        table.get_or_create("EXTERNAL-ITEM", IdentifierType.DATA_NAME, is_external=True)

        # Save to CSV
        csv_path = tmp_path / "mappings.csv"
        table.save_to_csv(csv_path)

        # Read and verify
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2

        # Find external entry
        external_row = next(r for r in rows if r["original_name"] == "EXTERNAL-ITEM")
        assert external_row["is_external"] == "true"
        assert external_row["anonymized_name"] == "EXTERNAL-ITEM"  # Unchanged when preserving

        # Find regular entry
        regular_row = next(r for r in rows if r["original_name"] == "WS-FIELD")
        assert regular_row["is_external"] == "false"

    def test_csv_export_with_external_names_anonymized(self, tmp_path):
        """CSV export shows external names are anonymized by default."""
        # With _preserve_external=False (default), external items are anonymized
        table = MappingTable(_naming_scheme=NamingScheme.NUMERIC)

        # Add regular mapping
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        # Add external name (will be anonymized since _preserve_external=False)
        table.get_or_create("EXTERNAL-ITEM", IdentifierType.DATA_NAME, is_external=True)

        # Save to CSV
        csv_path = tmp_path / "mappings.csv"
        table.save_to_csv(csv_path)

        # Read and verify
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2

        # Find external entry - still marked as external but has anonymized name
        external_row = next(r for r in rows if r["original_name"] == "EXTERNAL-ITEM")
        assert external_row["is_external"] == "true"
        assert external_row["anonymized_name"] != "EXTERNAL-ITEM"  # Anonymized

        # Find regular entry
        regular_row = next(r for r in rows if r["original_name"] == "WS-FIELD")
        assert regular_row["is_external"] == "false"

    def test_csv_export_with_null_values(self, tmp_path):
        """CSV export handles null values correctly."""
        table = MappingTable(_naming_scheme=NamingScheme.NUMERIC)

        # Add mapping without file/line info (nulls)
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        # Save to CSV
        csv_path = tmp_path / "mappings.csv"
        table.save_to_csv(csv_path)

        # Read and verify
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["first_seen_file"] == ""
        assert rows[0]["first_seen_line"] == ""

    def test_csv_export_with_file_line_info(self, tmp_path):
        """CSV export preserves file and line information."""
        table = MappingTable(_naming_scheme=NamingScheme.NUMERIC)

        # Add mapping with file/line info
        table.get_or_create(
            "WS-FIELD",
            IdentifierType.DATA_NAME,
            file_name="test.cob",
            line_number=42,
        )

        # Save to CSV
        csv_path = tmp_path / "mappings.csv"
        table.save_to_csv(csv_path)

        # Read and verify
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["first_seen_file"] == "test.cob"
        assert rows[0]["first_seen_line"] == "42"

    def test_csv_export_naming_scheme(self, tmp_path):
        """CSV export includes naming scheme."""
        table = MappingTable(_naming_scheme=NamingScheme.ANIMALS)
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        csv_path = tmp_path / "mappings.csv"
        table.save_to_csv(csv_path)

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert rows[0]["naming_scheme"] == "animals"

    def test_csv_export_generated_at(self, tmp_path):
        """CSV export includes generated_at timestamp."""
        table = MappingTable(_naming_scheme=NamingScheme.NUMERIC)
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        csv_path = tmp_path / "mappings.csv"
        table.save_to_csv(csv_path)

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Verify timestamp is ISO format
        timestamp = rows[0]["generated_at"]
        assert "T" in timestamp  # ISO format has T separator
        assert len(timestamp) > 10  # Has time component

    def test_csv_export_identifier_types(self, tmp_path):
        """CSV export preserves identifier types."""
        table = MappingTable(_naming_scheme=NamingScheme.NUMERIC)

        # Add different types
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        table.get_or_create("MAIN-PROGRAM", IdentifierType.PROGRAM_NAME)
        table.get_or_create("PROCESS-SECTION", IdentifierType.SECTION_NAME)
        table.get_or_create("PARA-100", IdentifierType.PARAGRAPH_NAME)

        csv_path = tmp_path / "mappings.csv"
        table.save_to_csv(csv_path)

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        id_types = {row["id_type"] for row in rows}
        assert "DATA_NAME" in id_types
        assert "PROGRAM_NAME" in id_types
        assert "SECTION_NAME" in id_types
        assert "PARAGRAPH_NAME" in id_types

    def test_csv_export_occurrence_count(self, tmp_path):
        """CSV export includes occurrence count."""
        table = MappingTable(_naming_scheme=NamingScheme.NUMERIC)

        # Add same identifier multiple times to increment count
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        csv_path = tmp_path / "mappings.csv"
        table.save_to_csv(csv_path)

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["occurrence_count"] == "3"

    def test_csv_export_creates_parent_directories(self, tmp_path):
        """CSV export creates parent directories if needed."""
        table = MappingTable(_naming_scheme=NamingScheme.NUMERIC)
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        # Path with nested directories
        csv_path = tmp_path / "subdir" / "nested" / "mappings.csv"
        table.save_to_csv(csv_path)

        assert csv_path.exists()

    def test_csv_export_empty_table(self, tmp_path):
        """CSV export works with empty table."""
        table = MappingTable(_naming_scheme=NamingScheme.NUMERIC)

        csv_path = tmp_path / "mappings.csv"
        table.save_to_csv(csv_path)

        # File should exist with only header
        assert csv_path.exists()

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 1  # Only header row
        assert rows[0][0] == "original_name"  # First column header

    def test_csv_export_utf8_encoding(self, tmp_path):
        """CSV export uses UTF-8 encoding."""
        table = MappingTable(_naming_scheme=NamingScheme.NUMERIC)
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)

        csv_path = tmp_path / "mappings.csv"
        table.save_to_csv(csv_path)

        # Verify file can be read as UTF-8
        content = csv_path.read_text(encoding="utf-8")
        assert "original_name" in content

    def test_csv_and_json_contain_same_mappings(self, tmp_path):
        """CSV and JSON exports contain equivalent data."""
        table = MappingTable(_naming_scheme=NamingScheme.NUMERIC)

        # Add some mappings
        table.get_or_create("WS-FIELD", IdentifierType.DATA_NAME)
        table.get_or_create("CUSTOMER-NAME", IdentifierType.DATA_NAME)
        table.get_or_create("MAIN-PROGRAM", IdentifierType.PROGRAM_NAME)

        # Save both formats
        json_path = tmp_path / "mappings.json"
        csv_path = tmp_path / "mappings.csv"
        table.save_to_file(json_path)
        table.save_to_csv(csv_path)

        # Load JSON
        import json

        with open(json_path) as f:
            json_data = json.load(f)

        # Load CSV
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            csv_rows = list(reader)

        # Compare number of mappings
        assert len(json_data["mappings"]) == len(csv_rows)

        # Compare original names
        json_names = {m["original_name"] for m in json_data["mappings"]}
        csv_names = {r["original_name"] for r in csv_rows}
        assert json_names == csv_names

        # Compare anonymized names
        json_anon = {m["anonymized_name"] for m in json_data["mappings"]}
        csv_anon = {r["anonymized_name"] for r in csv_rows}
        assert json_anon == csv_anon
