"""COBOL DATA DIVISION parser.

This module provides the main parser for extracting data structure
definitions from COBOL source code.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

from . import patterns
from .converters import calculate_comp_length
from .models import (
    CobolField,
    CobolParseError,
    CobolRecord,
    FieldType,
    PicClause,
)
from .warnings_log import WarningsLog


class CobolParser:
    """Parse COBOL DATA DIVISION structures.

    This parser extracts data structure definitions from COBOL source
    code and builds a tree of CobolField objects.
    """

    def __init__(
        self,
        warnings_log: WarningsLog | None = None,
        strict: bool = False,
    ) -> None:
        """Initialize the parser.

        Args:
            warnings_log: Optional WarningsLog instance for collecting warnings
            strict: If True, raise exceptions on parse errors
        """
        self.warnings = warnings_log or WarningsLog()
        self.strict = strict
        self._filler_counter = 0

    def parse_file(self, file_path: Path) -> list[CobolRecord]:
        """Parse a COBOL source file and extract record definitions.

        Args:
            file_path: Path to the COBOL source file

        Returns:
            List of CobolRecord objects
        """
        with open(file_path, encoding="utf-8") as f:
            return self.parse(f)

    def parse_string(self, source: str) -> list[CobolRecord]:
        """Parse COBOL source from a string.

        Args:
            source: COBOL source code string

        Returns:
            List of CobolRecord objects
        """
        from io import StringIO

        return self.parse(StringIO(source))

    def parse(self, source: TextIO) -> list[CobolRecord]:
        """Parse COBOL source from a file-like object.

        Args:
            source: File-like object containing COBOL source

        Returns:
            List of CobolRecord objects
        """
        records: list[CobolRecord] = []
        self._filler_counter = 0

        # Preprocess lines into complete statements
        statements = list(self._preprocess_lines(source))

        # Parse each statement into a field
        fields: list[CobolField] = []
        for line_num, statement in statements:
            try:
                field = self._parse_statement(statement, line_num)
                if field:
                    fields.append(field)
            except CobolParseError as e:
                if self.strict:
                    raise
                self.warnings.add(str(e), line_num)

        # Build hierarchy from flat field list
        records = self._build_hierarchy(fields)

        # Calculate offsets for each record
        for record in records:
            self._calculate_offsets(record)
            self._resolve_redefines(record)

        return records

    def _preprocess_lines(self, source: TextIO) -> Iterator[tuple[int, str]]:
        """Preprocess COBOL lines into complete statements.

        Handles:
        - Sequence numbers (columns 1-6)
        - Comment lines (column 7 asterisk)
        - Continuation lines (column 7 hyphen)
        - Inline comments (*> to end)
        - Statement accumulation until period

        Args:
            source: File-like object containing COBOL source

        Yields:
            Tuples of (line_number, statement)
        """
        current_statement = ""
        statement_start_line = 0

        for line_num, raw_line in enumerate(source, 1):
            line = raw_line.rstrip("\n\r")

            # Skip empty lines
            if not line.strip():
                continue

            # Handle fixed-format COBOL (columns 1-6 are sequence numbers)
            if len(line) >= 7:
                # Check for sequence numbers
                seq_match = patterns.SEQUENCE_PATTERN.match(line)
                if seq_match:
                    line = line[6:]  # Strip sequence numbers

                # Check for comment line (asterisk in column 7 / position 0 after strip)
                if line and line[0] == "*":
                    continue

                # Check for continuation line (hyphen in column 7)
                if line and line[0] == "-":
                    # Continuation: append to previous statement
                    line = line[1:].lstrip()
                    current_statement += " " + line
                    continue

            # For free-format or after stripping sequence numbers
            # Strip any remaining comment indicators at start
            line = line.lstrip()
            if line.startswith("*"):
                continue

            # Strip inline comments
            inline_match = patterns.INLINE_COMMENT_PATTERN.search(line)
            if inline_match:
                line = line[: inline_match.start()].rstrip()

            if not line:
                continue

            # Start new statement or continue existing one
            if not current_statement:
                statement_start_line = line_num
                current_statement = line
            else:
                current_statement += " " + line

            # Check for statement terminator (period)
            if patterns.PERIOD_PATTERN.search(current_statement):
                # Remove trailing period and whitespace
                statement = current_statement.rstrip(". \t")
                yield (statement_start_line, statement)
                current_statement = ""
                statement_start_line = 0

        # Handle any remaining statement without period
        if current_statement.strip():
            self.warnings.add(
                f"Statement without terminating period: {current_statement[:50]}...",
                statement_start_line,
            )
            statement = current_statement.rstrip(". \t")
            yield (statement_start_line, statement)

    def _parse_statement(self, statement: str, line_num: int) -> CobolField | None:
        """Parse a single COBOL statement into a CobolField.

        Args:
            statement: The COBOL statement to parse
            line_num: Line number for error reporting

        Returns:
            CobolField or None if not a field definition
        """
        # Extract level number
        level_match = patterns.LEVEL_PATTERN.match(statement)
        if not level_match:
            return None

        level = int(level_match.group(1))

        # Skip special levels
        if level == 66:
            self.warnings.add("Level 66 (RENAMES) not supported, skipping", line_num)
            return None
        if level == 88:
            # Level 88 condition names - skip silently (not data)
            return None

        # Extract field name
        name = "FILLER"
        is_filler = False

        if patterns.FILLER_PATTERN.match(statement):
            self._filler_counter += 1
            name = f"FILLER-{self._filler_counter}"
            is_filler = True
        else:
            name_match = patterns.NAME_PATTERN.match(statement)
            if name_match:
                name = name_match.group(1).upper()

        # Parse PIC clause
        pic = self._parse_pic_clause(statement, line_num)

        # Parse OCCURS clause
        occurs_count = None
        occurs_match = patterns.OCCURS_PATTERN.search(statement)
        if occurs_match:
            occurs_count = int(occurs_match.group(1))

        # Check for OCCURS DEPENDING ON (use max count)
        depending_match = patterns.OCCURS_DEPENDING_PATTERN.search(statement)
        if depending_match:
            occurs_count = int(depending_match.group(1))
            self.warnings.add(
                f"OCCURS DEPENDING ON treated as fixed size {occurs_count}",
                line_num,
            )

        # Parse REDEFINES clause
        redefines_name = None
        redefines_match = patterns.REDEFINES_PATTERN.search(statement)
        if redefines_match:
            redefines_name = redefines_match.group(1).upper()

        # Create the field
        field = CobolField(
            name=name,
            level=level,
            line_number=line_num,
            pic=pic,
            occurs_count=occurs_count,
            redefines_name=redefines_name,
            is_filler=is_filler,
        )

        # Calculate storage length
        if pic:
            field.storage_length = pic.storage_length
        # Group fields get their length from children later

        return field

    def _parse_pic_clause(self, statement: str, line_num: int) -> PicClause | None:
        """Parse the PIC clause from a statement.

        Args:
            statement: The COBOL statement
            line_num: Line number for error reporting

        Returns:
            PicClause or None if no PIC clause found
        """
        pic_match = patterns.PIC_PATTERN.search(statement)
        if not pic_match:
            return None

        pic_string = pic_match.group(1).upper()

        # Determine field type
        is_signed = bool(patterns.PIC_SIGNED.match(pic_string))

        # Check for alphanumeric
        has_alpha = "X" in pic_string.upper() or "A" in pic_string.upper()
        has_numeric = "9" in pic_string or "Z" in pic_string.upper()

        if has_alpha and not has_numeric:
            field_type = FieldType.ALPHANUMERIC
        elif has_numeric:
            field_type = FieldType.SIGNED_NUMERIC if is_signed else FieldType.NUMERIC
        else:
            field_type = FieldType.UNKNOWN
            self.warnings.add(f"Unknown PIC pattern: {pic_string}", line_num)

        # Calculate lengths
        display_length, decimal_positions = patterns.parse_pic_length(pic_string)

        # Check for COMP usage
        usage = "DISPLAY"
        comp_match = patterns.COMP_PATTERN.search(statement)
        if comp_match:
            usage = patterns.normalize_usage(comp_match.group(1))
            if usage in ("COMP-3", "COMP"):
                field_type = FieldType.COMP_3 if usage == "COMP-3" else FieldType.COMP

        # Also check USAGE clause
        usage_match = patterns.USAGE_PATTERN.search(statement)
        if usage_match:
            usage = patterns.normalize_usage(usage_match.group(1))
            if usage in ("COMP-3", "COMP"):
                field_type = FieldType.COMP_3 if usage == "COMP-3" else FieldType.COMP

        # Create PicClause
        pic = PicClause(
            raw=pic_string,
            field_type=field_type,
            display_length=display_length,
            storage_length=display_length,  # Updated below for COMP
            decimal_positions=decimal_positions,
            is_signed=is_signed,
            usage=usage,
        )

        # Calculate storage length for COMP fields
        if field_type in (FieldType.COMP, FieldType.COMP_3):
            pic.storage_length = calculate_comp_length(pic)

        return pic

    def _build_hierarchy(self, fields: list[CobolField]) -> list[CobolRecord]:
        """Build record hierarchy from flat field list.

        Args:
            fields: List of CobolField objects in order

        Returns:
            List of CobolRecord objects with hierarchy built
        """
        records: list[CobolRecord] = []
        current_record: CobolRecord | None = None
        stack: list[CobolField] = []  # Stack of parent fields

        for field in fields:
            if field.level == 1 or field.level == 77:
                # Start new record
                if current_record:
                    records.append(current_record)

                current_record = CobolRecord(name=field.name)
                current_record.root = field
                stack = [field]

                # Level 77 is standalone (no children)
                if field.level == 77:
                    records.append(current_record)
                    current_record = None
                    stack = []

            elif current_record:
                # Find parent: pop until stack top has lower level
                while stack and stack[-1].level >= field.level:
                    stack.pop()

                if stack:
                    parent = stack[-1]
                    field.parent = parent
                    parent.children.append(field)
                else:
                    # Orphan field - attach to record root
                    self.warnings.add(
                        f"Orphan field {field.name} attached to root",
                        field.line_number,
                    )
                    if current_record.root:
                        field.parent = current_record.root
                        current_record.root.children.append(field)

                stack.append(field)

        # Don't forget the last record
        if current_record:
            records.append(current_record)

        return records

    def _calculate_offsets(self, record: CobolRecord) -> None:
        """Calculate byte offsets for all fields in a record.

        Args:
            record: The CobolRecord to process
        """
        if not record.root:
            return

        def calc(field: CobolField, current_offset: int) -> int:
            """Recursively calculate offsets.

            Returns the total length consumed by this field.
            """
            field.offset = current_offset

            if field.children:
                # Group field: process children
                running_offset = current_offset
                for child in field.children:
                    if child.redefines_name:
                        # REDEFINES handled later in _resolve_redefines
                        child.offset = running_offset  # Temporary
                        calc(child, running_offset)
                        # Don't advance offset for REDEFINES
                    else:
                        child_length = calc(child, running_offset)
                        running_offset += child_length

                field.storage_length = running_offset - current_offset
            else:
                # Elementary field: length already set from PIC
                pass

            # Return total length including OCCURS
            total = field.storage_length
            if field.occurs_count and field.occurs_count > 1:
                total *= field.occurs_count

            return total

        total_length = calc(record.root, 0)
        record.total_length = total_length

    def _resolve_redefines(self, record: CobolRecord) -> None:
        """Resolve REDEFINES references and fix offsets.

        Args:
            record: The CobolRecord to process
        """
        if not record.root:
            return

        # Build name-to-field map
        name_map: dict[str, CobolField] = {}

        def build_map(field: CobolField) -> None:
            name_map[field.name.upper()] = field
            for child in field.children:
                build_map(child)

        build_map(record.root)

        # Resolve REDEFINES and update child offsets
        def resolve(field: CobolField) -> None:
            if field.redefines_name:
                target_name = field.redefines_name.upper()
                target = name_map.get(target_name)

                if target:
                    field.redefines_target = target
                    old_offset = field.offset
                    new_offset = target.offset
                    offset_delta = new_offset - old_offset

                    # Update field's offset and all children's offsets
                    field.offset = new_offset
                    self._adjust_child_offsets(field, offset_delta)
                else:
                    self.warnings.add(
                        f"REDEFINES target not found: {field.redefines_name}",
                        field.line_number,
                    )

            for child in field.children:
                resolve(child)

        resolve(record.root)

    def _adjust_child_offsets(self, field: CobolField, delta: int) -> None:
        """Recursively adjust child offsets by a delta.

        Args:
            field: The parent field
            delta: Offset adjustment to apply
        """
        for child in field.children:
            child.offset += delta
            self._adjust_child_offsets(child, delta)


def parse_copybook(file_path: Path, strict: bool = False) -> CobolRecord | None:
    """Parse a COBOL copybook file.

    Convenience function that returns the first record found.

    Args:
        file_path: Path to the COBOL file
        strict: If True, raise exceptions on parse errors

    Returns:
        The first CobolRecord or None if no records found
    """
    parser = CobolParser(strict=strict)
    records = parser.parse_file(file_path)
    return records[0] if records else None


def parse_string(source: str, strict: bool = False) -> CobolRecord | None:
    """Parse COBOL from a string.

    Convenience function that returns the first record found.

    Args:
        source: COBOL source code string
        strict: If True, raise exceptions on parse errors

    Returns:
        The first CobolRecord or None if no records found
    """
    parser = CobolParser(strict=strict)
    records = parser.parse_string(source)
    return records[0] if records else None
