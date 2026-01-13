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
| **Syntactic Validity** | Generated identifiers must be valid COBOL names |

### 1.4 COBOL Identifier Constraints

Generated identifiers must comply with COBOL naming rules:
- Maximum 30 characters
- Must start with a letter
- Can contain letters, digits, and hyphens
- **Cannot end with a hyphen**
- **Cannot start with a hyphen**
- Case-insensitive

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
├── exceptions.py               # All exception classes
├── logging_config.py           # Logging configuration
│
├── core/
│   ├── __init__.py
│   ├── tokenizer.py            # COBOL-aware line tokenization
│   ├── classifier.py           # Token type classification
│   ├── anonymizer.py           # Main anonymization logic
│   ├── mapper.py               # Global identifier mapping table
│   └── utils.py                # Utility functions
│
├── cobol/
│   ├── __init__.py
│   ├── column_handler.py       # Fixed-format column parsing
│   ├── reserved_words.py       # COBOL reserved word list
│   ├── pic_parser.py           # PIC clause detection and preservation
│   ├── copy_resolver.py        # COPY statement handling
│   └── level_handler.py        # Level number hierarchy tracking
│
├── generators/
│   ├── __init__.py
│   ├── name_generator.py       # Anonymized name generation
│   └── comment_generator.py    # Comment text replacement
│
└── output/
    ├── __init__.py
    ├── writer.py               # Column-preserving file writer
    ├── validator.py            # Output validation
    └── report.py               # Mapping report generator
```

---

## 3. COBOL Fixed-Format Handling

### 3.1 Column Layout

COBOL uses a fixed-format structure with specific column meanings:

```
Columns  1-6:   Sequence number area (optional line numbers or change tags)
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
    raw: str                    # Original line (unchanged)
    line_number: int            # 1-based line number in file
    sequence: str               # Columns 1-6
    indicator: str              # Column 7 (single character)
    area_a: str                 # Columns 8-11
    area_b: str                 # Columns 12-72
    identification: str         # Columns 73-80
    original_length: int        # Original line length before padding
    line_ending: str            # Original line ending (\n, \r\n, \r)
    has_change_tag: bool        # True if sequence area has non-numeric tag

    @property
    def is_comment(self) -> bool:
        return self.indicator == '*'

    @property
    def is_continuation(self) -> bool:
        return self.indicator == '-'

    @property
    def is_debug(self) -> bool:
        return self.indicator == 'D'

    @property
    def code_area(self) -> str:
        """Combined Area A and Area B (columns 8-72)"""
        return self.area_a + self.area_b

def parse_line(raw: str, line_number: int) -> COBOLLine:
    """Parse a raw line into COBOL column structure"""
    # Detect and preserve line ending
    line_ending = ''
    if raw.endswith('\r\n'):
        line_ending = '\r\n'
    elif raw.endswith('\n'):
        line_ending = '\n'
    elif raw.endswith('\r'):
        line_ending = '\r'

    # Strip line ending for processing
    content = raw.rstrip('\n\r')
    original_length = len(content)

    # Pad to 80 characters for consistent parsing
    padded = content.ljust(80)

    # Detect change tags (non-numeric content in sequence area)
    sequence = padded[0:6]
    has_change_tag = bool(sequence.strip()) and not sequence.strip().isdigit()

    return COBOLLine(
        raw=raw,
        line_number=line_number,
        sequence=sequence,
        indicator=padded[6] if len(padded) > 6 else ' ',
        area_a=padded[7:11] if len(padded) > 7 else '',
        area_b=padded[11:72] if len(padded) > 11 else '',
        identification=padded[72:80] if len(padded) > 72 else '',
        original_length=original_length,
        line_ending=line_ending,
        has_change_tag=has_change_tag
    )
```

### 3.3 Change Tag Handling

Real-world COBOL files often contain change/modification tags in the sequence area:

```cobol
BENIQ  77  FLG-CLAUSOLA-RITAR-VI               PIC X(1).
CDR    07  Q130-IMP-COMM-RIST-ANNUO            PIC S9(12)V9(03)
DM2724 77  FLG-SOMMA-IN-SCADENZA               PIC X(1).
REPLAT*                                        VALUE 'A   ' THRU 'A999',
```

**Handling Strategy**:
- Detect non-numeric content in columns 1-6
- Preserve change tags as-is (configurable: preserve or anonymize)
- Do not treat these as part of the code for tokenization

### 3.4 Line Reconstruction

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

    # Trim to original length to preserve trailing space behavior
    if len(result) > line.original_length and line.original_length > 0:
        result = result[:max(line.original_length, 7)]  # Keep at least indicator

    return result.rstrip() + line.line_ending
```

### 3.5 Column Overflow Validation

```python
MAX_CODE_LENGTH = 65  # Columns 8-72 = 65 characters

def validate_code_area(area_a: str, area_b: str, line_number: int, file: str) -> None:
    """Validate that code area doesn't overflow column 72"""
    total_length = len(area_a) + len(area_b)
    if total_length > MAX_CODE_LENGTH:
        raise ColumnOverflowError(
            f"{file}:{line_number}: Code area exceeds column 72 "
            f"({total_length} > {MAX_CODE_LENGTH} chars)"
        )
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
    INDEX_NAME = auto()         # INDEXED BY names
    LITERAL_STRING = auto()     # Quoted string literals
    COMMENT_TEXT = auto()       # Comment content
    IDENTIFICATION = auto()     # Columns 73-80 content
    SEQUENCE_NUMBER = auto()    # Columns 1-6 content
    EXTERNAL_NAME = auto()      # EXTERNAL data items (DO NOT ANONYMIZE)
```

### 4.2 Supported Level Numbers

The anonymizer supports all COBOL level numbers found in the codebase:

| Level | Purpose |
|-------|---------|
| 01 | Record description, group item |
| 02-49 | Elementary or group items (nested) |
| 66 | RENAMES clause |
| 77 | Independent elementary item |
| 88 | Condition name |

**Observed in codebase**: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 15, 77, 88

### 4.3 Mapping Entry

```python
@dataclass
class MappingEntry:
    """Single identifier mapping record"""
    original: str               # Original identifier (normalized to uppercase)
    anonymized: str             # Anonymized replacement
    identifier_type: IdentifierType
    first_file: str             # File where first encountered
    first_line: int             # Line number where first encountered
    occurrence_count: int = 1   # Total occurrences across all files
    is_external: bool = False   # True if marked EXTERNAL (don't anonymize)
    parent_name: Optional[str] = None  # For 88-levels, tracks parent data name
    scope: Optional[str] = None # Scope context (file or copybook name)

    def to_dict(self) -> dict:
        return {
            'original': self.original,
            'anonymized': self.anonymized,
            'type': self.identifier_type.name,
            'first_seen': f"{self.first_file}:{self.first_line}",
            'occurrences': self.occurrence_count,
            'is_external': self.is_external
        }
```

### 4.4 Global Mapping Table

```python
# COBOL identifier constraints
MAX_IDENTIFIER_LENGTH = 30
MIN_IDENTIFIER_LENGTH = 1

@dataclass
class MappingTable:
    """Cross-file consistent mapping storage"""
    mappings: Dict[str, MappingEntry] = field(default_factory=dict)
    counters: Dict[IdentifierType, int] = field(default_factory=lambda: defaultdict(int))
    reserved_words: Set[str] = field(default_factory=set)
    external_names: Set[str] = field(default_factory=set)  # Names marked EXTERNAL

    def get_or_create(self, original: str, id_type: IdentifierType,
                      file: str, line: int, is_external: bool = False) -> str:
        """Get existing mapping or create new one"""
        key = original.upper()  # COBOL is case-insensitive

        # EXTERNAL names are never anonymized
        if is_external or key in self.external_names:
            self.external_names.add(key)
            return original

        if key in self.mappings:
            self.mappings[key].occurrence_count += 1
            return self.mappings[key].anonymized

        # Generate new anonymized name
        self.counters[id_type] += 1
        anonymized = self._generate_name(original, id_type, self.counters[id_type])

        # Validate generated name
        self._validate_identifier(anonymized)

        self.mappings[key] = MappingEntry(
            original=original.upper(),
            anonymized=anonymized,
            identifier_type=id_type,
            first_file=file,
            first_line=line,
            is_external=is_external
        )

        return anonymized

    def _generate_name(self, original: str, id_type: IdentifierType,
                       counter: int) -> str:
        """Generate anonymized name with valid COBOL syntax"""
        prefixes = {
            IdentifierType.PROGRAM_NAME: 'PG',
            IdentifierType.COPYBOOK_NAME: 'CP',
            IdentifierType.SECTION_NAME: 'SC',
            IdentifierType.PARAGRAPH_NAME: 'PA',
            IdentifierType.DATA_NAME: 'D',
            IdentifierType.CONDITION_NAME: 'C',
            IdentifierType.FILE_NAME: 'FL',
            IdentifierType.INDEX_NAME: 'IX',
        }

        prefix = prefixes.get(id_type, 'ID')
        target_len = min(len(original), MAX_IDENTIFIER_LENGTH)

        # Calculate how many digits we need for the counter
        # Format: PREFIX + COUNTER (zero-padded to fill remaining space)
        available_digits = target_len - len(prefix)

        if available_digits < 1:
            # Name too short, use minimum viable format
            return f"{prefix}{counter}"

        # Generate name with zero-padded counter (NO trailing hyphens)
        # Example: D00001, PA0042, CP0001
        format_str = f"{prefix}{{:0{available_digits}d}}"
        generated = format_str.format(counter)

        # If counter overflows available digits, extend the name
        if len(generated) > target_len:
            generated = f"{prefix}{counter}"

        # Ensure we don't exceed max length
        if len(generated) > MAX_IDENTIFIER_LENGTH:
            # Truncate prefix if needed
            max_counter_digits = MAX_IDENTIFIER_LENGTH - 1
            generated = f"{prefix[0]}{counter:0{max_counter_digits}d}"[-MAX_IDENTIFIER_LENGTH:]

        return generated

    def _validate_identifier(self, name: str) -> None:
        """Validate that generated identifier is valid COBOL"""
        if len(name) > MAX_IDENTIFIER_LENGTH:
            raise MappingError(f"Generated identifier '{name}' exceeds {MAX_IDENTIFIER_LENGTH} chars")
        if len(name) < MIN_IDENTIFIER_LENGTH:
            raise MappingError(f"Generated identifier '{name}' is empty")
        if name[0].isdigit():
            raise MappingError(f"Generated identifier '{name}' starts with digit")
        if name[0] == '-':
            raise MappingError(f"Generated identifier '{name}' starts with hyphen")
        if name[-1] == '-':
            raise MappingError(f"Generated identifier '{name}' ends with hyphen")
        if name.upper() in self.reserved_words:
            raise MappingError(f"Generated identifier '{name}' is a reserved word")

    def save(self, path: str) -> None:
        """Persist mappings to JSON file"""
        data = {
            'version': '1.0',
            'generated': datetime.now().isoformat(),
            'statistics': {
                'total_mappings': len(self.mappings),
                'external_names': len(self.external_names),
                'by_type': {t.name: c for t, c in self.counters.items()}
            },
            'mappings': [e.to_dict() for e in self.mappings.values()],
            'external_names': list(self.external_names)
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> 'MappingTable':
        """Load existing mappings from JSON file"""
        with open(path) as f:
            data = json.load(f)

        table = cls()
        table.external_names = set(data.get('external_names', []))
        for entry in data['mappings']:
            table.mappings[entry['original'].upper()] = MappingEntry(
                original=entry['original'],
                anonymized=entry['anonymized'],
                identifier_type=IdentifierType[entry['type']],
                first_file=entry['first_seen'].split(':')[0],
                first_line=int(entry['first_seen'].split(':')[1]),
                occurrence_count=entry['occurrences'],
                is_external=entry.get('is_external', False)
            )
        return table
```

### 4.5 Token Representation

```python
@dataclass
class Token:
    """Represents a single token within the code area"""
    value: str                  # Token text
    token_type: TokenType       # Classification
    start_col: int              # Start column (1-based, relative to line start)
    end_col: int                # End column (1-based)
    original_value: str         # Original value before transformation
    area: str                   # 'A' or 'B' indicating which area
    preceding_whitespace: str   # Whitespace before this token

class TokenType(Enum):
    """Token classification for processing"""
    KEYWORD = auto()            # COBOL reserved word
    IDENTIFIER = auto()         # User-defined name
    LEVEL_NUMBER = auto()       # 01, 02, ..., 49, 66, 77, 88
    PIC_CLAUSE = auto()         # PIC X(10), PIC 9(5)V99, etc.
    LITERAL_STRING = auto()     # 'text' or "text"
    LITERAL_NUMBER = auto()     # 123, -45.67
    OPERATOR = auto()           # = < > + - * /
    PUNCTUATION = auto()        # . , ; ( )
    WHITESPACE = auto()         # Spaces (preserved)
    CLAUSE_KEYWORD = auto()     # REDEFINES, VALUE, OCCURS, etc.
```

---

## 5. PIC Clause Handling

### 5.1 PIC Clause Preservation

PIC (PICTURE) clauses define data layout and must NEVER be modified. The PIC parser detects and protects these clauses.

### 5.2 PIC Patterns to Detect

```python
# PIC clause patterns found in codebase
PIC_PATTERNS = [
    r'PIC\s+X\(\d+\)',           # PIC X(10)
    r'PIC\s+X',                   # PIC X
    r'PIC\s+9\(\d+\)',           # PIC 9(5)
    r'PIC\s+9+',                  # PIC 999
    r'PIC\s+S9\(\d+\)',          # PIC S9(8) - signed
    r'PIC\s+S9\(\d+\)V9\(\d+\)', # PIC S9(8)V9(2) - with decimal
    r'PIC\s+Z+9*',               # PIC ZZZ9 - edited numeric
    r'PIC\s+-+9+',               # PIC ---9 - edited with sign
]

# USAGE clauses to preserve
USAGE_PATTERNS = [
    r'COMP-3',
    r'COMP-1',
    r'COMP-2',
    r'COMP',
    r'COMPUTATIONAL-3',
    r'COMPUTATIONAL',
    r'DISPLAY',
    r'BINARY',
    r'PACKED-DECIMAL',
]
```

### 5.3 PIC Parser Implementation

```python
class PICParser:
    """Detect and preserve PIC clauses"""

    PIC_REGEX = re.compile(
        r'PIC(?:TURE)?\s+[SV9XAZ\(\)\d\.\,\+\-\*\/\s]+',
        re.IGNORECASE
    )

    USAGE_REGEX = re.compile(
        r'\b(COMP(?:UTATIONAL)?(?:-[123])?|DISPLAY|BINARY|PACKED-DECIMAL)\b',
        re.IGNORECASE
    )

    def find_pic_ranges(self, code: str) -> List[Tuple[int, int]]:
        """Find all PIC clause ranges in code (start, end positions)"""
        ranges = []
        for match in self.PIC_REGEX.finditer(code):
            ranges.append((match.start(), match.end()))
        return ranges

    def is_in_pic_clause(self, position: int, pic_ranges: List[Tuple[int, int]]) -> bool:
        """Check if a position is within a PIC clause"""
        for start, end in pic_ranges:
            if start <= position < end:
                return True
        return False
```

---

## 6. COPY Statement Handling

### 6.1 COPY Statement Patterns

```cobol
COPY copyname.
COPY copyname OF library.
COPY copyname REPLACING ==pattern== BY ==replacement==.
COPY copyname REPLACING pattern-1 BY replacement-1
                        pattern-2 BY replacement-2.
```

### 6.2 COPY Parser Implementation

```python
class CopyResolver:
    """Parse and resolve COPY statements"""

    # Full COPY statement regex including REPLACING
    COPY_REGEX = re.compile(
        r'COPY\s+(\w+)'                           # Copybook name
        r'(?:\s+OF\s+(\w+))?'                     # Optional library
        r'(?:\s+REPLACING\s+(.+?))?'              # Optional REPLACING clause
        r'\s*\.',                                  # Terminating period
        re.IGNORECASE | re.DOTALL
    )

    # REPLACING pattern: ==text== BY ==text== or identifier BY identifier
    REPLACING_PATTERN = re.compile(
        r'==([^=]+)==\s+BY\s+==([^=]+)=='         # ==pattern== BY ==replacement==
        r'|(\w[\w-]*)\s+BY\s+(\w[\w-]*)',         # word BY word
        re.IGNORECASE
    )

    def parse_copy_statement(self, code: str) -> Optional[CopyStatement]:
        """Parse a COPY statement and extract all components"""
        match = self.COPY_REGEX.search(code)
        if not match:
            return None

        copybook_name = match.group(1)
        library = match.group(2)
        replacing_clause = match.group(3)

        replacements = []
        if replacing_clause:
            for rep_match in self.REPLACING_PATTERN.finditer(replacing_clause):
                if rep_match.group(1):  # ==pattern== form
                    pattern = rep_match.group(1).strip()
                    replacement = rep_match.group(2).strip()
                else:  # word form
                    pattern = rep_match.group(3)
                    replacement = rep_match.group(4)
                replacements.append((pattern, replacement))

        return CopyStatement(
            copybook_name=copybook_name,
            library=library,
            replacements=replacements
        )

@dataclass
class CopyStatement:
    copybook_name: str
    library: Optional[str]
    replacements: List[Tuple[str, str]]
```

### 6.3 COPY REPLACING Anonymization Strategy

When a COPY statement has REPLACING:
1. Anonymize the copybook name
2. Anonymize patterns in REPLACING that are identifiers
3. Track that the same copybook may produce different identifiers in different files

```python
def anonymize_copy_statement(self, stmt: CopyStatement, mapper: MappingTable) -> str:
    """Anonymize a COPY statement including REPLACING patterns"""
    anon_copybook = mapper.get_or_create(
        stmt.copybook_name, IdentifierType.COPYBOOK_NAME, self.file, self.line
    )

    result = f"COPY {anon_copybook}"

    if stmt.library:
        # Libraries are typically not anonymized (system references)
        result += f" OF {stmt.library}"

    if stmt.replacements:
        result += " REPLACING"
        for pattern, replacement in stmt.replacements:
            # Anonymize if pattern looks like an identifier prefix
            if self._is_identifier_pattern(pattern):
                anon_pattern = self._anonymize_pattern(pattern, mapper)
                anon_replacement = self._anonymize_pattern(replacement, mapper)
                result += f" =={anon_pattern}== BY =={anon_replacement}=="
            else:
                result += f" =={pattern}== BY =={replacement}=="

    result += "."
    return result
```

---

## 7. Special COBOL Constructs

### 7.1 EXTERNAL Clause

Data items marked with `EXTERNAL` are globally visible across programs and should NOT be anonymized.

```cobol
01  MSMFS-GRP       EXTERNAL.
    05 MSMFS-MODNAME          PIC X(00008).
```

**Handling**:
```python
def detect_external(self, line: COBOLLine) -> bool:
    """Detect if line declares an EXTERNAL data item"""
    return 'EXTERNAL' in line.code_area.upper()

def process_external_declaration(self, line: COBOLLine) -> None:
    """Mark data item as EXTERNAL (do not anonymize)"""
    # Extract the data name from the line
    data_name = self._extract_data_name(line)
    if data_name:
        self.mapper.external_names.add(data_name.upper())
```

### 7.2 JUSTIFIED Clause

```cobol
10 CODICE-ELEMENTO              PIC X(20) JUST RIGHT.
```

**Handling**: Preserve JUSTIFIED/JUST clause unchanged.

### 7.3 Multi-line VALUE Clauses

```cobol
88 MS01-PROFILO-DIREZIONALE
                           VALUE 'D   ' THRU 'D00 ',
                          'D001' THRU 'D999', 'D00B' THRU 'DZZZ'.
88 MS01-PROFILO-AGENZIALE
                           VALUE 'A   ' THRU 'AZZZ',
                                'D00A'.
```

**Handling**:
1. Track continuation of VALUE clauses across lines
2. Preserve all VALUE literals (don't anonymize the actual values)
3. Only anonymize the condition name (88-level name)

### 7.4 Nested REDEFINES

```cobol
03  FILLER      REDEFINES   A000-CHIAVE-AREE-AGGIORNAMENTO.
  05  A000-CODICE-AREA                      PIC  X(05).
  05  FILLER         REDEFINES   A000-CODICE-AREA.
    06 A000-IDENTIFICATIVO-DB               PIC  X(01).
  05  A000-IDENT-AREA.
    06  FILLER         REDEFINES   A000-IDENT-AREA-CHIAVE.
      08  A000-IDENT-CONTRATTO.
```

**Handling**:
1. Track REDEFINES target at each level
2. Map REDEFINES target to its anonymized name
3. Support arbitrary nesting depth
4. Handle FILLER REDEFINES (FILLER is preserved)

```python
class RedefinesTracker:
    """Track REDEFINES relationships for consistent mapping"""

    def __init__(self):
        self.redefines_map: Dict[str, str] = {}  # redefined_name -> original_name

    def register_redefines(self, redefining: str, redefined: str) -> None:
        """Register a REDEFINES relationship"""
        self.redefines_map[redefining.upper()] = redefined.upper()

    def get_anonymized_target(self, target: str, mapper: MappingTable) -> str:
        """Get the anonymized name for a REDEFINES target"""
        key = target.upper()
        if key == 'FILLER':
            return 'FILLER'  # FILLER is never anonymized
        if key in mapper.mappings:
            return mapper.mappings[key].anonymized
        raise MappingError(f"REDEFINES target '{target}' not found in mappings")
```

### 7.5 CONFIGURATION SECTION

```cobol
CONFIGURATION                      SECTION.
SOURCE-COMPUTER.         IBM-370 WITH DEBUGGING MODE.
OBJECT-COMPUTER.         IBM-370-G65.
SPECIAL-NAMES.
    DECIMAL-POINT IS COMMA.
```

**Handling**: CONFIGURATION SECTION contains system-specific items that are typically preserved:
- SOURCE-COMPUTER: Preserve
- OBJECT-COMPUTER: Preserve
- SPECIAL-NAMES: Preserve (affects numeric literal parsing)

### 7.6 Qualified Names

```cobol
MOVE WS-FIELD OF WS-GROUP TO OUTPUT-FIELD.
MOVE COUNTER IN WS-AREA TO WS-TARGET.
```

**Handling**:
```python
def transform_qualified_name(self, qualified: str, mapper: MappingTable) -> str:
    """Transform each component of a qualified name independently"""
    # Split on OF or IN
    parts = re.split(r'\s+(OF|IN)\s+', qualified, flags=re.IGNORECASE)

    result_parts = []
    for i, part in enumerate(parts):
        if part.upper() in ('OF', 'IN'):
            result_parts.append(part)  # Preserve keyword
        else:
            # Anonymize this identifier
            anon = mapper.get_or_create(
                part.strip(), IdentifierType.DATA_NAME, self.file, self.line
            )
            result_parts.append(anon)

    return ' '.join(result_parts)
```

---

## 8. Anonymization Rules

### 8.1 Elements to Anonymize

| Element | Detection Pattern | Anonymization Strategy |
|---------|-------------------|------------------------|
| Program name | `PROGRAM-ID. name` | `PG000001` |
| Copybook name | `COPY name` | `CP000001` (+ rename file) |
| Section name | `name SECTION.` | `SC000001` |
| Paragraph name | `name.` in PROCEDURE | `PA000001` |
| Data name | Level + name | `D0000001` (length-preserved) |
| Condition name | `88 name` | `C0000001` |
| File name | `FD name` | `FL000001` |
| Index name | `INDEXED BY name` | `IX000001` |
| String literal | `'text'` or `"text"` | `'AAA00001'` (length-preserved) |
| Comment text | After `*` in col 7 | Generic replacement |

### 8.2 Elements to Preserve (NEVER Modify)

| Element | Reason |
|---------|--------|
| COBOL reserved words | Required for syntax |
| PIC clauses | Define data layout |
| Level numbers | Define data hierarchy |
| FILLER keyword | Standard placeholder |
| Numeric literals | Often define sizes/counts |
| COMP/COMP-3/DISPLAY | Define storage format |
| EXTERNAL items | Cross-program visibility |
| CONFIGURATION items | System-specific settings |
| JUSTIFIED clause | Alignment specification |
| SYNC clause | Storage alignment |
| BLANK WHEN ZERO | Display formatting |

### 8.3 Sample Transformation

**Before Anonymization:**
```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID.    EQTRHORI.
      *    SISTEMA PORTAFOGLIO RAMI DANNI
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  MSMFS-GRP       EXTERNAL.
           05 MSMFS-MODNAME          PIC X(00008).
       01  WS-POLIZZA-DATA.
           05 WS-NUMERO-POLIZZA      PIC X(10).
           05 WS-DATA-EMISSIONE      PIC 9(08).
              88 WS-DATA-VALIDA      VALUE 19000101 THRU 99991231.
       PROCEDURE DIVISION.
       A100-MAIN-PROCESS.
           COPY EDMCA000.
           MOVE WS-NUMERO-POLIZZA TO OUTPUT-FIELD.
```

**After Anonymization:**
```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID.    PG000001.
      *    SYSTEM MODULE PROCESSING
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  MSMFS-GRP       EXTERNAL.
           05 MSMFS-MODNAME          PIC X(00008).
       01  D0000001.
           05 D0000002               PIC X(10).
           05 D0000003               PIC 9(08).
              88 C0000001            VALUE 19000101 THRU 99991231.
       PROCEDURE DIVISION.
       PA000001.
           COPY CP000001.
           MOVE D0000002 TO D0000004.
```

Note: `MSMFS-GRP` and `MSMFS-MODNAME` are preserved because they are EXTERNAL.

---

## 9. Configuration

```python
@dataclass
class Config:
    """Anonymizer configuration options"""

    # Input/Output paths
    input_dir: Path
    output_dir: Path

    # File selection
    extensions: List[str] = field(default_factory=lambda: ['.cob', '.cbl', '.cpy'])
    encoding: str = 'utf-8'

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
    anonymize_change_tags: bool = False     # BENIQ, CDR, etc.

    # Preservation rules
    preserve_external: bool = True          # Don't anonymize EXTERNAL items

    # Generation options
    preserve_name_length: bool = True
    random_seed: Optional[int] = None       # For reproducibility

    # Mapping persistence
    mapping_file: Optional[Path] = None     # Load existing mappings
    save_mapping: bool = True

    # Validation
    validate_columns: bool = True
    validate_consistency: bool = True
    validate_identifier_length: bool = True  # Enforce 30-char limit

    # Output
    generate_report: bool = True
    verbose: bool = False
    log_level: str = 'INFO'
```

---

## 10. Error Handling

### 10.1 Exception Hierarchy

```python
class AnonymizerError(Exception):
    """Base exception for anonymizer errors"""
    pass

class ParseError(AnonymizerError):
    """Error parsing COBOL source"""
    def __init__(self, file: str, line: int, message: str):
        self.file = file
        self.line = line
        super().__init__(f"{file}:{line}: {message}")

class MappingError(AnonymizerError):
    """Error in mapping generation or application"""
    pass

class ValidationError(AnonymizerError):
    """Output validation failure"""
    pass

class ColumnOverflowError(ValidationError):
    """Line exceeds column 72 in code area"""
    pass

class IdentifierLengthError(ValidationError):
    """Generated identifier exceeds 30 characters"""
    pass

class ConfigError(AnonymizerError):
    """Configuration error"""
    pass

class CopyNotFoundError(AnonymizerError):
    """Referenced copybook not found"""
    def __init__(self, copybook: str, file: str, line: int):
        self.copybook = copybook
        super().__init__(f"{file}:{line}: Copybook '{copybook}' not found")

class CircularDependencyError(AnonymizerError):
    """Circular COPY dependency detected"""
    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        super().__init__(f"Circular COPY dependency: {' -> '.join(cycle)}")
```

### 10.2 Recovery Strategies

| Error Type | Strategy | Behavior |
|------------|----------|----------|
| Parse error | Log warning, preserve line | Continue processing, mark file as partial |
| Mapping collision | Generate alternative | Append incrementing suffix until unique |
| Reserved word collision | Use alternative prefix | Try next prefix in sequence |
| Column overflow | Error | Stop processing, report exact location |
| Identifier too long | Truncate with warning | Use max 30 chars, log warning |
| Copybook not found | Error | Stop processing, report missing file |
| Circular dependency | Error | Stop processing, report cycle |

### 10.3 Logging Configuration

```python
import logging

def setup_logging(config: Config) -> logging.Logger:
    """Configure logging for the anonymizer"""
    logger = logging.getLogger('cobol_anonymizer')
    logger.setLevel(getattr(logging, config.log_level.upper()))

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
```

---

## 11. Processing Pipeline

### 11.1 Phase 1: Discovery

```python
class DiscoveryPhase:
    """Scan files and build dependency graph"""

    def execute(self, input_dir: str, extensions: List[str]) -> DiscoveryResult:
        # 1. Find all COBOL files (sorted for determinism)
        files = sorted(self._scan_files(input_dir, extensions))

        # 2. Build COPY dependency graph
        copy_graph = self._build_copy_graph(files)

        # 3. Check for circular dependencies
        self._check_circular_dependencies(copy_graph)

        # 4. Determine processing order (copybooks before programs)
        processing_order = self._topological_sort(copy_graph, files)

        # 5. Extract all identifiers for pre-registration
        identifiers = self._extract_identifiers(files)

        return DiscoveryResult(
            files=files,
            copy_graph=copy_graph,
            processing_order=processing_order,
            identifiers=identifiers
        )

    def _check_circular_dependencies(self, graph: Dict[str, List[str]]) -> None:
        """Detect circular COPY dependencies"""
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    raise CircularDependencyError(path[cycle_start:] + [neighbor])

            path.pop()
            rec_stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node, [])
```

### 11.2 Phase 2: Mapping Generation

```python
class MappingPhase:
    """Generate consistent anonymized mappings"""

    def __init__(self, config: Config):
        self.config = config
        self.table = MappingTable()
        self._load_reserved_words()

    def execute(self, discovery: DiscoveryResult) -> MappingTable:
        # Process files in dependency order (copybooks first)
        for file_path in discovery.processing_order:
            self._process_file(file_path)

        # Validate no collisions with reserved words
        self._validate_no_collisions()

        return self.table

    def _process_file(self, file_path: Path) -> None:
        """Extract and register identifiers from a file"""
        with open(file_path, encoding=self.config.encoding) as f:
            context = FileContext(file_path)

            for line_num, raw_line in enumerate(f, 1):
                line = parse_line(raw_line, line_num)

                if line.is_comment:
                    continue

                # Update context (current division, section, etc.)
                context.update(line)

                # Check for EXTERNAL declaration
                is_external = self._detect_external(line)

                # Extract and register identifiers
                for identifier, id_type in self._extract_from_line(line, context):
                    self.table.get_or_create(
                        identifier, id_type,
                        file_path.name, line_num,
                        is_external=is_external and self.config.preserve_external
                    )
```

---

## 12. Testing Strategy

### 12.1 Unit Tests

| Module | Test Focus |
|--------|------------|
| `column_handler` | Column parsing, change tags, reconstruction |
| `tokenizer` | Token extraction, PIC clause detection |
| `name_generator` | Valid names, length limits, no trailing hyphens |
| `mapper` | Consistency, EXTERNAL handling, persistence |
| `pic_parser` | All PIC patterns, COMP variations |
| `copy_resolver` | COPY parsing, REPLACING patterns |

### 12.2 Integration Tests

```python
def test_cross_file_consistency():
    """Same identifier maps to same name across files"""

def test_copy_reference_integrity():
    """COPY statements reference correctly renamed copybooks"""

def test_redefines_integrity():
    """REDEFINES clauses reference valid anonymized names"""

def test_deterministic_output():
    """Same input always produces identical output"""

def test_external_preservation():
    """EXTERNAL items are never anonymized"""

def test_nested_redefines():
    """Multi-level REDEFINES handled correctly"""

def test_column_overflow_detection():
    """Overflow at column 72 is detected and reported"""
```

### 12.3 Validation Tests

```python
def test_column_format_preserved():
    """All output lines respect 80-column format"""

def test_no_reserved_word_collision():
    """Generated names don't conflict with COBOL reserved words"""

def test_pic_clauses_unchanged():
    """PIC clauses are never modified"""

def test_identifier_length_valid():
    """All generated identifiers are <= 30 characters"""

def test_no_trailing_hyphens():
    """No generated identifier ends with hyphen"""

def test_configuration_section_preserved():
    """CONFIGURATION SECTION items unchanged"""
```

### 12.4 Edge Case Test Files

| File | Edge Cases |
|------|------------|
| `EDMCA000.cpy` | 3-level nested REDEFINES, all level numbers |
| `EGECMS01.cob` | Multi-line VALUE THRU, change tags (REPLAT) |
| `ELSCQ130.cob` | Deep nesting, COMP-3, 88-levels |
| `MSMFSDTA.cob` | EXTERNAL clause |
| `EQTRHORI.cbl` | CONFIGURATION SECTION, full program |
| `ITBCPA01.cpy` | JUSTIFIED clause |

---

## 13. Future Considerations

### 13.1 Potential Enhancements

- **COBOL dialect support**: Handle IBM, Micro Focus, GnuCOBOL variations
- **Syntax validation**: Integrate with COBOL compiler for validation
- **Incremental processing**: Handle updates to already-anonymized code
- **Reverse mapping**: Generate tool to map anonymized back to original

### 13.2 Performance Optimization

- **Parallel processing**: Process independent files concurrently
- **Streaming**: Handle very large files without full memory load
- **Caching**: Cache parsed copybooks for reuse

---

## Appendix A: COBOL Reserved Words

The tool maintains a comprehensive list of ~400 COBOL reserved words from COBOL-85 and COBOL-2002 standards that must never be used as anonymized identifiers.

## Appendix B: Identifier Naming Examples

| Original | Length | Generated | Notes |
|----------|--------|-----------|-------|
| WS-FIELD | 8 | D0000001 | 8 chars |
| WS-VERY-LONG-NAME | 17 | D0000000000000002 | 17 chars |
| X | 1 | D1 | Minimum viable |
| THIRTY-CHARACTER-IDENTIFIER-XX | 30 | D00000000000000000000000000003 | Max length |
| PARA-1 | 6 | PA0001 | 6 chars |

Note: All generated names use zero-padded counters, never trailing hyphens.
