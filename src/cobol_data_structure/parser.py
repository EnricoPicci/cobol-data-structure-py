"""COBOL DATA DIVISION parser.

Parses COBOL data definitions into CobolField structures.
"""

from __future__ import annotations

import re
from math import ceil
from pathlib import Path
from typing import TYPE_CHECKING

from .models import CobolDataStructure, CobolField, Warning
from .preprocessor import preprocess_lines, extract_data_division

if TYPE_CHECKING:
    pass

# =============================================================================
# Regex Patterns (case-insensitive)
# =============================================================================

FLAGS = re.IGNORECASE

# Level number (1-2 digits) and data name
LEVEL_PATTERN = re.compile(
    r"^\s*(\d{1,2})\s+([A-Z][A-Z0-9-]*|FILLER)\s*", FLAGS
)

# PIC clause - handles common patterns including editing characters
PIC_PATTERN = re.compile(
    r"PIC(?:TURE)?(?:\s+IS)?\s*([AXVS9ZP*$+\-,./()0-9B]+)", FLAGS
)

# OCCURS clause (captures count)
OCCURS_PATTERN = re.compile(r"OCCURS\s+(\d+)(?:\s+TIMES?)?", FLAGS)

# REDEFINES clause
REDEFINES_PATTERN = re.compile(r"REDEFINES\s+([A-Z][A-Z0-9-]*)", FLAGS)

# USAGE clause
USAGE_PATTERN = re.compile(
    r"(?:USAGE\s+)?(?:IS\s+)?"
    r"(COMP(?:UTATIONAL)?(?:-[1-5])?|DISPLAY|PACKED-DECIMAL|BINARY)",
    FLAGS,
)

# Standalone COMP without USAGE keyword (common shorthand)
STANDALONE_COMP_PATTERN = re.compile(
    r"\b(COMP(?:-[1-5])?)\b(?!\s*-)", FLAGS
)

# Detection patterns for warnings
COPY_PATTERN = re.compile(r"\bCOPY\s+([A-Z][A-Z0-9-]*)", FLAGS)
DEPENDING_ON_PATTERN = re.compile(r"DEPENDING\s+ON\s+([A-Z][A-Z0-9-]*)", FLAGS)
SIGN_SEPARATE_PATTERN = re.compile(
    r"SIGN\s+(?:IS\s+)?(?:LEADING|TRAILING)\s+SEPARATE", FLAGS
)
VALUE_PATTERN = re.compile(r"\bVALUE(?:\s+IS)?\s+", FLAGS)

# Pattern to extract repeat count from PIC like X(10) or 9(5)
PIC_REPEAT_PATTERN = re.compile(r"([AXVS9ZPB*$+\-,./0])\((\d+)\)", FLAGS)

# =============================================================================
# Size Calculation
# =============================================================================


def calculate_pic_size(pic: str, usage: str | None = None) -> tuple[int, str, bool, int]:
    """Calculate size in bytes from PIC clause.

    Args:
        pic: The PIC clause string (e.g., "X(10)", "S9(5)V99")
        usage: The USAGE clause if any (e.g., "COMP-3")

    Returns:
        Tuple of (size, pic_type, is_signed, decimal_positions)
    """
    if not pic:
        return 0, "", False, 0

    pic_upper = pic.upper()

    # Check for signed
    is_signed = "S" in pic_upper

    # Count decimal positions (digits after V)
    decimal_positions = 0
    if "V" in pic_upper:
        # Count 9s after V
        after_v = pic_upper.split("V", 1)[1]
        decimal_positions = count_pic_positions(after_v)

    # Expand PIC to count total positions
    total_positions = count_pic_positions(pic_upper)

    # Determine primary type
    pic_type = determine_pic_type(pic_upper)

    # Calculate size based on usage
    if usage:
        usage_upper = usage.upper()
        # Normalize COMPUTATIONAL to COMP
        usage_upper = usage_upper.replace("COMPUTATIONAL", "COMP")
        usage_upper = usage_upper.replace("PACKED-DECIMAL", "COMP-3")
        usage_upper = usage_upper.replace("BINARY", "COMP")

        if usage_upper in ("COMP", "COMP-4"):
            size = calculate_comp_size(total_positions)
        elif usage_upper == "COMP-3":
            size = calculate_comp3_size(total_positions)
        elif usage_upper == "COMP-1":
            size = 4  # Single precision float
        elif usage_upper == "COMP-2":
            size = 8  # Double precision float
        else:
            size = total_positions
    else:
        # DISPLAY format (default)
        size = total_positions

    return size, pic_type, is_signed, decimal_positions


def count_pic_positions(pic: str) -> int:
    """Count the number of character positions in a PIC clause.

    Handles both expanded (XXX) and compressed (X(3)) notation.

    Args:
        pic: PIC clause string

    Returns:
        Number of character positions
    """
    # Remove S and V as they don't take storage in DISPLAY
    pic = pic.replace("S", "").replace("V", "")

    count = 0
    i = 0
    while i < len(pic):
        char = pic[i]

        # Check for repeat notation like X(10)
        if i + 1 < len(pic) and pic[i + 1] == "(":
            # Find closing paren
            end = pic.find(")", i + 2)
            if end != -1:
                try:
                    repeat = int(pic[i + 2 : end])
                    count += repeat
                    i = end + 1
                    continue
                except ValueError:
                    pass

        # Single character
        if char in "X9AZPB*$+-,./0":
            count += 1

        i += 1

    return count


def determine_pic_type(pic: str) -> str:
    """Determine the primary data type from PIC clause.

    Args:
        pic: PIC clause string

    Returns:
        Primary type character: 'X', '9', 'A', or 'EDITED'
    """
    pic_clean = pic.replace("S", "").replace("V", "")

    # Check for editing characters
    if any(c in pic_clean for c in "Z*$+-,./B0"):
        return "EDITED"

    # Check for primary type
    if "X" in pic_clean:
        return "X"
    if "A" in pic_clean:
        return "A"
    if "9" in pic_clean:
        return "9"

    return "X"  # Default to alphanumeric


def calculate_comp_size(digits: int) -> int:
    """Calculate COMP/COMP-4 (binary) size.

    Args:
        digits: Number of digits in PIC

    Returns:
        Size in bytes
    """
    if digits <= 4:
        return 2
    if digits <= 9:
        return 4
    return 8


def calculate_comp3_size(digits: int) -> int:
    """Calculate COMP-3 (packed decimal) size.

    Formula: ceil((digits + 1) / 2)

    Args:
        digits: Number of digits in PIC

    Returns:
        Size in bytes
    """
    return ceil((digits + 1) / 2)


# =============================================================================
# Field Parsing
# =============================================================================


class FieldParser:
    """Parser for individual COBOL field definitions."""

    def __init__(self) -> None:
        """Initialize the parser."""
        self.warnings: list[Warning] = []
        self.filler_count: int = 0
        self.line_number: int = 0

    def parse_line(self, line: str, line_number: int = 0) -> CobolField | None:
        """Parse a single COBOL data definition line.

        Args:
            line: Preprocessed line of COBOL source
            line_number: Original line number for error reporting

        Returns:
            CobolField if successfully parsed, None otherwise
        """
        self.line_number = line_number

        # Check for unsupported constructs
        self._check_unsupported(line)

        # Try to match level number and name
        match = LEVEL_PATTERN.match(line)
        if not match:
            return None

        level = int(match.group(1))
        name = match.group(2).upper()

        # Handle FILLER
        is_filler = name == "FILLER"
        if is_filler:
            self.filler_count += 1
            name = f"FILLER-{self.filler_count}"

        # Skip level 66 (RENAMES) and 88 (conditions)
        if level in (66, 88):
            self._add_warning(f"Level {level} not supported, skipping", name)
            return None

        # Parse clauses from remainder of line
        remainder = line[match.end() :]

        # Parse PIC clause
        pic = None
        pic_match = PIC_PATTERN.search(remainder)
        if pic_match:
            pic = pic_match.group(1)

        # Parse OCCURS clause
        occurs = None
        occurs_match = OCCURS_PATTERN.search(remainder)
        if occurs_match:
            occurs = int(occurs_match.group(1))

        # Check for DEPENDING ON
        depending_match = DEPENDING_ON_PATTERN.search(remainder)
        if depending_match:
            self._add_warning(
                f"DEPENDING ON {depending_match.group(1)} not supported, "
                f"using fixed count {occurs}",
                name,
            )

        # Parse REDEFINES clause
        redefines = None
        redefines_match = REDEFINES_PATTERN.search(remainder)
        if redefines_match:
            redefines = redefines_match.group(1).upper()

        # Parse USAGE clause
        usage = None
        usage_match = USAGE_PATTERN.search(remainder)
        if usage_match:
            usage = usage_match.group(1).upper()
        else:
            # Check for standalone COMP
            comp_match = STANDALONE_COMP_PATTERN.search(remainder)
            if comp_match:
                usage = comp_match.group(1).upper()

        # Normalize usage
        if usage:
            usage = usage.replace("COMPUTATIONAL", "COMP")

        # Check for SIGN SEPARATE
        if SIGN_SEPARATE_PATTERN.search(remainder):
            self._add_warning("SIGN SEPARATE detected, size may be off by 1", name)

        # Calculate size and type
        size, pic_type, is_signed, decimal_positions = calculate_pic_size(pic, usage)

        return CobolField(
            name=name,
            level=level,
            pic=pic,
            pic_type=pic_type,
            size=size,
            offset=0,  # Calculated later
            occurs=occurs,
            redefines=redefines,
            usage=usage,
            children=[],
            parent=None,
            is_filler=is_filler,
            is_signed=is_signed,
            decimal_positions=decimal_positions,
        )

    def _check_unsupported(self, line: str) -> None:
        """Check for unsupported constructs and add warnings."""
        # Check for COPY statement
        copy_match = COPY_PATTERN.search(line)
        if copy_match:
            self._add_warning(
                f"COPY {copy_match.group(1)} not supported, skipping",
                severity="error",
            )

    def _add_warning(
        self,
        message: str,
        field_name: str | None = None,
        severity: str = "warning",
    ) -> None:
        """Add a warning to the list."""
        self.warnings.append(
            Warning(
                message=message,
                line_number=self.line_number,
                field_name=field_name,
                severity=severity,
            )
        )


# =============================================================================
# Hierarchy Building
# =============================================================================


def build_hierarchy(fields: list[CobolField]) -> CobolField:
    """Build field hierarchy using level numbers.

    Uses a stack-based approach: for each field, pop until we find a parent
    with a lower level number.

    Args:
        fields: List of parsed CobolField objects in order

    Returns:
        Root field with hierarchy built

    Raises:
        ValueError: If no fields provided
    """
    if not fields:
        raise ValueError("No fields to build hierarchy from")

    root = fields[0]
    stack: list[CobolField] = [root]

    for field in fields[1:]:
        # Pop stack until we find a parent (lower level number)
        while stack and stack[-1].level >= field.level:
            stack.pop()

        if stack:
            parent = stack[-1]
            parent.children.append(field)
            field.parent = parent

        stack.append(field)

    return root


def calculate_offsets(field: CobolField, start_offset: int = 0) -> int:
    """Calculate offsets for all fields recursively.

    Args:
        field: Field to calculate offset for
        start_offset: Starting offset

    Returns:
        Next available offset after this field
    """
    field.offset = start_offset

    if field.children:
        # Group item: children are laid out sequentially
        current_offset = start_offset
        max_redefines_end = start_offset

        for child in field.children:
            if child.redefines:
                # REDEFINES: same offset as redefined field
                # Find the redefined field among siblings
                redefined = None
                for sibling in field.children:
                    if sibling.name.upper() == child.redefines.upper():
                        redefined = sibling
                        break

                if redefined:
                    child_end = calculate_offsets(child, redefined.offset)
                    max_redefines_end = max(max_redefines_end, child_end)
                else:
                    # Redefined field not found, use current offset
                    child_end = calculate_offsets(child, current_offset)
                    max_redefines_end = max(max_redefines_end, child_end)
            else:
                current_offset = calculate_offsets(child, current_offset)

        # Group size is max of regular layout and redefines
        field.size = max(current_offset - start_offset, max_redefines_end - start_offset)

    # Apply OCCURS multiplier for total size
    total_size = field.size
    if field.occurs:
        total_size = field.size * field.occurs

    return start_offset + total_size


def calculate_sizes_recursive(field: CobolField) -> int:
    """Calculate sizes for group items (sum of children).

    Args:
        field: Field to calculate size for

    Returns:
        Calculated size
    """
    if field.children:
        # Group item: size is sum of children (without OCCURS multiplier)
        child_size = sum(calculate_sizes_recursive(child) for child in field.children)

        # Handle REDEFINES: size is max of overlapping fields
        # Group children by whether they redefine something
        base_size = 0
        redefines_sizes: dict[str, int] = {}

        for child in field.children:
            child_total = child.size * (child.occurs or 1)
            if child.redefines:
                key = child.redefines.upper()
                redefines_sizes[key] = max(redefines_sizes.get(key, 0), child_total)
            else:
                base_size += child_total

        # Total is base size (REDEFINES don't add to size)
        field.size = base_size

    return field.size * (field.occurs or 1)


# =============================================================================
# Main Parser
# =============================================================================


def parse_cobol_source(
    source: str,
    name: str = "RECORD",
    source_file: str | None = None,
) -> CobolDataStructure:
    """Parse COBOL source code and build data structure.

    Args:
        source: COBOL source code as string
        name: Name for the root structure (used if not found in source)
        source_file: Optional source file path for error reporting

    Returns:
        CobolDataStructure with parsed fields
    """
    # Preprocess source
    lines = source.splitlines()
    preprocessed = preprocess_lines(lines)
    data_lines = extract_data_division(preprocessed)

    # If no DATA DIVISION found, try parsing all lines
    if not data_lines:
        data_lines = preprocessed

    # Parse individual lines
    field_parser = FieldParser()
    fields: list[CobolField] = []

    for i, line in enumerate(data_lines):
        if not line.strip():
            continue

        field = field_parser.parse_line(line, i + 1)
        if field:
            fields.append(field)

    if not fields:
        # Create empty structure
        root = CobolField(
            name=name,
            level=1,
            children=[],
        )
        return CobolDataStructure(
            name=name,
            root_field=root,
            total_size=0,
            warnings=field_parser.warnings,
            source_file=source_file,
        )

    # Build hierarchy
    root = build_hierarchy(fields)

    # Calculate sizes and offsets
    calculate_offsets(root)

    # Get total size
    total_size = root.size
    if root.occurs:
        total_size = root.size * root.occurs

    # Use root field name as structure name
    structure_name = root.name if root.name != f"FILLER-1" else name

    return CobolDataStructure(
        name=structure_name,
        root_field=root,
        total_size=total_size,
        warnings=field_parser.warnings,
        source_file=source_file,
    )


def parse_cobol_file(
    filepath: str | Path,
    warning_file: str | Path | None = None,
) -> CobolDataStructure:
    """Parse a COBOL file and return the data structure.

    Args:
        filepath: Path to COBOL source file
        warning_file: Optional path to write warnings

    Returns:
        CobolDataStructure with parsed fields
    """
    filepath = Path(filepath)

    with filepath.open("r", encoding="utf-8", errors="replace") as f:
        source = f.read()

    structure = parse_cobol_source(
        source,
        name=filepath.stem.upper(),
        source_file=str(filepath),
    )

    if warning_file and structure.has_warnings():
        structure.write_warnings(warning_file)

    return structure


def parse_cobol_string(
    source: str,
    name: str = "RECORD",
    warning_file: str | Path | None = None,
) -> CobolDataStructure:
    """Parse COBOL source from a string.

    Args:
        source: COBOL source code
        name: Name for the structure
        warning_file: Optional path to write warnings

    Returns:
        CobolDataStructure with parsed fields
    """
    structure = parse_cobol_source(source, name=name)

    if warning_file and structure.has_warnings():
        structure.write_warnings(warning_file)

    return structure
