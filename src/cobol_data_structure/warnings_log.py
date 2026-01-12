"""Warning collection and logging utility.

This module provides utilities for collecting and optionally persisting
warnings that occur during COBOL parsing.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path


class WarningsLog:
    """Collect and optionally persist warnings.

    Attributes:
        warnings: List of warning messages collected
    """

    def __init__(self, output_path: Path | None = None) -> None:
        """Initialize the warnings log.

        Args:
            output_path: Optional path to write warnings to file
        """
        self._warnings: list[str] = []
        self._output_path = output_path
        self._logger = logging.getLogger("cobol_parser")

    def add(self, message: str, line_number: int = 0) -> None:
        """Add a warning message.

        Args:
            message: The warning message
            line_number: Optional line number for context
        """
        if line_number:
            full_message = f"Line {line_number}: {message}"
        else:
            full_message = message

        self._warnings.append(full_message)
        self._logger.warning(full_message)

        if self._output_path:
            self._write_to_file(full_message)

    def _write_to_file(self, message: str) -> None:
        """Write a warning message to the output file.

        Args:
            message: The message to write
        """
        if self._output_path is None:
            return
        with open(self._output_path, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")

    @property
    def warnings(self) -> list[str]:
        """Get a copy of all warnings."""
        return list(self._warnings)

    def has_warnings(self) -> bool:
        """Check if any warnings have been collected."""
        return len(self._warnings) > 0

    def count(self) -> int:
        """Get the number of warnings."""
        return len(self._warnings)

    def clear(self) -> None:
        """Clear all collected warnings."""
        self._warnings.clear()

    def __len__(self) -> int:
        """Return the number of warnings."""
        return len(self._warnings)

    def __iter__(self) -> Iterator[str]:
        """Iterate over warnings."""
        return iter(self._warnings)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"WarningsLog({len(self._warnings)} warnings)"
