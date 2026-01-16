"""
COBOL Anonymizer - Core anonymization engine.

This module provides the main anonymization functionality:
- Coordinates all phases (discovery, mapping, transform)
- Processes files in dependency order
- Applies identifier mappings
- Preserves COBOL structure and column alignment
- Validates output
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cobol_anonymizer.cobol.column_handler import (
    COBOLFormat,
    COBOLLine,
    detect_cobol_format,
    parse_file_line,
    parse_file_line_auto,
    parse_line,
    parse_line_auto,
    validate_code_area,
)
from cobol_anonymizer.cobol.copy_resolver import CopyResolver
from cobol_anonymizer.cobol.pic_parser import (
    get_protected_ranges,
    has_external_clause,
    has_redefines_clause,
)
from cobol_anonymizer.core.classifier import (
    ClassifiedIdentifier,
    IdentifierClassifier,
    IdentifierType,
)
from cobol_anonymizer.core.mapper import MappingTable
from cobol_anonymizer.core.tokenizer import (
    Token,
    TokenType,
    tokenize_line,
)
from cobol_anonymizer.core.literal_anonymizer import (
    LiteralAnonymizer,
    select_literal_scheme,
    transform_literals,
)
from cobol_anonymizer.core.utils import is_filler
from cobol_anonymizer.exceptions import ColumnOverflowError
from cobol_anonymizer.generators.comment_generator import (
    CommentTransformer,
)
from cobol_anonymizer.generators.naming_schemes import NamingScheme

# Pre-compiled regex pattern for REDEFINES clause parsing
# Pattern: level_number name REDEFINES target_name
REDEFINES_PATTERN = re.compile(
    r"(\d+)\s+([A-Za-z][A-Za-z0-9\-]*)\s+REDEFINES\s+([A-Za-z][A-Za-z0-9\-]*)", re.IGNORECASE
)


@dataclass
class RedefinesEntry:
    """Tracks a REDEFINES relationship."""

    redefining_name: str
    redefined_name: str
    level_number: int
    line_number: int


@dataclass
class RedefinesTracker:
    """
    Tracks REDEFINES relationships for correct anonymization.

    When we anonymize a data item, any REDEFINES clause that references
    it must also be updated to use the anonymized name.
    """

    # original_name -> list of entries that REDEFINE it
    _relationships: dict[str, list[RedefinesEntry]] = field(default_factory=dict)
    # redefining_name -> redefined_name
    _redefines_map: dict[str, str] = field(default_factory=dict)

    def add_redefines(
        self,
        redefining_name: str,
        redefined_name: str,
        level_number: int,
        line_number: int,
    ) -> None:
        """
        Record a REDEFINES relationship.

        Args:
            redefining_name: The name doing the REDEFINES
            redefined_name: The name being redefined
            level_number: Level number of the redefining item
            line_number: Line where the REDEFINES occurs
        """
        key = redefined_name.upper()
        entry = RedefinesEntry(
            redefining_name=redefining_name,
            redefined_name=redefined_name,
            level_number=level_number,
            line_number=line_number,
        )
        if key not in self._relationships:
            self._relationships[key] = []
        self._relationships[key].append(entry)
        self._redefines_map[redefining_name.upper()] = redefined_name

    def get_redefined_name(self, redefining_name: str) -> Optional[str]:
        """Get the original name that this item REDEFINES."""
        return self._redefines_map.get(redefining_name.upper())

    def get_redefining_items(self, redefined_name: str) -> list[RedefinesEntry]:
        """Get all items that REDEFINE the given name."""
        return self._relationships.get(redefined_name.upper(), [])


@dataclass
class TransformResult:
    """Result of transforming a single line."""

    original_line: str
    transformed_line: str
    line_number: int
    changes_made: list[tuple[str, str]]  # (original, anonymized)
    is_comment: bool = False
    warnings: list[str] = field(default_factory=list)


class LineTransformer:
    """
    Transforms a single COBOL line by applying identifier mappings.

    Preserves:
    - PIC clauses
    - USAGE clauses
    - Reserved words
    - FILLER
    - EXTERNAL items (when preserve_external=True)
    - Column alignment
    """

    def __init__(
        self,
        mapping_table: MappingTable,
        redefines_tracker: Optional[RedefinesTracker] = None,
        comment_transformer: Optional[CommentTransformer] = None,
        preserve_external: bool = False,
        literal_anonymizer: Optional[LiteralAnonymizer] = None,
        anonymize_literals: bool = True,
    ):
        """
        Initialize the transformer.

        Args:
            mapping_table: The mapping table for identifier lookups
            redefines_tracker: Optional tracker for REDEFINES handling
            comment_transformer: Optional transformer for comment anonymization
            preserve_external: If True, keep EXTERNAL item names unchanged
            literal_anonymizer: Optional anonymizer for string literals
            anonymize_literals: Whether to anonymize string literals (default: True)
        """
        self.mapping_table = mapping_table
        self.redefines_tracker = redefines_tracker or RedefinesTracker()
        self.comment_transformer = comment_transformer or CommentTransformer()
        self.preserve_external = preserve_external
        self.literal_anonymizer = literal_anonymizer
        self.anonymize_literals = anonymize_literals

    def transform_line(
        self,
        cobol_line: COBOLLine,
        filename: str = "<unknown>",
    ) -> TransformResult:
        """
        Transform a single COBOL line.

        Args:
            cobol_line: The parsed COBOL line
            filename: Source filename for error reporting

        Returns:
            TransformResult with original and transformed content
        """
        changes = []
        warnings = []

        # Transform comment lines using the comment transformer
        if cobol_line.is_comment:
            transformed_line, comment_result = self.comment_transformer.transform_line(
                cobol_line.raw
            )
            return TransformResult(
                original_line=cobol_line.raw,
                transformed_line=transformed_line,
                line_number=cobol_line.line_number,
                changes_made=comment_result.changes_made,
                is_comment=True,
            )

        # Get the code area
        code_area = cobol_line.code_area

        # Get protected ranges (PIC, USAGE clauses)
        protected_ranges = get_protected_ranges(code_area)

        # Tokenize the code area
        tokens = tokenize_line(code_area, cobol_line.line_number)

        # Check for REDEFINES and track it
        if has_redefines_clause(code_area):
            self._handle_redefines(code_area, cobol_line.line_number)

        # Check for EXTERNAL
        is_external = has_external_clause(code_area)

        # Transform identifier tokens
        for token in tokens:
            if token.type == TokenType.IDENTIFIER:
                # Skip if in protected range
                if self._is_in_protected_range(token.start_pos, protected_ranges):
                    continue

                # Skip FILLER
                if is_filler(token.value):
                    continue

                # Skip if EXTERNAL and we're preserving external items
                if is_external and self.preserve_external:
                    continue

                # Skip system identifiers that are marked as external
                if self.preserve_external and self.mapping_table.is_external(token.value):
                    continue

                # Get or create anonymized name
                anon_name = self.mapping_table.get_anonymized_name(token.value)
                if anon_name and anon_name.upper() != token.value.upper():
                    token.value = anon_name
                    changes.append((token.original_value, anon_name))

        # Transform CALL statement program names (string literals after CALL)
        call_changes = self._transform_call_literals(tokens)
        changes.extend(call_changes)

        # Reconstruct the code area from tokens
        if changes:
            new_code_area = self._reconstruct_code_area(tokens, code_area)
        else:
            new_code_area = code_area

        # Apply literal anonymization if enabled
        if self.anonymize_literals and self.literal_anonymizer:
            new_code_area = transform_literals(new_code_area, self.literal_anonymizer)
            if new_code_area != code_area or changes:
                # Mark as changed if literals were transformed
                if new_code_area != code_area and not changes:
                    changes.append(("literals", "anonymized"))

        if changes:
            # Validate column boundaries
            try:
                # Create a temporary line with the new code area
                temp_line = COBOLLine(
                    raw=cobol_line.raw,
                    line_number=cobol_line.line_number,
                    sequence=cobol_line.sequence,
                    indicator=cobol_line.indicator,
                    area_a=new_code_area[:4].ljust(4),
                    area_b=new_code_area[4:].ljust(61),
                    identification=cobol_line.identification,
                    original_length=cobol_line.original_length,
                    line_ending=cobol_line.line_ending,
                    has_change_tag=cobol_line.has_change_tag,
                )
                validate_code_area(temp_line, filename, new_code_area)
            except ColumnOverflowError as e:
                warnings.append(f"Column overflow at line {cobol_line.line_number}: {e}")

            # Build the new line
            transformed = self._build_transformed_line(cobol_line, new_code_area)
        else:
            transformed = cobol_line.raw

        return TransformResult(
            original_line=cobol_line.raw,
            transformed_line=transformed,
            line_number=cobol_line.line_number,
            changes_made=changes,
            warnings=warnings,
        )

    def _is_in_protected_range(
        self,
        position: int,
        ranges: list[tuple[int, int]],
    ) -> bool:
        """Check if position is in a protected range."""
        for start, end in ranges:
            if start <= position < end:
                return True
        return False

    def _handle_redefines(self, code_area: str, line_number: int) -> None:
        """Extract and track REDEFINES relationship."""
        match = REDEFINES_PATTERN.search(code_area)
        if match:
            level = int(match.group(1))
            redefining = match.group(2)
            redefined = match.group(3)
            self.redefines_tracker.add_redefines(redefining, redefined, level, line_number)

    def _transform_call_literals(self, tokens: list[Token]) -> list[tuple[str, str]]:
        """
        Transform CALL statement program names in string literals.

        COBOL CALL statements reference programs by name in string literals:
            CALL "MYPROGRAM" USING ...

        This method finds the string literal after CALL and replaces the
        program name with its anonymized version if a mapping exists.

        Args:
            tokens: List of tokens from the line

        Returns:
            List of (original, anonymized) change tuples
        """
        changes = []
        found_call = False

        for token in tokens:
            if token.type == TokenType.WHITESPACE:
                continue

            # Look for CALL keyword
            if token.type == TokenType.RESERVED and token.value.upper() == "CALL":
                found_call = True
                continue

            # After CALL, look for string literal containing program name
            if found_call and token.type == TokenType.LITERAL_STRING:
                # Extract program name from string (remove quotes)
                original_literal = token.value
                # Handle both single and double quotes
                if len(original_literal) >= 2:
                    quote_char = original_literal[0]
                    program_name = original_literal[1:-1]  # Remove quotes

                    # Look up the program name in mappings
                    anon_name = self.mapping_table.get_anonymized_name(program_name)
                    if anon_name and anon_name.upper() != program_name.upper():
                        # Replace the token value with anonymized name (keep quotes)
                        token.value = f'{quote_char}{anon_name}{quote_char}'
                        changes.append((original_literal, token.value))

                # Only process the first literal after CALL
                found_call = False
                continue

            # If we found CALL but hit something other than whitespace or string,
            # reset (might be CALL identifier syntax instead of CALL literal)
            if found_call and token.type not in (TokenType.WHITESPACE, TokenType.LITERAL_STRING):
                found_call = False

        return changes

    def _reconstruct_code_area(
        self,
        tokens: list[Token],
        original: str,
    ) -> str:
        """Reconstruct code area from modified tokens."""
        # Sort tokens by position
        sorted_tokens = sorted(tokens, key=lambda t: t.start_pos)

        result = []
        last_end = 0

        for token in sorted_tokens:
            # Fill gap with original content
            if token.start_pos > last_end:
                result.append(original[last_end : token.start_pos])

            # Add token value (possibly modified)
            result.append(token.value)

            # Track the end position based on ORIGINAL value length
            # to handle length changes
            last_end = token.start_pos + len(token.original_value)

        # Add any remaining content
        if last_end < len(original):
            result.append(original[last_end:])

        return "".join(result)

    def _build_transformed_line(
        self,
        original: COBOLLine,
        new_code_area: str,
    ) -> str:
        """Build a complete transformed line."""
        # Handle free-format COBOL differently
        if original.source_format == COBOLFormat.FREE:
            # For free format, the code_area IS the full line content
            # Trim to original length to preserve the line structure
            result = new_code_area.rstrip()
            # Preserve original line length if it was longer (trailing spaces)
            if len(result) < original.original_length:
                result = result.ljust(original.original_length)
            return result

        # Fixed format handling
        # Ensure proper area sizing
        if len(new_code_area) < 65:
            new_code_area = new_code_area.ljust(65)

        # Reconstruct with sequence, indicator, areas, and identification
        full_line = (
            original.sequence
            + original.indicator
            + new_code_area[:4]  # Area A
            + new_code_area[4:65]  # Area B
        )

        # Add identification area if original was that long
        if original.original_length >= 72:
            full_line += original.identification

        # Trim or pad to original length
        if original.original_length < len(full_line):
            full_line = full_line[: original.original_length]
        else:
            full_line = full_line.ljust(original.original_length)

        return full_line


@dataclass
class FileTransformResult:
    """Result of transforming a complete file."""

    filename: str
    original_path: Path
    total_lines: int
    transformed_lines: int
    changes: list[TransformResult]
    warnings: list[str]


class Anonymizer:
    """
    Main COBOL Anonymizer class.

    Coordinates all phases of anonymization:
    1. Discovery - Scan files and build dependency graph
    2. Classification - Identify all identifiers and their types
    3. Mapping - Generate anonymized names
    4. Transformation - Apply mappings to source files
    5. Output - Write anonymized files
    """

    def __init__(
        self,
        source_directory: Optional[Path] = None,
        output_directory: Optional[Path] = None,
        preserve_comments: bool = True,
        naming_scheme: NamingScheme = NamingScheme.CORPORATE,
        preserve_external: bool = False,
        anonymize_literals: bool = True,
        seed: Optional[int] = None,
    ):
        """
        Initialize the anonymizer.

        Args:
            source_directory: Directory containing original files
            output_directory: Directory for anonymized output
            preserve_comments: If True, keep comments (may still anonymize content)
            naming_scheme: The naming scheme for anonymized identifiers
            preserve_external: If True, keep EXTERNAL item names unchanged
            anonymize_literals: If True (default), anonymize string literal contents
            seed: Optional seed for deterministic output
        """
        self.source_directory = source_directory
        self.output_directory = output_directory
        self.preserve_comments = preserve_comments
        self.naming_scheme = naming_scheme
        self.preserve_external = preserve_external
        self.anonymize_literals = anonymize_literals
        self.seed = seed

        self.mapping_table = MappingTable(
            _naming_scheme=naming_scheme,
            _preserve_external=preserve_external,
        )
        self.copy_resolver = CopyResolver()
        self.redefines_tracker = RedefinesTracker()

        # Create literal anonymizer with a different scheme than the main one
        self.literal_anonymizer: Optional[LiteralAnonymizer] = None
        if anonymize_literals:
            literal_scheme = select_literal_scheme(naming_scheme, seed)
            self.literal_anonymizer = LiteralAnonymizer(literal_scheme, seed)

        self._files_processed: set[str] = set()
        self._processing_order: list[str] = []

    def discover_files(self) -> list[Path]:
        """
        Discover all COBOL files and build dependency graph.

        Returns:
            List of files in processing order
        """
        if not self.source_directory:
            return []

        # Add source directory to search paths
        self.copy_resolver.add_search_path(self.source_directory)

        # Scan all files
        self.copy_resolver.scan_directory(self.source_directory)

        # Get processing order
        self._processing_order = self.copy_resolver.get_processing_order()

        # Map normalized names to actual file paths
        files = []
        for name in self._processing_order:
            path = self.copy_resolver.find_copybook(name)
            if path:
                files.append(path)

        return files

    def classify_file(self, file_path: Path) -> list[ClassifiedIdentifier]:
        """
        Classify all identifiers in a file.

        Args:
            file_path: Path to the COBOL file

        Returns:
            List of classified identifiers
        """
        content = file_path.read_text(encoding="latin-1")
        lines = content.splitlines()

        # Detect COBOL format (fixed vs free)
        detected_format = detect_cobol_format(lines)

        classifier = IdentifierClassifier(file_path.name)

        for line_num, line in enumerate(lines, 1):
            # Parse the line using detected format
            parsed = parse_line_auto(line, line_num, detected_format=detected_format)
            is_comment = parsed.is_comment

            # Classify the code area
            classifier.classify_line(parsed.code_area, line_num, is_comment)

        return classifier.get_all_identifiers()

    def build_mappings(self, identifiers: list[ClassifiedIdentifier]) -> None:
        """
        Build mappings for all identifiers.

        Args:
            identifiers: List of classified identifiers
        """
        # Process definitions first
        definitions = [i for i in identifiers if i.is_definition]

        for ident in definitions:
            # Determine if this is an EXTERNAL item (should not be anonymized)
            is_external = ident.is_external or ident.type == IdentifierType.EXTERNAL_NAME
            self.mapping_table.get_or_create(
                ident.name,
                ident.type,
                is_external=is_external,
            )

    def transform_file(self, file_path: Path) -> FileTransformResult:
        """
        Transform a single file.

        Args:
            file_path: Path to the file to transform

        Returns:
            FileTransformResult with all changes
        """
        content = file_path.read_text(encoding="latin-1")
        lines_raw = content.splitlines(keepends=True)

        # Detect COBOL format (fixed vs free)
        # Use lines without keepends for detection
        lines_for_detection = content.splitlines()
        detected_format = detect_cobol_format(lines_for_detection)

        transformer = LineTransformer(
            self.mapping_table,
            self.redefines_tracker,
            preserve_external=self.preserve_external,
            literal_anonymizer=self.literal_anonymizer,
            anonymize_literals=self.anonymize_literals,
        )

        results = []
        warnings = []
        transformed_count = 0

        for line_num, raw_line in enumerate(lines_raw, 1):
            # Parse the raw line using detected format
            parsed = parse_file_line_auto(raw_line, line_num, detected_format)

            # Transform
            result = transformer.transform_line(parsed, file_path.name)
            results.append(result)

            if result.changes_made:
                transformed_count += 1

            warnings.extend(result.warnings)

        return FileTransformResult(
            filename=file_path.name,
            original_path=file_path,
            total_lines=len(lines_raw),
            transformed_lines=transformed_count,
            changes=results,
            warnings=warnings,
        )

    def anonymize_file(
        self,
        file_path: Path,
        output_path: Optional[Path] = None,
    ) -> FileTransformResult:
        """
        Fully anonymize a single file.

        Args:
            file_path: Path to the source file
            output_path: Optional path for output (otherwise uses output_directory)

        Returns:
            FileTransformResult
        """
        # Classify identifiers
        identifiers = self.classify_file(file_path)

        # Build mappings
        self.build_mappings(identifiers)

        # Transform the file
        result = self.transform_file(file_path)

        # Write output if path specified
        if output_path or self.output_directory:
            if output_path:
                output = output_path
            else:
                # Use anonymized filename
                anon_filename = self._get_anonymized_filename(file_path.name)
                output = self.output_directory / anon_filename
            self._write_output(result, output)

        return result

    def anonymize_all(self) -> list[FileTransformResult]:
        """
        Anonymize all discovered files in dependency order.

        Returns:
            List of FileTransformResult for all files
        """
        results = []

        # Discover and order files
        files = self.discover_files()

        # First pass: classify all files to build complete mapping
        all_identifiers = []
        for file_path in files:
            identifiers = self.classify_file(file_path)
            all_identifiers.extend(identifiers)

        # Build mappings from all identifiers
        self.build_mappings(all_identifiers)

        # Second pass: transform all files
        for file_path in files:
            result = self.transform_file(file_path)
            results.append(result)

            # Write output
            if self.output_directory:
                # Get anonymized filename
                anon_filename = self._get_anonymized_filename(file_path.name)
                output_path = self.output_directory / anon_filename
                self._write_output(result, output_path)

        return results

    def _get_anonymized_filename(self, original_name: str) -> str:
        """Get the anonymized version of a filename."""
        # Extract name without extension
        stem = Path(original_name).stem
        suffix = Path(original_name).suffix.lower()

        # Check if we have a mapping for this name
        anon = self.mapping_table.get_anonymized_name(stem)
        if anon:
            return anon + Path(original_name).suffix

        # No existing mapping found - create one based on file type
        # Copybooks (.cpy) get COPYBOOK_NAME type, programs (.cob, .cbl) get PROGRAM_NAME
        if suffix == ".cpy":
            id_type = IdentifierType.COPYBOOK_NAME
        else:
            id_type = IdentifierType.PROGRAM_NAME

        anon = self.mapping_table.get_or_create(stem, id_type)
        return anon + Path(original_name).suffix

    def _write_output(
        self,
        result: FileTransformResult,
        output_path: Path,
    ) -> None:
        """Write transformed content to file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        for transform_result in result.changes:
            lines.append(transform_result.transformed_line)

        # Join lines with newlines
        output_path.write_text("\n".join(lines) + "\n", encoding="latin-1")

    def get_mapping_table(self) -> MappingTable:
        """Get the mapping table."""
        return self.mapping_table

    def save_mappings(self, path: Path) -> None:
        """Save mappings to a JSON file."""
        self.mapping_table.save_to_file(path)

    def save_mappings_csv(self, path: Path) -> None:
        """Save mappings to a CSV file."""
        self.mapping_table.save_to_csv(path)

    def load_mappings(self, path: Path) -> None:
        """Load mappings from a JSON file."""
        self.mapping_table = MappingTable.load_from_file(path)
