"""Tests for COBOL parser module."""


from cobol_data_structure import (
    CobolParser,
    FieldType,
    parse_string,
)


class TestParseSimpleRecord:
    """Tests for parsing simple records."""

    def test_parse_basic_record(self, simple_record_cobol: str) -> None:
        """Test parsing a basic record."""
        record = parse_string(simple_record_cobol)

        assert record is not None
        assert record.name == "CUSTOMER-RECORD"
        assert record.root is not None
        assert len(record.root.children) == 3

    def test_field_names(self, simple_record_cobol: str) -> None:
        """Test field names are extracted correctly."""
        record = parse_string(simple_record_cobol)
        assert record is not None

        field_names = [f.name for f in record.root.children]
        assert "CUSTOMER-ID" in field_names
        assert "CUSTOMER-NAME" in field_names
        assert "BALANCE" in field_names

    def test_pic_types(self, simple_record_cobol: str) -> None:
        """Test PIC types are determined correctly."""
        record = parse_string(simple_record_cobol)
        assert record is not None

        fields = {f.name: f for f in record.root.children}

        assert fields["CUSTOMER-ID"].pic.field_type == FieldType.NUMERIC
        assert fields["CUSTOMER-NAME"].pic.field_type == FieldType.ALPHANUMERIC
        assert fields["BALANCE"].pic.field_type == FieldType.SIGNED_NUMERIC

    def test_pic_lengths(self, simple_record_cobol: str) -> None:
        """Test PIC lengths are calculated correctly."""
        record = parse_string(simple_record_cobol)
        assert record is not None

        fields = {f.name: f for f in record.root.children}

        assert fields["CUSTOMER-ID"].pic.display_length == 8
        assert fields["CUSTOMER-NAME"].pic.display_length == 30
        # S9(7)V99 = 1 sign + 7 digits + 2 decimals = 10
        assert fields["BALANCE"].pic.display_length == 10
        assert fields["BALANCE"].pic.decimal_positions == 2

    def test_record_total_length(self, simple_record_cobol: str) -> None:
        """Test total record length calculation."""
        record = parse_string(simple_record_cobol)
        assert record is not None

        # 8 + 30 + 10 (S9(7)V99 with sign) = 48
        assert record.total_length == 48


class TestParseNestedRecord:
    """Tests for parsing nested records."""

    def test_parse_nested_structure(self, nested_record_cobol: str) -> None:
        """Test parsing nested groups."""
        record = parse_string(nested_record_cobol)

        assert record is not None
        assert record.name == "EMPLOYEE-RECORD"
        assert len(record.root.children) == 3

    def test_nested_group_children(self, nested_record_cobol: str) -> None:
        """Test nested group has correct children."""
        record = parse_string(nested_record_cobol)
        assert record is not None

        emp_name = record.find_field("EMP-NAME")
        assert emp_name is not None
        assert len(emp_name.children) == 2

        child_names = [c.name for c in emp_name.children]
        assert "FIRST-NAME" in child_names
        assert "LAST-NAME" in child_names

    def test_nested_offsets(self, nested_record_cobol: str) -> None:
        """Test offset calculation for nested fields."""
        record = parse_string(nested_record_cobol)
        assert record is not None

        # EMP-ID: offset 0, length 6
        emp_id = record.find_field("EMP-ID")
        assert emp_id.offset == 0
        assert emp_id.storage_length == 6

        # FIRST-NAME: offset 6, length 15
        first_name = record.find_field("FIRST-NAME")
        assert first_name.offset == 6
        assert first_name.storage_length == 15

        # LAST-NAME: offset 21, length 20
        last_name = record.find_field("LAST-NAME")
        assert last_name.offset == 21
        assert last_name.storage_length == 20

    def test_group_is_not_elementary(self, nested_record_cobol: str) -> None:
        """Test group fields are correctly identified."""
        record = parse_string(nested_record_cobol)
        assert record is not None

        emp_name = record.find_field("EMP-NAME")
        assert emp_name.is_group is True
        assert emp_name.is_elementary is False

        first_name = record.find_field("FIRST-NAME")
        assert first_name.is_group is False
        assert first_name.is_elementary is True


class TestParseOccurs:
    """Tests for parsing OCCURS clause."""

    def test_occurs_count(self, occurs_record_cobol: str) -> None:
        """Test OCCURS count is extracted."""
        record = parse_string(occurs_record_cobol)
        assert record is not None

        items = record.find_field("ITEMS")
        assert items is not None
        assert items.occurs_count == 5

    def test_occurs_total_length(self, occurs_record_cobol: str) -> None:
        """Test OCCURS affects total length."""
        record = parse_string(occurs_record_cobol)
        assert record is not None

        items = record.find_field("ITEMS")
        # Each item: 10 + 3 + 7 = 20 bytes
        # 5 items = 100 bytes
        assert items.total_length == 100

    def test_record_with_occurs_length(self, occurs_record_cobol: str) -> None:
        """Test total record length with OCCURS."""
        record = parse_string(occurs_record_cobol)
        assert record is not None

        # ORDER-ID (8) + ITEM-COUNT (2) + ITEMS (5 * 20) = 110
        assert record.total_length == 110


class TestParseRedefines:
    """Tests for parsing REDEFINES clause."""

    def test_redefines_name_captured(self, redefines_record_cobol: str) -> None:
        """Test REDEFINES target name is captured."""
        record = parse_string(redefines_record_cobol)
        assert record is not None

        redef_field = record.find_field("RECORD-DATA-NUM")
        assert redef_field is not None
        assert redef_field.redefines_name == "RECORD-DATA"

    def test_redefines_target_resolved(self, redefines_record_cobol: str) -> None:
        """Test REDEFINES target is resolved."""
        record = parse_string(redefines_record_cobol)
        assert record is not None

        redef_field = record.find_field("RECORD-DATA-NUM")
        assert redef_field.redefines_target is not None
        assert redef_field.redefines_target.name == "RECORD-DATA"

    def test_redefines_same_offset(self, redefines_record_cobol: str) -> None:
        """Test REDEFINES field has same offset as target."""
        record = parse_string(redefines_record_cobol)
        assert record is not None

        original = record.find_field("RECORD-DATA")
        redef = record.find_field("RECORD-DATA-NUM")

        assert redef.offset == original.offset


class TestParseFiller:
    """Tests for parsing FILLER fields."""

    def test_filler_auto_naming(self, filler_record_cobol: str) -> None:
        """Test FILLER fields get auto-generated names."""
        record = parse_string(filler_record_cobol)
        assert record is not None

        field_names = [f.name for f in record.root.children]
        assert "FILLER-1" in field_names
        assert "FILLER-2" in field_names

    def test_filler_is_marked(self, filler_record_cobol: str) -> None:
        """Test FILLER fields are marked as filler."""
        record = parse_string(filler_record_cobol)
        assert record is not None

        filler1 = record.find_field("FILLER-1")
        assert filler1 is not None
        assert filler1.is_filler is True

        header = record.find_field("HEADER")
        assert header.is_filler is False

    def test_filler_counts_in_offsets(self, filler_record_cobol: str) -> None:
        """Test FILLER fields affect offset calculations."""
        record = parse_string(filler_record_cobol)
        assert record is not None

        # HEADER (4) + FILLER-1 (2) = 6
        data_field = record.find_field("DATA-FIELD")
        assert data_field.offset == 6


class TestParseEdgeCases:
    """Tests for edge cases in parsing."""

    def test_level_77_standalone(self) -> None:
        """Test level 77 creates standalone record."""
        cobol = "77 COUNTER PIC 9(5)."
        parser = CobolParser()
        records = parser.parse_string(cobol)

        assert len(records) == 1
        assert records[0].name == "COUNTER"
        assert records[0].root.level == 77

    def test_mixed_case(self) -> None:
        """Test case insensitivity."""
        cobol = """
01 my-record.
    03 My-Field pic x(10).
"""
        record = parse_string(cobol)
        assert record is not None
        assert record.name == "MY-RECORD"

        field = record.find_field("MY-FIELD")
        assert field is not None

    def test_no_period_warning(self) -> None:
        """Test warning for missing period."""
        cobol = "01 RECORD\n    03 FIELD PIC X(10)"
        parser = CobolParser()
        parser.parse_string(cobol)

        assert parser.warnings.has_warnings()

    def test_empty_source(self) -> None:
        """Test parsing empty source."""
        record = parse_string("")
        assert record is None

    def test_comment_only(self) -> None:
        """Test parsing source with only comments."""
        cobol = """
* This is a comment
* Another comment
"""
        record = parse_string(cobol)
        assert record is None


class TestFindField:
    """Tests for field finding methods."""

    def test_find_field_at_root(self, nested_record_cobol: str) -> None:
        """Test finding fields at root level."""
        record = parse_string(nested_record_cobol)
        assert record is not None

        field = record.find_field("EMP-ID")
        assert field is not None
        assert field.name == "EMP-ID"

    def test_find_nested_field(self, nested_record_cobol: str) -> None:
        """Test finding deeply nested fields."""
        record = parse_string(nested_record_cobol)
        assert record is not None

        field = record.find_field("FIRST-NAME")
        assert field is not None
        assert field.name == "FIRST-NAME"

    def test_find_field_case_insensitive(self, nested_record_cobol: str) -> None:
        """Test case-insensitive field finding."""
        record = parse_string(nested_record_cobol)
        assert record is not None

        field = record.find_field("emp-id")
        assert field is not None

        field = record.find_field("EMP-ID")
        assert field is not None

    def test_find_nonexistent_field(self, nested_record_cobol: str) -> None:
        """Test finding nonexistent field returns None."""
        record = parse_string(nested_record_cobol)
        assert record is not None

        field = record.find_field("NONEXISTENT")
        assert field is None


class TestGetAllFields:
    """Tests for getting all fields."""

    def test_get_all_fields(self, nested_record_cobol: str) -> None:
        """Test getting all fields as flat list."""
        record = parse_string(nested_record_cobol)
        assert record is not None

        fields = record.get_all_fields()
        names = [f.name for f in fields]

        assert "EMPLOYEE-RECORD" in names
        assert "EMP-ID" in names
        assert "FIRST-NAME" in names
        assert "ZIP" in names
