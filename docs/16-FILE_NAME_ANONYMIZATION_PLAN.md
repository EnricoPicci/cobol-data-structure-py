# File Name Anonymization Implementation Plan

## Overview

This document provides a detailed, step-by-step implementation plan for adding file name anonymization to the COBOL anonymizer. The implementation builds on existing infrastructure that is approximately 70% complete but not wired together.

## Current State Analysis

### Existing Infrastructure

| Component | Status | Location |
|-----------|--------|----------|
| `MappingTable` with PROGRAM_NAME/COPYBOOK_NAME support | Complete | `core/mapper.py` |
| `NameGenerator` with all naming schemes | Complete | `generators/name_generator.py` |
| `OutputWriter.write_file()` with `anonymized_name` param | Complete | `output/writer.py` |
| `Anonymizer._get_anonymized_filename()` method | Exists but unused | `core/anonymizer.py:581-592` |
| `FileStats.anonymized_filename` field | Exists but not populated | `output/report.py` |
| COPY statement parsing | Complete | `cobol/copy_resolver.py` |
| Dependency graph for processing order | Complete | `cobol/copy_resolver.py` |

### What's Missing

1. **Configuration option** to enable/disable file name anonymization
2. **File-to-identifier mapping** linking files to their PROGRAM-ID or copybook name
3. **COPY statement transformation** in source code
4. **Pipeline integration** to actually use file name mappings
5. **Report population** with file name mappings

---

## Phase 1: Configuration

### 1.1 Add Configuration Option

**File**: `src/cobol_anonymizer/config.py`

**Changes**:
```python
@dataclass
class Config:
    # Existing fields...

    # Add new field
    anonymize_file_names: bool = True
```

**Tasks**:
1. Add `anonymize_file_names: bool = True` field to `Config` dataclass
2. Add to JSON serialization/deserialization
3. Add to `_merge_cli_args()` for CLI override

### 1.2 Add CLI Option

**File**: `src/cobol_anonymizer/cli.py`

**Tasks**:
1. Add `--no-file-names` flag to disable file name anonymization
2. Add to argument parser
3. Pass to Config

**Example**:
```python
parser.add_argument(
    "--no-file-names",
    action="store_true",
    help="Disable file name anonymization (keep original file names)"
)
```

### 1.3 Test Cases

```python
# tests/test_config.py
def test_anonymize_file_names_default_true():
    """File name anonymization is enabled by default."""
    config = Config(input_dir=Path("."), output_dir=Path("."))
    assert config.anonymize_file_names is True

def test_anonymize_file_names_cli_override():
    """CLI can disable file name anonymization."""
    # Test --no-file-names flag
```

---

## Phase 2: File-to-Identifier Mapping

### 2.1 Create FileMapper Class

**File**: `src/cobol_anonymizer/core/file_mapper.py` (new file)

**Purpose**: Track the relationship between files and their defining identifiers.

**Implementation**:
```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from enum import Enum

class FileType(str, Enum):
    """Classification of COBOL file types."""
    PROGRAM = "program"
    COPYBOOK = "copybook"
    UNKNOWN = "unknown"

@dataclass
class FileIdentity:
    """Identity information for a COBOL file."""
    original_path: Path
    file_type: FileType
    program_id: Optional[str] = None  # For program files
    copybook_name: Optional[str] = None  # For copybook files
    anonymized_name: Optional[str] = None
    referenced_by: list[str] = field(default_factory=list)

@dataclass
class FileMapper:
    """Maps files to their defining identifiers."""
    _files: dict[str, FileIdentity] = field(default_factory=dict)

    def register_program(self, path: Path, program_id: str) -> None:
        """Register a program file with its PROGRAM-ID."""
        key = self._normalize_key(path)
        self._files[key] = FileIdentity(
            original_path=path,
            file_type=FileType.PROGRAM,
            program_id=program_id
        )

    def register_copybook(self, path: Path, copybook_name: str) -> None:
        """Register a copybook file with its reference name."""
        key = self._normalize_key(path)
        if key in self._files:
            # Update existing entry
            self._files[key].copybook_name = copybook_name
        else:
            self._files[key] = FileIdentity(
                original_path=path,
                file_type=FileType.COPYBOOK,
                copybook_name=copybook_name
            )

    def get_identity(self, path: Path) -> Optional[FileIdentity]:
        """Get the identity for a file."""
        return self._files.get(self._normalize_key(path))

    def _normalize_key(self, path: Path) -> str:
        """Normalize path to case-insensitive key."""
        return str(path.resolve()).upper()
```

### 2.2 Extract PROGRAM-ID During Scanning

**File**: `src/cobol_anonymizer/cobol/copy_resolver.py`

**Tasks**:
1. Add PROGRAM-ID extraction regex
2. Extract PROGRAM-ID when scanning files
3. Store in FileMapper

**Implementation**:
```python
import re

PROGRAM_ID_PATTERN = re.compile(
    r"PROGRAM-ID\s*\.\s*([A-Z0-9][-A-Z0-9]*)",
    re.IGNORECASE
)

def extract_program_id(content: str) -> Optional[str]:
    """Extract PROGRAM-ID from file content."""
    match = PROGRAM_ID_PATTERN.search(content)
    if match:
        return match.group(1).upper()
    return None
```

### 2.3 Integrate FileMapper into Anonymizer

**File**: `src/cobol_anonymizer/core/anonymizer.py`

**Tasks**:
1. Create FileMapper instance in Anonymizer.__init__()
2. Populate during discover_files() phase
3. Use for file name generation

**Changes**:
```python
def __init__(self, config: Config):
    # Existing initialization...
    self.file_mapper = FileMapper()

def discover_files(self) -> list[Path]:
    # Existing discovery logic...

    # Add: Register file identities
    for file_path in discovered_files:
        content = file_path.read_text()
        program_id = extract_program_id(content)
        if program_id:
            self.file_mapper.register_program(file_path, program_id)

    # Register copybooks from COPY graph
    for copybook_name, file_path in self.copy_resolver.copybook_locations.items():
        self.file_mapper.register_copybook(file_path, copybook_name)
```

### 2.4 Test Cases

```python
# tests/test_file_mapper.py
def test_register_program():
    """Register program file with PROGRAM-ID."""
    mapper = FileMapper()
    mapper.register_program(Path("TEST.cob"), "TEST-PROGRAM")
    identity = mapper.get_identity(Path("TEST.cob"))
    assert identity.program_id == "TEST-PROGRAM"
    assert identity.file_type == FileType.PROGRAM

def test_register_copybook():
    """Register copybook file with reference name."""
    mapper = FileMapper()
    mapper.register_copybook(Path("COPY.cpy"), "COPY-NAME")
    identity = mapper.get_identity(Path("COPY.cpy"))
    assert identity.copybook_name == "COPY-NAME"
    assert identity.file_type == FileType.COPYBOOK

def test_extract_program_id():
    """Extract PROGRAM-ID from COBOL content."""
    content = """
           IDENTIFICATION DIVISION.
           PROGRAM-ID. MY-PROGRAM.
    """
    assert extract_program_id(content) == "MY-PROGRAM"
```

---

## Phase 3: File Name Mapping Generation

### 3.1 Generate File Name Mappings

**File**: `src/cobol_anonymizer/core/anonymizer.py`

**Tasks**:
1. Update `build_file_mappings()` method (or create new)
2. Use NameGenerator with appropriate identifier type
3. Store anonymized names in FileMapper

**Implementation**:
```python
def build_file_mappings(self) -> None:
    """Generate anonymized file names for all files."""
    if not self.config.anonymize_file_names:
        return

    for identity in self.file_mapper.all_files():
        if identity.file_type == FileType.PROGRAM:
            # Use PROGRAM_NAME type for naming
            anon_name = self.name_generator.generate(
                original_name=identity.program_id,
                id_type=IdentifierType.PROGRAM_NAME,
                target_length=len(identity.program_id)
            )
            identity.anonymized_name = anon_name + identity.original_path.suffix

        elif identity.file_type == FileType.COPYBOOK:
            # Use COPYBOOK_NAME type for naming
            anon_name = self.name_generator.generate(
                original_name=identity.copybook_name,
                id_type=IdentifierType.COPYBOOK_NAME,
                target_length=len(identity.copybook_name)
            )
            identity.anonymized_name = anon_name + ".cpy"
```

### 3.2 Update _get_anonymized_filename()

**File**: `src/cobol_anonymizer/core/anonymizer.py`

The method exists but is unused. Update to use FileMapper:

```python
def _get_anonymized_filename(self, original_path: Path) -> str:
    """Get the anonymized filename for a file."""
    if not self.config.anonymize_file_names:
        return original_path.name

    identity = self.file_mapper.get_identity(original_path)
    if identity and identity.anonymized_name:
        return identity.anonymized_name

    # Fallback: keep original name
    return original_path.name
```

### 3.3 Test Cases

```python
# tests/test_anonymizer.py
def test_build_file_mappings_numeric():
    """File names use numeric naming scheme."""
    config = Config(
        input_dir=Path("."),
        output_dir=Path("."),
        naming_scheme=NamingScheme.NUMERIC
    )
    anonymizer = Anonymizer(config)
    anonymizer.file_mapper.register_program(Path("TEST.cob"), "TEST-PROG")
    anonymizer.build_file_mappings()

    identity = anonymizer.file_mapper.get_identity(Path("TEST.cob"))
    assert identity.anonymized_name == "PG000001.cob"

def test_build_file_mappings_animals():
    """File names use animals naming scheme."""
    config = Config(
        input_dir=Path("."),
        output_dir=Path("."),
        naming_scheme=NamingScheme.ANIMALS
    )
    # Similar test with ANIMALS scheme
```

---

## Phase 4: COPY Statement Transformation

### 4.1 Add COPY Transformation to LineTransformer

**File**: `src/cobol_anonymizer/core/anonymizer.py`

**Tasks**:
1. Detect COPY statements in transform_line()
2. Extract copybook name
3. Replace with anonymized name
4. Handle REPLACING clause

**Implementation**:
```python
import re

COPY_PATTERN = re.compile(
    r"(\bCOPY\s+)([A-Z0-9][-A-Z0-9]*)(\s*\.|\s+OF\s|\s+REPLACING\s)",
    re.IGNORECASE
)

def transform_copy_statement(self, line: str) -> str:
    """Transform COPY statement to use anonymized copybook name."""
    if not self.config.anonymize_file_names:
        return line

    def replace_copybook(match: re.Match) -> str:
        prefix = match.group(1)  # "COPY "
        copybook_name = match.group(2)  # Original name
        suffix = match.group(3)  # "." or " OF " or " REPLACING "

        # Look up anonymized name
        anon_name = self.mapping_table.get_anonymized_name(copybook_name)
        if anon_name:
            return f"{prefix}{anon_name}{suffix}"
        return match.group(0)  # No change if not found

    return COPY_PATTERN.sub(replace_copybook, line)
```

### 4.2 Integrate into transform_line()

**File**: `src/cobol_anonymizer/core/anonymizer.py`

Update the main transformation pipeline:

```python
def transform_line(self, line: COBOLLine) -> str:
    """Transform a single line, applying all anonymization."""
    result = line.raw

    # Existing transformations...
    result = self.transform_identifiers(result)

    # Add COPY statement transformation
    result = self.transform_copy_statement(result)

    return result
```

### 4.3 Handle Multi-line COPY Statements

COPY statements may span multiple lines:

```cobol
           COPY LONG-COPYBOOK-NAME
               REPLACING ==:TAG:== BY ==WS-==.
```

**Strategy**: Track COPY context across lines, transform when complete statement is found.

### 4.4 Test Cases

```python
# tests/test_copy_transformation.py
def test_transform_simple_copy():
    """Transform simple COPY statement."""
    # Setup: COMMON-FIELDS maps to CP000001
    line = "           COPY COMMON-FIELDS."
    result = transformer.transform_copy_statement(line)
    assert result == "           COPY CP000001."

def test_transform_copy_with_library():
    """Transform COPY with OF clause."""
    line = "           COPY COMMON-FIELDS OF MYLIB."
    result = transformer.transform_copy_statement(line)
    assert result == "           COPY CP000001 OF MYLIB."

def test_transform_copy_with_replacing():
    """Transform COPY with REPLACING clause."""
    line = "           COPY TEMPLATE REPLACING ==:TAG:== BY ==WS-==."
    result = transformer.transform_copy_statement(line)
    # Copybook name transformed, REPLACING patterns also if they're identifiers

def test_preserve_copy_formatting():
    """Preserve whitespace and column alignment."""
    # Ensure column positions are maintained
```

---

## Phase 5: Pipeline Integration

### 5.1 Update Main Pipeline

**File**: `src/cobol_anonymizer/main.py`

**Tasks**:
1. Call `build_file_mappings()` after file discovery
2. Pass anonymized file name to `OutputWriter.write_file()`
3. Update progress reporting

**Changes**:
```python
def run(self) -> AnonymizationResult:
    # Phase 1: Discovery
    files = self.anonymizer.discover_files()

    # Phase 2: Build file mappings (NEW)
    self.anonymizer.build_file_mappings()

    # Phase 3: Process each file
    for file_path in files:
        # Existing processing...
        anonymized_lines = self.anonymizer.transform_file(file_path)

        # Get anonymized filename (NEW)
        anon_filename = self.anonymizer._get_anonymized_filename(file_path)

        # Write with anonymized name
        self.writer.write_file(
            source_path=file_path,
            lines=anonymized_lines,
            anonymized_name=anon_filename  # Pass the new name
        )
```

### 5.2 Update OutputWriter Usage

**File**: `src/cobol_anonymizer/output/writer.py`

The writer already supports `anonymized_name` parameter. Verify it:
1. Creates output file with anonymized name
2. Populates `WriteResult.anonymized_name` correctly
3. Handles path construction properly

### 5.3 Test Cases

```python
# tests/test_pipeline.py
def test_pipeline_renames_files():
    """Pipeline creates output files with anonymized names."""
    result = pipeline.run()

    # Check output directory has renamed files
    assert (output_dir / "PG000001.cob").exists()
    assert (output_dir / "CP000001.cpy").exists()
    assert not (output_dir / "ORIGINAL-NAME.cob").exists()

def test_pipeline_updates_copy_statements():
    """COPY statements in output reference renamed files."""
    result = pipeline.run()

    # Read anonymized program file
    content = (output_dir / "PG000001.cob").read_text()
    assert "COPY CP000001." in content
    assert "COPY ORIGINAL-COPYBOOK." not in content
```

---

## Phase 6: Report Updates

### 6.1 Populate FileStats.anonymized_filename

**File**: `src/cobol_anonymizer/output/report.py`

**Tasks**:
1. Set `anonymized_filename` from FileMapper
2. Include file mappings in summary

**Changes**:
```python
def generate_file_stats(
    self,
    original_path: Path,
    file_mapper: FileMapper,
    # ... other params
) -> FileStats:
    identity = file_mapper.get_identity(original_path)
    anon_filename = identity.anonymized_name if identity else original_path.name

    return FileStats(
        filename=original_path.name,
        anonymized_filename=anon_filename,
        # ... other fields
    )
```

### 6.2 Add File Mappings to Report

**File**: `src/cobol_anonymizer/output/report.py`

Add a dedicated section for file name mappings:

```python
@dataclass
class FileMappingEntry:
    """File name mapping entry for report."""
    original_name: str
    anonymized_name: str
    file_type: str  # "program" or "copybook"
    identifier: str  # PROGRAM-ID or copybook reference name

@dataclass
class AnonymizationReport:
    # Existing fields...
    file_mappings: list[FileMappingEntry] = field(default_factory=list)
```

### 6.3 Update JSON/CSV Export

**Tasks**:
1. Include file mappings in JSON output
2. Add file mappings to CSV export
3. Update report format documentation

### 6.4 Test Cases

```python
# tests/test_report.py
def test_report_includes_file_mappings():
    """Report includes file name mappings."""
    report = generate_report(...)
    assert len(report.file_mappings) > 0
    assert report.file_mappings[0].original_name == "ORIGINAL.cob"
    assert report.file_mappings[0].anonymized_name == "PG000001.cob"

def test_file_stats_has_anonymized_filename():
    """FileStats includes anonymized filename."""
    stats = report.file_stats[0]
    assert stats.anonymized_filename == "PG000001.cob"
```

---

## Phase 7: Testing

### 7.1 Unit Tests

| Test File | Coverage |
|-----------|----------|
| `tests/test_file_mapper.py` | FileMapper class, identity registration |
| `tests/test_copy_transformation.py` | COPY statement transformation |
| `tests/test_file_naming.py` | File name generation with all schemes |

### 7.2 Integration Tests

```python
# tests/test_integration_file_names.py
def test_full_anonymization_with_file_names():
    """Complete anonymization including file name changes."""
    # Setup test files
    # Run anonymizer
    # Verify:
    #   - Files renamed correctly
    #   - COPY statements updated
    #   - Code would compile (COPY references valid)
    #   - Report shows mappings

def test_deterministic_file_names():
    """Same input produces same file names."""
    result1 = anonymize(input_dir, seed=42)
    result2 = anonymize(input_dir, seed=42)
    assert result1.file_mappings == result2.file_mappings
```

### 7.3 Edge Case Tests

```python
def test_file_without_program_id():
    """Handle files without PROGRAM-ID declaration."""

def test_orphan_copybook():
    """Handle copybooks not referenced by any COPY statement."""

def test_case_insensitive_copy_matching():
    """COPY MYBOOK matches mybook.cpy."""

def test_nested_copy_dependencies():
    """Copybook that COPYs another copybook."""
```

---

## Implementation Order

### Recommended Sequence

1. **Phase 1: Configuration** - Add config option and CLI flag
2. **Phase 2: FileMapper** - Create file-to-identifier mapping
3. **Phase 3: File Name Generation** - Generate anonymized names
4. **Phase 4: COPY Transformation** - Update COPY statements
5. **Phase 5: Pipeline Integration** - Wire everything together
6. **Phase 6: Report Updates** - Include file mappings in output
7. **Phase 7: Testing** - Comprehensive test coverage

**Note**: Additional anonymization refinements (EXTERNAL item anonymization and string literal anonymization) are documented separately in `16-ANONYMIZATION_REFINEMENTS_PLAN.md`.

### Dependencies

```
Phase 1 (Config)
    ↓
Phase 2 (FileMapper) ──→ Phase 3 (Name Generation)
                              ↓
                        Phase 4 (COPY Transform)
                              ↓
                        Phase 5 (Pipeline)
                              ↓
                        Phase 6 (Report)
                              ↓
                        Phase 7 (Testing)
```

---

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `src/cobol_anonymizer/core/file_mapper.py` | File-to-identifier mapping |
| `tests/test_file_mapper.py` | Unit tests for FileMapper |
| `tests/test_copy_transformation.py` | Unit tests for COPY transformation |
| `tests/test_integration_file_names.py` | Integration tests |

### Modified Files

| File | Changes |
|------|---------|
| `src/cobol_anonymizer/config.py` | Add `anonymize_file_names` option |
| `src/cobol_anonymizer/cli.py` | Add `--no-file-names` flag |
| `src/cobol_anonymizer/core/anonymizer.py` | Integrate FileMapper, COPY transformation |
| `src/cobol_anonymizer/cobol/copy_resolver.py` | Extract PROGRAM-ID during scanning |
| `src/cobol_anonymizer/main.py` | Call file mapping, pass to writer |
| `src/cobol_anonymizer/output/report.py` | Include file mappings |
| `src/cobol_anonymizer/output/writer.py` | Verify anonymized_name handling |

---

## Verification Checklist

After implementation, verify:

- [ ] Config option `anonymize_file_names` works
- [ ] CLI flag `--no-file-names` disables file renaming
- [ ] Program files are renamed based on PROGRAM-ID
- [ ] Copybook files are renamed based on copybook reference
- [ ] COPY statements are updated with new file names
- [ ] All naming schemes (NUMERIC, ANIMALS, etc.) work for files
- [ ] Mapping report includes file name mappings
- [ ] Deterministic: same input produces same output
- [ ] Edge cases handled (no PROGRAM-ID, orphan copybooks)
- [ ] Tests pass with >90% coverage for new code

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| COPY statement patterns missed | Comprehensive regex testing, real-world samples |
| File name conflicts | Counter ensures uniqueness |
| Circular dependencies break renaming | Already detected by existing code |
| Performance with many files | Batch processing, efficient lookups |
| Breaking existing tests | Run full test suite after each phase |
