# COBOL Code Anonymizer - Technical Design Document

## 1. Overview

### 1.1 Purpose

This document describes the technical design of a Python-based tool that automatically anonymizes COBOL source code while preserving exact logical equivalence. The tool transforms customer-specific COBOL code into generic, non-identifiable code suitable for public distribution.

### 1.2 Scope

The anonymizer processes:
- COBOL program files (`.cob`, `.cbl`)
- COBOL copybook files (`.cpy`)
- All divisions: IDENTIFICATION, ENVIRONMENT, DATA, and PROCEDURE

### 1.3 Design Goals

| Goal | Description |
|------|-------------|
| **Logical Equivalence** | Anonymized code must behave identically to the original |
| **Cross-File Consistency** | Same identifier maps to same anonymized name across all files |
| **Format Preservation** | Maintain COBOL fixed-column format (columns 1-80) |
| **Deterministic Output** | Same input always produces identical output |
| **Traceability** | Generate mapping report for verification |

---

## 2. Architecture

### 2.1 Architecture Pattern: Token-Based with Pattern Recognition

The tool uses a token-based architecture that processes COBOL source code line-by-line, respecting the fixed-column format while identifying and transforming identifiable elements.

```
┌─────────────────────────────────────────────────────────────────┐
│                        ANONYMIZER PIPELINE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Discovery│───▶│ Mapping  │───▶│Transform │───▶│  Output  │  │
│  │  Phase   │    │Generation│    │  Phase   │    │  Phase   │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │              │               │               │          │
│       ▼              ▼               ▼               ▼          │
│  File scanning   Name creation   Tokenization   Column-aware   │
│  COPY graph      Uniqueness      Apply maps     file writing   │
│  Classification  Persistence     Preserve PIC   Validation     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Why Token-Based?

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Full Parser (AST)** | Perfect semantic accuracy | Requires complete COBOL grammar, complex | Overkill |
| **Token-Based** | Column-aware, good accuracy, maintainable | Requires careful classification | **Selected** |
| **Pure Regex** | Simple, fast | Cannot handle COBOL column structure | Insufficient |

### 2.3 Module Structure

```
src/cobol_anonymizer/
├── __init__.py
├── cli.py                      # Command-line interface (argparse)
├── config.py                   # Configuration dataclass
├── main.py                     # Pipeline orchestration
│
├── core/
│   ├── __init__.py
│   ├── tokenizer.py            # COBOL-aware line tokenization
│   ├── classifier.py           # Token type classification
│   ├── anonymizer.py           # Main anonymization logic
│   └── mapper.py               # Global identifier mapping table
│
├── cobol/
│   ├── __init__.py
│   ├── column_handler.py       # Fixed-format column parsing
│   ├── reserved_words.py       # COBOL reserved word list
│   ├── pic_parser.py           # PIC clause detection
│   └── copy_resolver.py        # COPY statement handling
│
├── generators/
│   ├── __init__.py
│   ├── name_generator.py       # Anonymized name generation
│   └── comment_generator.py    # Comment text replacement
│
└── output/
    ├── __init__.py
    ├── writer.py               # Column-preserving file writer
    └── report.py               # Mapping report generator
```

---

## 3. COBOL Fixed-Format Handling

### 3.1 Column Layout

COBOL uses a fixed-format structure with specific column meanings:

```
Columns  1-6:   Sequence number area (optional line numbers)
Column   7:     Indicator area (* = comment, - = continuation, D = debug)
Columns  8-11:  Area A (division/section/paragraph headers, level numbers)
Columns 12-72:  Area B (statements, clauses, data definitions)
Columns 73-80:  Identification area (optional program ID)
```

### 3.2 Column Parsing Implementation

```python
@dataclass
class COBOLLine:
    """Represents a parsed COBOL source line"""
    raw: str                    # Original line
    line_number: int            # 1-based line number in file
    sequence: str               # Columns 1-6
    indicator: str              # Column 7
    area_a: str                 # Columns 8-11
    area_b: str                 # Columns 12-72
    identification: str         # Columns 73-80

    @property
    def is_comment(self) -> bool:
        return self.indicator == '*'

    @property
    def is_continuation(self) -> bool:
        return self.indicator == '-'

    @property
    def code_area(self) -> str:
        """Combined Area A and Area B (columns 8-72)"""
        return self.area_a + self.area_b

def parse_line(raw: str, line_number: int) -> COBOLLine:
    """Parse a raw line into COBOL column structure"""
    # Pad to 80 characters for consistent parsing
    padded = raw.rstrip('\n\r').ljust(80)

    return COBOLLine(
        raw=raw,
        line_number=line_number,
        sequence=padded[0:6],
        indicator=padded[6] if len(padded) > 6 else ' ',
        area_a=padded[7:11] if len(padded) > 7 else '',
        area_b=padded[11:72] if len(padded) > 11 else '',
        identification=padded[72:80] if len(padded) > 72 else ''
    )
```

### 3.3 Line Reconstruction

```python
def reconstruct_line(line: COBOLLine) -> str:
    """Reconstruct a line preserving exact column positions"""
    result = line.sequence.ljust(6)
    result += line.indicator
    result += line.area_a
    result += line.area_b

    # Only include identification if original had content beyond column 72
    if line.identification.strip():
        result = result.ljust(72) + line.identification

    return result.rstrip()
```

---

## 4. Data Structures

### 4.1 Identifier Types

```python
from enum import Enum, auto

class IdentifierType(Enum):
    """Classification of COBOL identifiers for anonymization"""
    PROGRAM_NAME = auto()       # PROGRAM-ID value
    COPYBOOK_NAME = auto()      # COPY statement reference
    SECTION_NAME = auto()       # SECTION header names
    PARAGRAPH_NAME = auto()     # Paragraph names in PROCEDURE DIVISION
    DATA_NAME = auto()          # Variable names in DATA DIVISION
    CONDITION_NAME = auto()     # 88-level condition names
    FILE_NAME = auto()          # FD/SD file names
    LITERAL_STRING = auto()     # Quoted string literals
    COMMENT_TEXT = auto()       # Comment content
    IDENTIFICATION = auto()     # Columns 73-80 content
    SEQUENCE_NUMBER = auto()    # Columns 1-6 content
```

### 4.2 Mapping Entry

```python
@dataclass
class MappingEntry:
    """Single identifier mapping record"""
    original: str               # Original identifier
    anonymized: str             # Anonymized replacement
    identifier_type: IdentifierType
    first_file: str             # File where first encountered
    first_line: int             # Line number where first encountered
    occurrence_count: int = 1   # Total occurrences across all files

    def to_dict(self) -> dict:
        return {
            'original': self.original,
            'anonymized': self.anonymized,
            'type': self.identifier_type.name,
            'first_seen': f"{self.first_file}:{self.first_line}",
            'occurrences': self.occurrence_count
        }
```

### 4.3 Global Mapping Table

```python
@dataclass
class MappingTable:
    """Cross-file consistent mapping storage"""
    mappings: Dict[str, MappingEntry] = field(default_factory=dict)
    counters: Dict[IdentifierType, int] = field(default_factory=lambda: defaultdict(int))
    reserved_words: Set[str] = field(default_factory=set)

    def get_or_create(self, original: str, id_type: IdentifierType,
                      file: str, line: int) -> str:
        """Get existing mapping or create new one"""
        key = original.upper()  # COBOL is case-insensitive

        if key in self.mappings:
            self.mappings[key].occurrence_count += 1
            return self.mappings[key].anonymized

        # Generate new anonymized name
        self.counters[id_type] += 1
        anonymized = self._generate_name(original, id_type, self.counters[id_type])

        self.mappings[key] = MappingEntry(
            original=original,
            anonymized=anonymized,
            identifier_type=id_type,
            first_file=file,
            first_line=line
        )

        return anonymized

    def _generate_name(self, original: str, id_type: IdentifierType,
                       counter: int) -> str:
        """Generate anonymized name preserving length when possible"""
        prefixes = {
            IdentifierType.PROGRAM_NAME: 'PROG',
            IdentifierType.COPYBOOK_NAME: 'COPY',
            IdentifierType.SECTION_NAME: 'SECT',
            IdentifierType.PARAGRAPH_NAME: 'PARA',
            IdentifierType.DATA_NAME: 'VAR',
            IdentifierType.CONDITION_NAME: 'COND',
            IdentifierType.FILE_NAME: 'FILE',
        }

        prefix = prefixes.get(id_type, 'ID')
        base = f"{prefix}{counter:04d}"

        # Try to match original length with padding
        target_len = len(original)
        if len(base) < target_len:
            # Pad with hyphens (valid COBOL identifier character)
            return base + '-' * (target_len - len(base))

        return base

    def save(self, path: str) -> None:
        """Persist mappings to JSON file"""
        data = {
            'version': '1.0',
            'generated': datetime.now().isoformat(),
            'statistics': {
                'total_mappings': len(self.mappings),
                'by_type': {t.name: c for t, c in self.counters.items()}
            },
            'mappings': [e.to_dict() for e in self.mappings.values()]
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> 'MappingTable':
        """Load existing mappings from JSON file"""
        with open(path) as f:
            data = json.load(f)

        table = cls()
        for entry in data['mappings']:
            table.mappings[entry['original'].upper()] = MappingEntry(
                original=entry['original'],
                anonymized=entry['anonymized'],
                identifier_type=IdentifierType[entry['type']],
                first_file=entry['first_seen'].split(':')[0],
                first_line=int(entry['first_seen'].split(':')[1]),
                occurrence_count=entry['occurrences']
            )
        return table
```

### 4.4 Token Representation

```python
@dataclass
class Token:
    """Represents a single token within the code area"""
    value: str                  # Token text
    token_type: TokenType       # Classification
    start_col: int              # Start column (1-based)
    end_col: int                # End column (1-based)

class TokenType(Enum):
    """Token classification for processing"""
    KEYWORD = auto()            # COBOL reserved word
    IDENTIFIER = auto()         # User-defined name
    LEVEL_NUMBER = auto()       # 01, 05, 77, 88, etc.
    PIC_CLAUSE = auto()         # PIC X(10), PIC 9(5)V99, etc.
    LITERAL_STRING = auto()     # 'text' or "text"
    LITERAL_NUMBER = auto()     # 123, -45.67
    OPERATOR = auto()           # = < > + - * /
    PUNCTUATION = auto()        # . , ; ( )
    WHITESPACE = auto()         # Spaces (preserved)
```

---

## 5. Processing Pipeline

### 5.1 Phase 1: Discovery

```python
class DiscoveryPhase:
    """Scan files and build dependency graph"""

    def execute(self, input_dir: str, extensions: List[str]) -> DiscoveryResult:
        # 1. Find all COBOL files
        files = self._scan_files(input_dir, extensions)

        # 2. Build COPY dependency graph
        copy_graph = self._build_copy_graph(files)

        # 3. Determine processing order (copybooks before programs)
        processing_order = self._topological_sort(copy_graph)

        # 4. Extract all identifiers for pre-registration
        identifiers = self._extract_identifiers(files)

        return DiscoveryResult(
            files=files,
            copy_graph=copy_graph,
            processing_order=processing_order,
            identifiers=identifiers
        )

    def _build_copy_graph(self, files: List[Path]) -> Dict[str, List[str]]:
        """Build graph of COPY dependencies"""
        graph = defaultdict(list)
        copy_pattern = re.compile(r'COPY\s+(\w+)', re.IGNORECASE)

        for file_path in files:
            with open(file_path) as f:
                for line in f:
                    parsed = parse_line(line, 0)
                    if not parsed.is_comment:
                        match = copy_pattern.search(parsed.code_area)
                        if match:
                            graph[file_path.stem].append(match.group(1))

        return dict(graph)
```

### 5.2 Phase 2: Mapping Generation

```python
class MappingPhase:
    """Generate consistent anonymized mappings"""

    def __init__(self, config: Config):
        self.config = config
        self.table = MappingTable()
        self._load_reserved_words()

    def execute(self, discovery: DiscoveryResult) -> MappingTable:
        # Process files in dependency order
        for file_path in discovery.processing_order:
            self._process_file(file_path)

        # Validate no collisions with reserved words
        self._validate_no_collisions()

        return self.table

    def _process_file(self, file_path: Path) -> None:
        """Extract and register identifiers from a file"""
        with open(file_path) as f:
            context = FileContext(file_path)

            for line_num, raw_line in enumerate(f, 1):
                line = parse_line(raw_line, line_num)

                if line.is_comment:
                    continue

                # Update context (current division, section, etc.)
                context.update(line)

                # Extract and register identifiers
                for identifier, id_type in self._extract_from_line(line, context):
                    self.table.get_or_create(
                        identifier, id_type,
                        file_path.name, line_num
                    )
```

### 5.3 Phase 3: Transformation

```python
class TransformPhase:
    """Apply anonymization mappings to source files"""

    def __init__(self, mapping_table: MappingTable, config: Config):
        self.table = mapping_table
        self.config = config

    def execute(self, input_dir: Path, output_dir: Path,
                files: List[Path]) -> TransformResult:
        results = []

        for file_path in files:
            output_path = output_dir / file_path.name
            result = self._transform_file(file_path, output_path)
            results.append(result)

        return TransformResult(files=results)

    def _transform_file(self, input_path: Path, output_path: Path) -> FileResult:
        """Transform a single file"""
        lines_transformed = 0

        with open(input_path) as infile, open(output_path, 'w') as outfile:
            for line_num, raw_line in enumerate(infile, 1):
                line = parse_line(raw_line, line_num)
                transformed = self._transform_line(line)
                outfile.write(reconstruct_line(transformed) + '\n')

                if transformed != line:
                    lines_transformed += 1

        return FileResult(
            input_path=input_path,
            output_path=output_path,
            lines_transformed=lines_transformed
        )

    def _transform_line(self, line: COBOLLine) -> COBOLLine:
        """Transform a single line applying all mappings"""
        if line.is_comment:
            return self._transform_comment(line)

        # Transform code area
        new_code = self._transform_code(line.code_area)

        # Transform identification area if configured
        new_ident = line.identification
        if self.config.anonymize_identification:
            new_ident = self._transform_identification(line.identification)

        return COBOLLine(
            raw=line.raw,
            line_number=line.line_number,
            sequence=line.sequence,
            indicator=line.indicator,
            area_a=new_code[:4],
            area_b=new_code[4:],
            identification=new_ident
        )
```

### 5.4 Phase 4: Output and Validation

```python
class OutputPhase:
    """Write output and validate results"""

    def execute(self, transform_result: TransformResult,
                mapping_table: MappingTable, config: Config) -> None:
        # 1. Validate column format
        if config.validate_columns:
            self._validate_column_format(transform_result)

        # 2. Validate cross-file consistency
        self._validate_consistency(transform_result)

        # 3. Generate mapping report
        if config.generate_report:
            mapping_table.save(config.output_dir / 'mapping_report.json')

        # 4. Generate summary
        self._generate_summary(transform_result, config.output_dir)

    def _validate_column_format(self, result: TransformResult) -> None:
        """Ensure all output files have valid COBOL column format"""
        for file_result in result.files:
            with open(file_result.output_path) as f:
                for line_num, line in enumerate(f, 1):
                    if len(line.rstrip()) > 80:
                        raise ValidationError(
                            f"{file_result.output_path}:{line_num}: "
                            f"Line exceeds 80 columns"
                        )
```

---

## 6. Anonymization Rules

### 6.1 Elements to Anonymize

| Element | Detection Pattern | Anonymization Strategy |
|---------|-------------------|------------------------|
| Program name | `PROGRAM-ID. name` | `PROG0001` |
| Copybook name | `COPY name` | `COPY0001` (+ rename file) |
| Section name | `name SECTION.` | `SECT0001` |
| Paragraph name | `name.` in PROCEDURE | `PARA0001` |
| Data name | Level + name | `VAR0001--` (length-preserved) |
| Condition name | `88 name` | `COND0001-` |
| File name | `FD name` | `FILE0001` |
| String literal | `'text'` or `"text"` | `'AAAA0001'` |
| Comment text | After `*` in col 7 | Generic replacement |

### 6.2 Elements to Preserve

| Element | Reason |
|---------|--------|
| COBOL reserved words | Required for syntax |
| PIC clauses | Define data layout |
| Level numbers | Define data hierarchy |
| FILLER keyword | Standard placeholder |
| Numeric literals | Often define sizes/counts |
| COMP/COMP-3/DISPLAY | Define storage format |
| REDEFINES structure | Must reference valid names |
| VALUE literals | May need anonymization but preserve length |

### 6.3 Special Cases

#### 6.3.1 COPY REPLACING

```cobol
COPY ITBCPA01 REPLACING ==:TAG:== BY ==WS-==.
```

**Handling**: Both the copybook name and the replacement patterns must be anonymized consistently.

#### 6.3.2 88-Level Conditions

```cobol
05 WS-STATUS           PIC X(02).
   88 WS-STATUS-OK     VALUE '00'.
   88 WS-STATUS-ERROR  VALUE '99'.
```

**Handling**: 88-level names should use a prefix related to their parent for readability.

#### 6.3.3 REDEFINES

```cobol
05 WS-DATE            PIC X(08).
05 WS-DATE-R REDEFINES WS-DATE.
   07 WS-DATE-YYYY    PIC 9(04).
   07 WS-DATE-MM      PIC 9(02).
   07 WS-DATE-DD      PIC 9(02).
```

**Handling**: The REDEFINES target must map to the anonymized version of the referenced field.

#### 6.3.4 Qualified Names

```cobol
MOVE WS-FIELD OF WS-GROUP TO OUTPUT-FIELD.
```

**Handling**: Each component of a qualified name must be anonymized independently.

---

## 7. Configuration

```python
@dataclass
class Config:
    """Anonymizer configuration options"""

    # Input/Output paths
    input_dir: Path
    output_dir: Path

    # File selection
    extensions: List[str] = field(default_factory=lambda: ['.cob', '.cbl', '.cpy'])

    # Anonymization scope
    anonymize_program_names: bool = True
    anonymize_copybook_names: bool = True
    anonymize_section_names: bool = True
    anonymize_paragraph_names: bool = True
    anonymize_data_names: bool = True
    anonymize_condition_names: bool = True
    anonymize_file_names: bool = True
    anonymize_literals: bool = True
    anonymize_comments: bool = True
    anonymize_identification: bool = False  # Columns 73-80
    anonymize_sequence: bool = False        # Columns 1-6

    # Generation options
    preserve_name_length: bool = True
    random_seed: Optional[int] = None       # For reproducibility

    # Mapping persistence
    mapping_file: Optional[Path] = None     # Load existing mappings
    save_mapping: bool = True

    # Validation
    validate_columns: bool = True
    validate_consistency: bool = True

    # Output
    generate_report: bool = True
    verbose: bool = False
```

---

## 8. Error Handling

### 8.1 Error Categories

```python
class AnonymizerError(Exception):
    """Base exception for anonymizer errors"""
    pass

class ParseError(AnonymizerError):
    """Error parsing COBOL source"""
    def __init__(self, file: str, line: int, message: str):
        super().__init__(f"{file}:{line}: {message}")

class MappingError(AnonymizerError):
    """Error in mapping generation or application"""
    pass

class ValidationError(AnonymizerError):
    """Output validation failure"""
    pass

class ConfigError(AnonymizerError):
    """Configuration error"""
    pass
```

### 8.2 Recovery Strategies

| Error Type | Strategy |
|------------|----------|
| Parse error | Log warning, preserve original line |
| Mapping collision | Append numeric suffix |
| Reserved word collision | Use alternative prefix |
| Column overflow | Truncate with warning |

---

## 9. Testing Strategy

### 9.1 Unit Tests

| Module | Test Focus |
|--------|------------|
| `column_handler` | Column parsing and reconstruction |
| `tokenizer` | Token extraction and classification |
| `name_generator` | Name generation and uniqueness |
| `mapper` | Mapping consistency and persistence |

### 9.2 Integration Tests

```python
def test_cross_file_consistency():
    """Same identifier maps to same name across files"""

def test_copy_reference_integrity():
    """COPY statements reference correctly renamed copybooks"""

def test_redefines_integrity():
    """REDEFINES clauses reference valid anonymized names"""

def test_deterministic_output():
    """Same input always produces identical output"""
```

### 9.3 Validation Tests

```python
def test_column_format_preserved():
    """All output lines respect 80-column format"""

def test_no_reserved_word_collision():
    """Generated names don't conflict with COBOL reserved words"""

def test_pic_clauses_unchanged():
    """PIC clauses are never modified"""
```

---

## 10. Future Considerations

### 10.1 Potential Enhancements

- **COBOL dialect support**: Handle IBM, Micro Focus, GnuCOBOL variations
- **Syntax validation**: Integrate with COBOL compiler for validation
- **Incremental processing**: Handle updates to already-anonymized code
- **Reverse mapping**: Generate tool to map anonymized back to original (for debugging)

### 10.2 Performance Optimization

- **Parallel processing**: Process independent files concurrently
- **Streaming**: Handle very large files without full memory load
- **Caching**: Cache parsed copybooks for reuse

---

## Appendix A: COBOL Reserved Words

The tool maintains a comprehensive list of COBOL reserved words that must never be used as anonymized identifiers. This includes approximately 400+ keywords from COBOL-85 and COBOL-2002 standards.

## Appendix B: Sample Transformations

### Before Anonymization
```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID.    EQTRHORI.
      *    SISTEMA PORTAFOGLIO RAMI DANNI
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-POLIZZA-DATA.
           05 WS-NUMERO-POLIZZA    PIC X(10).
           05 WS-DATA-EMISSIONE    PIC 9(08).
              88 WS-DATA-VALIDA    VALUE 19000101 THRU 99991231.
       PROCEDURE DIVISION.
       A100-MAIN-PROCESS.
           COPY EDMCA000.
           MOVE WS-NUMERO-POLIZZA TO OUTPUT-FIELD.
```

### After Anonymization
```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID.    PROG0001.
      *    SYSTEM MODULE PROCESSING
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  VAR0001-------.
           05 VAR0002-----------    PIC X(10).
           05 VAR0003-----------    PIC 9(08).
              88 COND0001------    VALUE 19000101 THRU 99991231.
       PROCEDURE DIVISION.
       PARA0001---------.
           COPY COPY0001.
           MOVE VAR0002----------- TO VAR0004------.
```
