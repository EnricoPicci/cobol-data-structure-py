"""
Tests for Phase 6: COPY Statement Handling.

Tests for parsing COPY statements and dependency resolution.
"""

import pytest
from pathlib import Path

from cobol_anonymizer.cobol.copy_resolver import (
    ReplacingPair,
    CopyStatement,
    parse_copy_statement,
    parse_replacing_clause,
    find_copy_statements,
    DependencyGraph,
    CopyResolver,
)
from cobol_anonymizer.exceptions import (
    CopyNotFoundError,
    CircularDependencyError,
)


class TestReplacingPair:
    """Tests for ReplacingPair dataclass."""

    def test_simple_pair(self):
        """Create simple replacement pair."""
        pair = ReplacingPair(
            pattern="WS-OLD",
            replacement="WS-NEW",
            is_pseudo_text=False,
        )
        assert pair.pattern == "WS-OLD"
        assert pair.replacement == "WS-NEW"

    def test_pseudo_text_pair(self):
        """Create pseudo-text replacement pair."""
        pair = ReplacingPair(
            pattern=":TAG:",
            replacement="WS-",
            is_pseudo_text=True,
        )
        assert pair.is_pseudo_text is True

    def test_str_simple(self):
        """String representation for simple pair."""
        pair = ReplacingPair("OLD", "NEW", False)
        assert str(pair) == "OLD BY NEW"

    def test_str_pseudo_text(self):
        """String representation for pseudo-text pair."""
        pair = ReplacingPair(":TAG:", "WS-", True)
        assert "==" in str(pair)


class TestCopyStatement:
    """Tests for CopyStatement dataclass."""

    def test_simple_copy(self):
        """Create simple COPY statement."""
        stmt = CopyStatement(copybook_name="SAMPLE01")
        assert stmt.copybook_name == "SAMPLE01"
        assert stmt.has_replacing is False

    def test_copy_with_replacing(self):
        """Create COPY with REPLACING."""
        stmt = CopyStatement(
            copybook_name="SAMPLE01",
            replacements=[ReplacingPair("OLD", "NEW", False)],
        )
        assert stmt.has_replacing is True

    def test_copy_with_library(self):
        """Create COPY with OF library."""
        stmt = CopyStatement(
            copybook_name="COPYBOOK",
            library="MYLIB",
        )
        assert stmt.library == "MYLIB"


class TestParseCopyStatement:
    """Tests for parsing COPY statements."""

    def test_parse_simple_copy(self):
        """Parse simple COPY statement."""
        line = "COPY SAMPLE01."
        stmt = parse_copy_statement(line)
        assert stmt is not None
        assert stmt.copybook_name == "SAMPLE01"

    def test_parse_copy_with_library(self):
        """Parse COPY with OF clause."""
        line = "COPY COPYBOOK OF MYLIB."
        stmt = parse_copy_statement(line)
        assert stmt is not None
        assert stmt.copybook_name == "COPYBOOK"
        assert stmt.library == "MYLIB"

    def test_parse_copy_with_simple_replacing(self):
        """Parse COPY with simple REPLACING."""
        line = "COPY COPYBOOK REPLACING WS-OLD BY WS-NEW."
        stmt = parse_copy_statement(line)
        assert stmt is not None
        assert len(stmt.replacements) == 1
        assert stmt.replacements[0].pattern == "WS-OLD"
        assert stmt.replacements[0].replacement == "WS-NEW"

    def test_parse_copy_with_pseudo_text(self):
        """Parse COPY with pseudo-text REPLACING."""
        line = "COPY COPYBOOK REPLACING ==:TAG:== BY ==WS-==."
        stmt = parse_copy_statement(line)
        assert stmt is not None
        assert len(stmt.replacements) == 1
        assert stmt.replacements[0].is_pseudo_text is True
        assert stmt.replacements[0].pattern == ":TAG:"

    def test_parse_copy_case_insensitive(self):
        """COPY keyword is case-insensitive."""
        lines = ["copy sample01.", "Copy Sample01.", "COPY SAMPLE01."]
        for line in lines:
            stmt = parse_copy_statement(line)
            assert stmt is not None

    def test_parse_no_copy(self):
        """Return None for non-COPY line."""
        line = "MOVE X TO Y."
        stmt = parse_copy_statement(line)
        assert stmt is None

    def test_parse_copy_preserves_line_number(self):
        """Line number is preserved."""
        line = "COPY SAMPLE01."
        stmt = parse_copy_statement(line, line_number=42)
        assert stmt.line_number == 42


class TestParseReplacingClause:
    """Tests for parsing REPLACING clauses."""

    def test_parse_simple_replacing(self):
        """Parse simple identifier REPLACING."""
        text = "WS-OLD BY WS-NEW"
        pairs = parse_replacing_clause(text)
        assert len(pairs) == 1
        assert pairs[0].pattern == "WS-OLD"
        assert pairs[0].replacement == "WS-NEW"
        assert pairs[0].is_pseudo_text is False

    def test_parse_pseudo_text_replacing(self):
        """Parse pseudo-text REPLACING."""
        text = "==:TAG:== BY ==WS-=="
        pairs = parse_replacing_clause(text)
        assert len(pairs) == 1
        assert pairs[0].is_pseudo_text is True

    def test_parse_multiple_replacing(self):
        """Parse multiple REPLACING pairs."""
        text = "==:A:== BY ==X-== ==:B:== BY ==Y-=="
        pairs = parse_replacing_clause(text)
        assert len(pairs) == 2


class TestFindCopyStatements:
    """Tests for finding COPY statements in files."""

    def test_find_single_copy(self):
        """Find single COPY statement."""
        lines = [
            "       IDENTIFICATION DIVISION.",
            "       COPY SAMPLE01.",
            "       PROCEDURE DIVISION.",
        ]
        stmts = find_copy_statements(lines, "TEST.cob")
        assert len(stmts) == 1
        assert stmts[0].copybook_name == "SAMPLE01"

    def test_find_multiple_copies(self):
        """Find multiple COPY statements."""
        lines = [
            "       COPY COPY01.",
            "       COPY COPY02.",
            "       COPY COPY03.",
        ]
        stmts = find_copy_statements(lines, "TEST.cob")
        assert len(stmts) == 3

    def test_find_no_copies(self):
        """No COPY statements in file."""
        lines = [
            "       MOVE X TO Y.",
            "       DISPLAY 'HELLO'.",
        ]
        stmts = find_copy_statements(lines, "TEST.cob")
        assert len(stmts) == 0


class TestDependencyGraph:
    """Tests for DependencyGraph."""

    def test_add_dependency(self):
        """Add dependencies to graph."""
        graph = DependencyGraph()
        graph.add_dependency("PROG.cob", "COPY1.cpy")
        graph.add_dependency("PROG.cob", "COPY2.cpy")

        deps = graph.get_dependencies("PROG.cob")
        # Filenames are normalized (extensions removed)
        assert "COPY1" in deps
        assert "COPY2" in deps

    def test_get_dependents(self):
        """Get files that depend on a copybook."""
        graph = DependencyGraph()
        graph.add_dependency("PROG1.cob", "SHARED.cpy")
        graph.add_dependency("PROG2.cob", "SHARED.cpy")

        dependents = graph.get_dependents("SHARED.cpy")
        # Filenames are normalized (extensions removed)
        assert "PROG1" in dependents
        assert "PROG2" in dependents

    def test_detect_no_cycle(self):
        """No cycle detected in acyclic graph."""
        graph = DependencyGraph()
        graph.add_dependency("A", "B")
        graph.add_dependency("B", "C")

        cycle = graph.detect_cycles()
        assert cycle is None

    def test_detect_simple_cycle(self):
        """Detect simple circular dependency."""
        graph = DependencyGraph()
        graph.add_dependency("A", "B")
        graph.add_dependency("B", "A")

        cycle = graph.detect_cycles()
        assert cycle is not None
        assert "A" in cycle
        assert "B" in cycle

    def test_detect_complex_cycle(self):
        """Detect cycle in larger graph."""
        graph = DependencyGraph()
        graph.add_dependency("A", "B")
        graph.add_dependency("B", "C")
        graph.add_dependency("C", "A")

        cycle = graph.detect_cycles()
        assert cycle is not None

    def test_topological_sort_simple(self):
        """Topological sort of simple graph."""
        graph = DependencyGraph()
        graph.add_file("PROG.COB")
        graph.add_file("COPY.CPY")
        graph.add_dependency("PROG.COB", "COPY.CPY")

        order = graph.topological_sort()
        # COPY should come before PROG (dependencies first)
        # Names are normalized (no extensions)
        assert order.index("COPY") < order.index("PROG")

    def test_topological_sort_complex(self):
        """Topological sort of complex graph."""
        graph = DependencyGraph()
        graph.add_dependency("A", "B")
        graph.add_dependency("A", "C")
        graph.add_dependency("B", "D")
        graph.add_dependency("C", "D")

        order = graph.topological_sort()
        # D should come before B and C, which should come before A
        assert order.index("D") < order.index("B")
        assert order.index("D") < order.index("C")
        assert order.index("B") < order.index("A")
        assert order.index("C") < order.index("A")

    def test_topological_sort_raises_on_cycle(self):
        """Topological sort raises error on cycle."""
        graph = DependencyGraph()
        graph.add_dependency("A", "B")
        graph.add_dependency("B", "A")

        with pytest.raises(CircularDependencyError):
            graph.topological_sort()


class TestCopyResolver:
    """Tests for CopyResolver class."""

    def test_create_resolver(self):
        """Create a CopyResolver."""
        resolver = CopyResolver()
        assert resolver is not None

    def test_add_search_path(self):
        """Add search path."""
        resolver = CopyResolver()
        resolver.add_search_path(Path("/some/path"))
        assert Path("/some/path") in resolver.search_paths

    def test_find_copybook_in_search_path(self, tmp_path):
        """Find copybook in search path."""
        # Create a copybook file
        copybook = tmp_path / "SAMPLE01.cpy"
        copybook.write_text("01 WS-RECORD.")

        resolver = CopyResolver(search_paths=[tmp_path])
        found = resolver.find_copybook("SAMPLE01")
        assert found is not None
        assert found.exists()

    def test_find_copybook_case_insensitive(self, tmp_path):
        """Copybook search is case-insensitive."""
        copybook = tmp_path / "SAMPLE01.cpy"
        copybook.write_text("01 WS-RECORD.")

        resolver = CopyResolver(search_paths=[tmp_path])
        # Try different cases
        assert resolver.find_copybook("SAMPLE01") is not None
        assert resolver.find_copybook("sample01") is not None

    def test_find_copybook_not_found(self, tmp_path):
        """Return None when copybook not found."""
        resolver = CopyResolver(search_paths=[tmp_path])
        found = resolver.find_copybook("NONEXISTENT")
        assert found is None

    def test_scan_file(self, tmp_path):
        """Scan a file for COPY statements."""
        # Create a program with COPY
        program = tmp_path / "PROG.cob"
        program.write_text("       COPY SAMPLE01.\n       COPY SAMPLE02.")

        resolver = CopyResolver(search_paths=[tmp_path])
        stmts = resolver.scan_file(program)
        assert len(stmts) == 2

    def test_scan_file_recursive(self, tmp_path):
        """Scan recursively follows COPY chain."""
        # Create copybook that COPYs another
        copy1 = tmp_path / "COPY1.cpy"
        copy1.write_text("       01 REC1.\n       COPY COPY2.")

        copy2 = tmp_path / "COPY2.cpy"
        copy2.write_text("          05 FIELD PIC X.")

        program = tmp_path / "PROG.cob"
        program.write_text("       COPY COPY1.")

        resolver = CopyResolver(search_paths=[tmp_path])
        resolver.scan_file(program)

        # All three files should be in the graph
        order = resolver.get_processing_order()
        assert len(order) == 3

    def test_processing_order(self, tmp_path):
        """Get correct processing order."""
        # Create files with dependencies
        copy1 = tmp_path / "COPY1.cpy"
        copy1.write_text("01 REC.")

        program = tmp_path / "PROG.cob"
        program.write_text("       COPY COPY1.")

        resolver = CopyResolver(search_paths=[tmp_path])
        resolver.scan_file(program)

        order = resolver.get_processing_order()
        # COPY1 should come before PROG
        copy_idx = next(i for i, f in enumerate(order) if "COPY1" in f)
        prog_idx = next(i for i, f in enumerate(order) if "PROG" in f)
        assert copy_idx < prog_idx


class TestCopyResolverErrors:
    """Tests for error handling in CopyResolver."""

    def test_missing_copybook_error(self, tmp_path):
        """Raise CopyNotFoundError when copybook missing."""
        program = tmp_path / "PROG.cob"
        program.write_text("       COPY MISSING.")

        resolver = CopyResolver(search_paths=[tmp_path])

        with pytest.raises(CopyNotFoundError) as exc_info:
            resolver.scan_file(program, require_copybooks=True)

        assert exc_info.value.copybook == "MISSING"

    def test_circular_dependency_error(self, tmp_path):
        """Raise CircularDependencyError on cycle."""
        # Create circular dependency
        copy1 = tmp_path / "COPY1.cpy"
        copy1.write_text("       COPY COPY2.")

        copy2 = tmp_path / "COPY2.cpy"
        copy2.write_text("       COPY COPY1.")

        resolver = CopyResolver(search_paths=[tmp_path])
        resolver.scan_file(copy1)

        with pytest.raises(CircularDependencyError):
            resolver.get_processing_order()


class TestRealWorldCopyPatterns:
    """Tests using realistic COPY patterns."""

    def test_itbcpa01_pattern(self):
        """Parse COPY pattern from ITBCPA01."""
        # Example from actual COBOL file
        line = "       COPY ITBCP497 REPLACING ==:XYZ:== BY ==ITB-=="
        stmt = parse_copy_statement(line + ".")
        assert stmt is not None
        assert stmt.copybook_name == "ITBCP497"
        assert len(stmt.replacements) == 1

    def test_multiline_copy(self):
        """Parse multi-line COPY with multiple REPLACING."""
        lines = [
            "       COPY COPYBOOK REPLACING",
            "            ==:A:== BY ==X-==",
            "            ==:B:== BY ==Y-==.",
        ]
        stmts = find_copy_statements(lines, "TEST.cob")
        assert len(stmts) == 1
        assert len(stmts[0].replacements) == 2
