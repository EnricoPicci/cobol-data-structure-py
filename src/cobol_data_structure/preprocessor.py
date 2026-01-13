"""COBOL source code preprocessor.

Handles:
- Column conventions (1-6 sequence, 7 indicator, 8-72 code, 73-80 identification)
- Comment removal (* in column 7)
- Continuation line joining (- in column 7)
- DATA DIVISION extraction
"""

from __future__ import annotations


def preprocess_lines(lines: list[str]) -> list[str]:
    """Preprocess COBOL source lines.

    Handles fixed-format COBOL:
    - Columns 1-6: Sequence area (ignored)
    - Column 7: Indicator (* = comment, - = continuation, D = debug)
    - Columns 8-72: Code area
    - Columns 73-80: Identification area (ignored)

    Args:
        lines: Raw lines from COBOL source file

    Returns:
        List of preprocessed logical lines (continuations joined)
    """
    result: list[str] = []
    current_line = ""

    for line in lines:
        # Handle short lines (may not have all columns)
        if len(line) < 7:
            # Very short line - might still have content if free-format
            stripped = line.strip()
            if stripped and not stripped.startswith("*"):
                if current_line:
                    result.append(current_line)
                current_line = stripped
            continue

        indicator = line[6]

        # Skip comments (*, /) and debug lines (D, d)
        if indicator in ("*", "/", "D", "d"):
            continue

        # Extract code area (columns 8-72, 0-indexed: 7-71)
        if len(line) > 72:
            code = line[7:72]
        else:
            code = line[7:]
        code = code.rstrip()

        # Handle continuation (- in column 7)
        if indicator == "-":
            # Continuation: append to previous line, strip leading spaces
            current_line += code.lstrip()
        else:
            # New logical line
            if current_line:
                result.append(current_line)
            current_line = code

    # Don't forget the last line
    if current_line:
        result.append(current_line)

    return result


def extract_data_division(lines: list[str]) -> list[str]:
    """Extract only the DATA DIVISION section from preprocessed lines.

    Args:
        lines: Preprocessed COBOL lines

    Returns:
        Lines from DATA DIVISION only (excluding the header)
    """
    in_data_division = False
    result: list[str] = []

    for line in lines:
        line_upper = line.upper().strip()

        # Check for DATA DIVISION start
        if "DATA DIVISION" in line_upper:
            in_data_division = True
            continue

        # Check for next division (end of DATA DIVISION)
        if in_data_division:
            if any(
                div in line_upper
                for div in [
                    "PROCEDURE DIVISION",
                    "ENVIRONMENT DIVISION",
                    "IDENTIFICATION DIVISION",
                ]
            ):
                break

            # Skip section headers within DATA DIVISION
            if any(
                sect in line_upper
                for sect in [
                    "WORKING-STORAGE SECTION",
                    "FILE SECTION",
                    "LINKAGE SECTION",
                    "LOCAL-STORAGE SECTION",
                    "COMMUNICATION SECTION",
                    "REPORT SECTION",
                    "SCREEN SECTION",
                ]
            ):
                continue

            # Skip empty lines
            if line.strip():
                result.append(line)

    return result


def preprocess_source(source: str) -> list[str]:
    """Full preprocessing pipeline for COBOL source.

    Args:
        source: Complete COBOL source code as string

    Returns:
        Preprocessed lines from DATA DIVISION
    """
    lines = source.splitlines()
    preprocessed = preprocess_lines(lines)
    return extract_data_division(preprocessed)


def is_free_format(lines: list[str]) -> bool:
    """Detect if source appears to be free-format COBOL.

    Free-format COBOL (COBOL 2002+) doesn't use fixed columns.

    Args:
        lines: Raw source lines

    Returns:
        True if source appears to be free-format
    """
    # Heuristic: check if lines have content in columns 1-6
    # that looks like code rather than sequence numbers
    for line in lines[:20]:  # Check first 20 lines
        if len(line) > 6:
            prefix = line[:6]
            # If prefix contains non-numeric, non-space chars, likely free-format
            if prefix.strip() and not prefix.strip().isdigit():
                # Check if it looks like a COBOL keyword
                if any(
                    kw in prefix.upper()
                    for kw in ["IDENT", "DATA", "PROCE", "WORKI", "01", "05"]
                ):
                    return True
    return False


def preprocess_free_format(lines: list[str]) -> list[str]:
    """Preprocess free-format COBOL source.

    Args:
        lines: Raw lines from free-format COBOL source

    Returns:
        List of preprocessed lines
    """
    result: list[str] = []
    current_line = ""

    for line in lines:
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("*>"):
            continue

        # Handle continuation (line ending with -)
        # Note: This is a simplified heuristic
        if current_line.endswith("-"):
            current_line = current_line[:-1] + stripped
        else:
            if current_line:
                result.append(current_line)
            current_line = stripped

    if current_line:
        result.append(current_line)

    return result
