"""
COBOL COPY Statement Resolver - Handles COPY statements and dependencies.

This module handles:
- Parsing COPY statements including REPLACING clauses
- Building dependency graphs between files
- Topological sorting for processing order
- Detecting circular dependencies
- Locating copybook files
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cobol_anonymizer.exceptions import (
    CircularDependencyError,
    CopyNotFoundError,
)


@dataclass
class ReplacingPair:
    """
    A single REPLACING pattern pair.

    Attributes:
        pattern: The text to find
        replacement: The replacement text
        is_pseudo_text: True if using ==...== syntax
    """

    pattern: str
    replacement: str
    is_pseudo_text: bool = False

    def __str__(self):
        if self.is_pseudo_text:
            return f"=={self.pattern}== BY =={self.replacement}=="
        return f"{self.pattern} BY {self.replacement}"


@dataclass
class CopyStatement:
    """
    Represents a parsed COPY statement.

    Attributes:
        copybook_name: The name of the copybook to include
        library: Optional library name (from OF clause)
        replacements: List of REPLACING pairs
        line_number: Line where the COPY appears
        source_file: File containing the COPY statement
        raw_text: The original COPY statement text
    """

    copybook_name: str
    library: Optional[str] = None
    replacements: list[ReplacingPair] = field(default_factory=list)
    line_number: int = 0
    source_file: Optional[str] = None
    raw_text: str = ""

    @property
    def has_replacing(self) -> bool:
        """Check if this COPY has REPLACING clauses."""
        return len(self.replacements) > 0


# Regex for parsing COPY statements
# Handles: COPY name [OF library] [REPLACING ...].
COPY_PATTERN = re.compile(
    r"\bCOPY\s+([A-Za-z][A-Za-z0-9\-]*)"  # Copybook name
    r"(?:\s+OF\s+([A-Za-z][A-Za-z0-9\-]*))?"  # Optional OF library
    r"(?:\s+REPLACING\s+(.+?))?"  # Optional REPLACING clause
    r"\s*\.",  # Terminating period
    re.IGNORECASE | re.DOTALL,
)

# Regex for pseudo-text replacement: ==text== BY ==text==
PSEUDO_TEXT_PATTERN = re.compile(r"==([^=]*)==\s+BY\s+==([^=]*)==", re.IGNORECASE)

# Regex for simple replacement: identifier BY identifier
SIMPLE_REPLACING_PATTERN = re.compile(
    r"([A-Za-z][A-Za-z0-9\-]*)\s+BY\s+([A-Za-z][A-Za-z0-9\-]*)", re.IGNORECASE
)


def parse_copy_statement(
    line: str,
    line_number: int = 0,
    source_file: Optional[str] = None,
) -> Optional[CopyStatement]:
    """
    Parse a COPY statement from a line.

    Args:
        line: The source line containing the COPY statement
        line_number: Line number for error reporting
        source_file: Source file name for error reporting

    Returns:
        CopyStatement if found, None otherwise
    """
    match = COPY_PATTERN.search(line)
    if not match:
        return None

    copybook_name = match.group(1)
    library = match.group(2)  # May be None
    replacing_text = match.group(3)  # May be None

    replacements = []
    if replacing_text:
        replacements = parse_replacing_clause(replacing_text)

    return CopyStatement(
        copybook_name=copybook_name,
        library=library,
        replacements=replacements,
        line_number=line_number,
        source_file=source_file,
        raw_text=match.group(0),
    )


def parse_replacing_clause(replacing_text: str) -> list[ReplacingPair]:
    """
    Parse a REPLACING clause to extract replacement pairs.

    Handles both pseudo-text (==...==) and simple identifier replacement.

    Args:
        replacing_text: The text after REPLACING keyword

    Returns:
        List of ReplacingPair objects
    """
    pairs = []

    # First, try to find pseudo-text patterns ==...== BY ==...==
    pseudo_matches = PSEUDO_TEXT_PATTERN.findall(replacing_text)
    for pattern, replacement in pseudo_matches:
        pairs.append(
            ReplacingPair(
                pattern=pattern.strip(),
                replacement=replacement.strip(),
                is_pseudo_text=True,
            )
        )

    # If no pseudo-text found, try simple identifier replacement
    if not pairs:
        simple_matches = SIMPLE_REPLACING_PATTERN.findall(replacing_text)
        for pattern, replacement in simple_matches:
            pairs.append(
                ReplacingPair(
                    pattern=pattern,
                    replacement=replacement,
                    is_pseudo_text=False,
                )
            )

    return pairs


def find_copy_statements(
    lines: list[str],
    filename: str,
) -> list[CopyStatement]:
    """
    Find all COPY statements in a file's lines.

    Args:
        lines: List of source lines
        filename: Name of the source file

    Returns:
        List of CopyStatement objects
    """
    statements = []

    # Join lines to handle multi-line COPY statements
    full_text = ""
    line_starts = []  # Track where each line starts

    for _i, line in enumerate(lines, 1):
        line_starts.append(len(full_text))
        full_text += line + "\n"

    # Find all COPY statements
    for match in COPY_PATTERN.finditer(full_text):
        # Determine line number from position
        pos = match.start()
        line_num = 1
        for i, start in enumerate(line_starts):
            if start <= pos:
                line_num = i + 1
            else:
                break

        stmt = parse_copy_statement(match.group(0), line_num, filename)
        if stmt:
            statements.append(stmt)

    return statements


def normalize_filename(filename: str) -> str:
    """
    Normalize a filename for consistent lookup.

    Removes extension and converts to uppercase.
    """
    name = filename.upper()
    # Remove common extensions
    for ext in [".CPY", ".COB", ".CBL"]:
        if name.endswith(ext):
            name = name[: -len(ext)]
            break
    return name


@dataclass
class DependencyGraph:
    """
    Manages file dependencies based on COPY statements.

    Provides topological sorting and cycle detection.
    """

    # file -> set of copybooks it depends on
    dependencies: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    # All known files
    all_files: set[str] = field(default_factory=set)
    # Copybook -> files that use it
    reverse_deps: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    # File -> CopyStatements
    copy_statements: dict[str, list[CopyStatement]] = field(
        default_factory=lambda: defaultdict(list)
    )
    # Mapping from normalized name to original filename
    _original_names: dict[str, str] = field(default_factory=dict)

    def _normalize(self, filename: str) -> str:
        """Normalize filename for consistent lookup."""
        normalized = normalize_filename(filename)
        # Track original name
        if normalized not in self._original_names:
            self._original_names[normalized] = filename.upper()
        return normalized

    def add_file(self, filename: str) -> None:
        """Register a file."""
        normalized = self._normalize(filename)
        self.all_files.add(normalized)

    def add_dependency(
        self,
        source_file: str,
        copybook: str,
        statement: Optional[CopyStatement] = None,
    ) -> None:
        """
        Add a dependency: source_file depends on copybook.

        Args:
            source_file: The file containing the COPY statement
            copybook: The copybook being COPYed
            statement: The parsed CopyStatement
        """
        source_norm = self._normalize(source_file)
        copybook_norm = self._normalize(copybook)

        self.all_files.add(source_norm)
        self.all_files.add(copybook_norm)
        self.dependencies[source_norm].add(copybook_norm)
        self.reverse_deps[copybook_norm].add(source_norm)

        if statement:
            self.copy_statements[source_norm].append(statement)

    def get_dependencies(self, filename: str) -> set[str]:
        """Get all direct dependencies of a file."""
        return self.dependencies.get(self._normalize(filename), set())

    def get_dependents(self, filename: str) -> set[str]:
        """Get all files that depend on this file."""
        return self.reverse_deps.get(self._normalize(filename), set())

    def detect_cycles(self) -> Optional[list[str]]:
        """
        Detect circular dependencies.

        Returns:
            List of files forming a cycle, or None if no cycle exists
        """
        # Use DFS coloring: WHITE=unvisited, GRAY=in progress, BLACK=done
        WHITE, GRAY, BLACK = 0, 1, 2
        colors = dict.fromkeys(self.all_files, WHITE)
        path = []

        def dfs(node: str) -> Optional[list[str]]:
            colors[node] = GRAY
            path.append(node)

            for dep in self.dependencies.get(node, set()):
                if colors[dep] == GRAY:
                    # Found cycle - extract it
                    cycle_start = path.index(dep)
                    return path[cycle_start:] + [dep]
                elif colors[dep] == WHITE:
                    result = dfs(dep)
                    if result:
                        return result

            path.pop()
            colors[node] = BLACK
            return None

        for file in self.all_files:
            if colors[file] == WHITE:
                cycle = dfs(file)
                if cycle:
                    return cycle

        return None

    def topological_sort(self) -> list[str]:
        """
        Return files in dependency order (dependencies first).

        Raises:
            CircularDependencyError: If a cycle is detected

        Returns:
            List of filenames in processing order
        """
        # Check for cycles first
        cycle = self.detect_cycles()
        if cycle:
            raise CircularDependencyError(cycle)

        # Kahn's algorithm for topological sort
        in_degree = dict.fromkeys(self.all_files, 0)
        for deps in self.dependencies.values():
            for dep in deps:
                in_degree[dep] = in_degree.get(dep, 0)  # Ensure it exists

        # Actually, we want files with no dependencies to come first
        # So we reverse: files that nothing depends on come last

        # Recalculate: how many files does this file depend on?
        dep_count = {f: len(self.dependencies.get(f, set())) for f in self.all_files}

        result = []
        ready = [f for f in self.all_files if dep_count[f] == 0]

        while ready:
            # Sort for deterministic order
            ready.sort()
            current = ready.pop(0)
            result.append(current)

            # Remove current from dependencies of other files
            for source, deps in list(self.dependencies.items()):
                if current in deps:
                    deps.remove(current)
                    dep_count[source] = len(deps)
                    if dep_count[source] == 0 and source not in result:
                        ready.append(source)

        # If we didn't process all files, there's a cycle
        # (though detect_cycles should have caught this)
        if len(result) != len(self.all_files):
            remaining = [f for f in self.all_files if f not in result]
            raise CircularDependencyError(remaining)

        return result


class CopyResolver:
    """
    Resolves COPY statements and manages copybook locations.

    Usage:
        resolver = CopyResolver(search_paths=[Path("copybooks/")])
        resolver.scan_file(Path("program.cob"))
        order = resolver.get_processing_order()
    """

    def __init__(
        self,
        search_paths: Optional[list[Path]] = None,
        extensions: Optional[list[str]] = None,
    ):
        """
        Initialize the COPY resolver.

        Args:
            search_paths: Directories to search for copybooks
            extensions: File extensions to look for (default: .cpy, .cob, .cbl)
        """
        self.search_paths = search_paths or []
        self.extensions = extensions or [".cpy", ".cob", ".cbl", ""]
        self.graph = DependencyGraph()
        self._copybook_locations: dict[str, Path] = {}
        self._scanned_files: set[str] = set()

    def add_search_path(self, path: Path) -> None:
        """Add a directory to search for copybooks."""
        if path not in self.search_paths:
            self.search_paths.append(path)

    def find_copybook(self, copybook_name: str) -> Optional[Path]:
        """
        Find a copybook file by name.

        Args:
            copybook_name: The copybook name from COPY statement

        Returns:
            Path to the copybook file, or None if not found
        """
        name_upper = copybook_name.upper()

        # Check cache
        if name_upper in self._copybook_locations:
            return self._copybook_locations[name_upper]

        # Search in all paths
        for search_path in self.search_paths:
            for ext in self.extensions:
                # Try exact match
                candidate = search_path / f"{copybook_name}{ext}"
                if candidate.exists():
                    self._copybook_locations[name_upper] = candidate
                    return candidate

                # Try uppercase
                candidate = search_path / f"{copybook_name.upper()}{ext}"
                if candidate.exists():
                    self._copybook_locations[name_upper] = candidate
                    return candidate

                # Try lowercase
                candidate = search_path / f"{copybook_name.lower()}{ext}"
                if candidate.exists():
                    self._copybook_locations[name_upper] = candidate
                    return candidate

        return None

    def scan_file(
        self,
        file_path: Path,
        require_copybooks: bool = False,
    ) -> list[CopyStatement]:
        """
        Scan a file for COPY statements.

        Args:
            file_path: Path to the file to scan
            require_copybooks: If True, raise error for missing copybooks

        Returns:
            List of COPY statements found

        Raises:
            CopyNotFoundError: If copybook not found and require_copybooks is True
        """
        filename = file_path.name.upper()
        if filename in self._scanned_files:
            return self.graph.copy_statements.get(filename, [])

        self._scanned_files.add(filename)
        self.graph.add_file(filename)

        # Read file
        try:
            content = file_path.read_text(encoding="latin-1")
            lines = content.splitlines()
        except OSError:
            return []

        # Find COPY statements
        statements = find_copy_statements(lines, str(file_path))

        for stmt in statements:
            self.graph.add_dependency(filename, stmt.copybook_name, stmt)

            # Try to find and scan the copybook
            copybook_path = self.find_copybook(stmt.copybook_name)
            if copybook_path:
                # Recursively scan the copybook
                self.scan_file(copybook_path, require_copybooks)
            elif require_copybooks:
                raise CopyNotFoundError(
                    stmt.copybook_name,
                    str(file_path),
                    stmt.line_number,
                )

        return statements

    def scan_directory(
        self,
        directory: Path,
        require_copybooks: bool = False,
    ) -> None:
        """
        Scan all COBOL files in a directory.

        Args:
            directory: Directory to scan
            require_copybooks: If True, raise error for missing copybooks
        """
        # Add the directory to search paths
        self.add_search_path(directory)

        # Find all COBOL files
        for ext in [".cob", ".cbl", ".cpy"]:
            for file_path in directory.glob(f"*{ext}"):
                self.scan_file(file_path, require_copybooks)

    def get_processing_order(self) -> list[str]:
        """
        Get files in dependency order for processing.

        Returns:
            List of filenames (dependencies first)
        """
        return self.graph.topological_sort()

    def get_copy_statements(self, filename: str) -> list[CopyStatement]:
        """Get all COPY statements in a file."""
        return self.graph.copy_statements.get(filename.upper(), [])

    def get_all_copy_statements(self) -> dict[str, list[CopyStatement]]:
        """Get all COPY statements organized by file."""
        return dict(self.graph.copy_statements)
