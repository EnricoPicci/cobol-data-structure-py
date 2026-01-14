# Refactoring Opportunities for COBOL Anonymizer

This document identifies refactoring opportunities discovered through a comprehensive code review of the COBOL Anonymizer codebase. The analysis covers all major modules: core processing, COBOL handling, name generation, and output management.

## Executive Summary

The codebase demonstrates good architecture with clear separation of concerns. However, several areas have accumulated technical debt that can be addressed:

- **30+ refactoring opportunities** identified
- **~200+ lines of code** can be reduced or simplified
- **3 instances of dead code** should be removed
- **Multiple duplicate patterns** can be consolidated

### Priority Distribution
| Priority | Count | Description |
|----------|-------|-------------|
| HIGH | 6 | Critical duplications affecting maintainability |
| MEDIUM | 16 | Consolidation and simplification opportunities |
| LOW | 10 | Code hygiene and minor improvements |

---

## Part 1: Core Module Refactoring (`src/cobol_anonymizer/core/`)

### 1.1 HIGH: Repetitive Token Iteration Pattern in Classifier

**Location:** `core/classifier.py` (lines 284-420)

**Issue:** Seven methods repeat the same pattern of iterating through tokens, skipping whitespace, and finding the first token after a keyword:
- `_is_paragraph_definition()` (284-292)
- `_is_data_definition()` (296-300)
- `_classify_program_id()` (309-328)
- `_classify_copy_statement()` (337-351)
- `_classify_fd_declaration()` (360-376)
- `_classify_section_header()` (384-398)
- `_classify_paragraph()` (406-420)

**Current Pattern:**
```python
found_keyword = False
for token in tokens:
    if token.type == TokenType.WHITESPACE:
        continue
    if found_keyword:
        if token.type in (TokenType.IDENTIFIER, TokenType.RESERVED):
            # ... process and return
    if token.type == TokenType.RESERVED and "KEYWORD" in token.value.upper():
        found_keyword = True
```

**Refactoring:** Extract a helper method:
```python
def _find_token_after_keyword(
    self,
    tokens: List[Token],
    keyword: str,
    expected_types: Set[TokenType] = None,
) -> Optional[Token]:
    """Find the first non-whitespace identifier after a specific keyword."""
    found_keyword = False
    for token in tokens:
        if token.type == TokenType.WHITESPACE:
            continue
        if found_keyword:
            if expected_types is None or token.type in expected_types:
                return token
        if token.type == TokenType.RESERVED and keyword in token.value.upper():
            found_keyword = True
    return None
```

**Impact:** Reduces ~40 lines, improves maintainability

---

### 1.2 HIGH: Dead Code in Tokenizer

**Location:** `core/tokenizer.py` (lines 289-313)

**Issue:** Numeric literal matching code appears twice - at lines 241-255 and again at lines 289-313. The second block is unreachable dead code.

**Refactoring:** Delete lines 289-313 entirely.

**Impact:** Removes ~20 lines of dead code

---

### 1.3 MEDIUM: Redundant `tokenize_code_area()` Function

**Location:** `core/tokenizer.py` (lines 328-346)

**Issue:** This function is a thin wrapper around `tokenize_line()` that adds no value:
```python
def tokenize_code_area(code, line_number=1, is_comment=False):
    return tokenize_line(code, line_number, is_comment)
```

**Refactoring:** Remove function, update callers to use `tokenize_line()` directly.

---

### 1.4 MEDIUM: Regex Pattern Recompilation

**Location:** `core/anonymizer.py` (line 279-282)

**Issue:** REDEFINES pattern compiled on-the-fly for every line processed.

**Refactoring:** Move to module level:
```python
REDEFINES_PATTERN = re.compile(
    r'(\d+)\s+([A-Za-z][A-Za-z0-9\-]*)\s+REDEFINES\s+([A-Za-z][A-Za-z0-9\-]*)',
    re.IGNORECASE
)
```

---

### 1.5 MEDIUM: Simplified EXTERNAL Handling

**Location:** `core/anonymizer.py` (lines 468-481)

**Issue:** Redundant `mark_external()` call before `get_or_create()`.

**Current:**
```python
if ident.is_external or ident.type == IdentifierType.EXTERNAL_NAME:
    self.mapping_table.mark_external(ident.name)
    self.mapping_table.get_or_create(ident.name, ident.type, is_external=True)
else:
    self.mapping_table.get_or_create(ident.name, ident.type, is_external=False)
```

**Refactoring:**
```python
is_external = ident.is_external or ident.type == IdentifierType.EXTERNAL_NAME
self.mapping_table.get_or_create(ident.name, ident.type, is_external=is_external)
```

---

### 1.6 LOW: Unused Parameter in `tokenize_line()`

**Location:** `core/tokenizer.py` (line 125)

**Issue:** Parameter `is_continuation` is defined but never used.

**Refactoring:** Remove parameter or implement continuation handling.

---

## Part 2: Generator Module Refactoring (`src/cobol_anonymizer/generators/`)

### 2.1 HIGH: Duplicate Numeric Name Formatting

**Location:** Multiple files (4 locations)

**Files Affected:**
- `generators/naming_schemes.py` (lines 84-104, 155-166)
- `generators/name_generator.py` (lines 144-166, 207-242)

**Issue:** The numeric name formatting logic (`PREFIX + zero-padded counter`) is duplicated four times.

**Refactoring:** Create single utility function:
```python
def _format_numeric_name(prefix: str, counter: int, available_digits: int) -> str:
    """Format numeric name with zero-padded counter."""
    if available_digits < 1:
        return f"{prefix}{counter}"
    counter_str = str(counter).zfill(available_digits)
    if len(counter_str) > available_digits:
        counter_str = str(counter)
    return f"{prefix}{counter_str}"
```

**Impact:** HIGH - Eliminates 60+ lines of duplication

---

### 2.2 HIGH: Duplicate Comment Processing Functions

**Location:** `generators/comment_generator.py` (lines 293-366)

**Issue:** Three functions follow identical patterns:
- `remove_personal_names()` (294-316)
- `remove_system_ids()` (319-341)
- `translate_italian_terms()` (344-366)

**Refactoring:** Create generic pattern matcher:
```python
def _apply_pattern_replacements(
    text: str,
    patterns: Dict[str, str],
    case_sensitive: bool = False
) -> Tuple[str, List[Tuple[str, str]]]:
    """Apply dictionary of replacements to text."""
    changes = []
    result = text
    for old, new in patterns.items():
        pattern = re.compile(rf'\b{re.escape(old)}\b',
                            re.IGNORECASE if not case_sensitive else 0)
        if pattern.search(result):
            result = pattern.sub(new, result)
            changes.append((old, new))
    return result, changes
```

---

### 2.3 MEDIUM: NAME_PREFIXES Lookup Duplication

**Location:** Multiple files

**Issue:** Pattern `NAME_PREFIXES.get(id_type, "X")` appears 4+ times.

**Refactoring:** Create utility function:
```python
def get_prefix_for_type(id_type: IdentifierType) -> str:
    """Get the naming prefix for an identifier type."""
    return NAME_PREFIXES.get(id_type, "X")
```

---

### 2.4 MEDIUM: WordBasedNamingStrategy Complexity

**Location:** `generators/naming_schemes.py` (lines 110-221)

**Issues:**
- `_fallback_to_numeric()` duplicates NumericNamingStrategy logic
- `_hash_name()` is trivial 2-line wrapper
- `_truncate_name()` has redundant validation

**Refactoring:**
1. Remove `_fallback_to_numeric()` - use shared utility from 2.1
2. Inline `_hash_name()` logic
3. Simplify `_truncate_name()` validation

---

### 2.5 LOW: Potential Dead Code in NameGenerator

**Location:** `generators/name_generator.py` (lines 193-204)

**Issue:** `get_counter_state()` and `set_counter_state()` methods may be unused in production.

**Action:** Verify usage before removing.

---

## Part 3: COBOL Module Refactoring (`src/cobol_anonymizer/cobol/`)

### 3.1 MEDIUM: PIC Parser Function Consolidation

**Location:** `cobol/pic_parser.py` (lines 355-439)

**Issue:** Multiple thin wrapper functions for clause checking:
- `has_value_clause()`
- `has_redefines_clause()`
- `has_occurs_clause()`
- `has_external_clause()`
- `has_global_clause()`

**Refactoring:** Create generic clause checker:
```python
def has_clause(line: str, clause_name: str) -> bool:
    """Check if a line contains a specific COBOL clause."""
    return bool(re.search(rf'\b{clause_name}\b', line, re.IGNORECASE))
```

---

### 3.2 LOW: Inconsistent Position Checking

**Location:** `cobol/pic_parser.py` (line 341)

**Issue:** `is_protected_position()` calls both `is_in_pic_clause()` and `is_in_usage_clause()` separately instead of using `get_protected_ranges()`.

**Refactoring:**
```python
def is_protected_position(line: str, position: int) -> bool:
    ranges = get_protected_ranges(line)
    return any(start <= position < end for start, end in ranges)
```

---

## Part 4: Output Module Refactoring (`src/cobol_anonymizer/output/`)

### 4.1 HIGH: Duplicate Output/Logging Logic in CLI

**Location:** `cli.py` (lines 236-334)

**Issue:** `run_validation()` and `run_anonymization()` contain substantial duplication in error/warning output handling.

**Refactoring:** Extract `format_result_output()` function:
```python
def _print_issues(issues: List, label: str, limit: int = 10, file=None) -> None:
    """Print issues with optional limit."""
    if not issues:
        return
    print(f"\n{label} ({len(issues)}):", file=file)
    for issue in issues[:limit]:
        print(f"  {issue}", file=file)
    if len(issues) > limit:
        print(f"  ... and {len(issues) - limit} more", file=file)
```

**Impact:** Reduces ~50 lines of duplicated code

---

### 4.2 MEDIUM: Validator Instantiation Without Configuration

**Location:** Multiple files (3 locations)
- `main.py:99`
- `main.py:257`
- `cli.py:246`

**Issue:** `OutputValidator()` instantiated 3 times without passing config.

**Refactoring:** Create factory function:
```python
def create_validator_from_config(config: Config) -> OutputValidator:
    """Create validator with configuration from main Config."""
    validator_config = ValidatorConfig(
        max_identifier_length=config.max_identifier_length,
        # ... other config mappings
    )
    return OutputValidator(validator_config)
```

---

### 4.3 MEDIUM: Multiple Standalone Validation Functions

**Location:** `output/validator.py` (lines 332-418)

**Issue:** Three standalone functions could be methods on `OutputValidator`:
- `validate_identifier_lengths()`
- `validate_column_format()`
- `validate_mapping_table()`

**Refactoring:** Move into class as methods with consistent return types.

---

### 4.4 MEDIUM: Verbose Output Callback Logic

**Location:** `cli.py` (lines 278-296)

**Issue:** Three callback functions have repetitive verbose/quiet checking.

**Refactoring:** Create `ConsoleReporter` class:
```python
class ConsoleReporter:
    def __init__(self, verbose: bool = False, quiet: bool = False):
        self.verbose = verbose
        self.quiet = quiet

    def on_file_start(self, file_path: Path, index: int, total: int) -> None:
        if self.verbose:
            print(f"Processing [{index}/{total}] {file_path.name}...")

    # ... other methods
```

---

### 4.5 MEDIUM: Config Setup Method Too Long

**Location:** `main.py` (lines 63-99)

**Issue:** `setup()` method creates 7 components with interleaved config logic.

**Refactoring:** Extract factory methods:
- `_setup_anonymizer()`
- `_setup_comment_transformer()`
- `_setup_writer()`
- `_setup_validator()`

---

### 4.6 MEDIUM: Report Generation Spread Across Functions

**Location:** `output/report.py` (lines 273-337)

**Issue:** Three separate functions create different report formats with duplicated statistics gathering:
- `create_mapping_report()` (273-305)
- `create_summary_report()` (308-337)
- `ReportGenerator.generate_report()` (213-259)

**Refactoring:** Create unified `ReportFormatter` class with `.to_text()`, `.to_summary()`, `.to_mapping()` methods.

---

### 4.7 LOW: Redundant validate_directory Wrapper

**Location:** `main.py` (lines 247-258)

**Issue:** Thin wrapper that adds no value.

**Refactoring:** Remove function or expand to accept config; update exports.

---

### 4.8 LOW: Time Tracking Duplication

**Location:** `main.py` (lines 118, 187, 204)

**Issue:** Processing time calculated and stored twice; line 204 overwrites line 187.

**Refactoring:** Calculate once at line 187, remove duplicate at line 204.

---

## Implementation Plan

### Phase 1: Quick Wins (Low Risk, High Value)

**Estimated effort:** 2-4 hours

| Task | File | Lines Saved |
|------|------|-------------|
| Remove dead code (tokenizer numeric) | `core/tokenizer.py` | ~20 |
| Remove redundant `tokenize_code_area()` | `core/tokenizer.py` | ~18 |
| Fix time tracking duplication | `main.py` | ~3 |
| Simplify EXTERNAL handling | `core/anonymizer.py` | ~8 |
| Remove unused `is_continuation` param | `core/tokenizer.py` | ~1 |

**Total:** ~50 lines removed

### Phase 2: Pattern Consolidation (Medium Risk, High Value)

**Estimated effort:** 4-6 hours

| Task | Files | Impact |
|------|-------|--------|
| Extract token iteration helper | `core/classifier.py` | 7 methods simplified |
| Create numeric name formatting utility | `generators/*.py` | 4 locations unified |
| Create comment pattern replacement utility | `generators/comment_generator.py` | 3 functions unified |
| Extract CLI output formatting | `cli.py` | ~50 lines reduced |

### Phase 3: Structural Improvements (Medium Risk, Medium Value)

**Estimated effort:** 4-6 hours

| Task | Files | Benefit |
|------|-------|---------|
| Extract setup factory methods | `main.py` | Improved testability |
| Move regex patterns to module level | `core/anonymizer.py` | Performance |
| Create validator config factory | Multiple | Consistency |
| Consolidate validation functions | `output/validator.py` | API clarity |

### Phase 4: Polish (Low Risk, Low Value)

**Estimated effort:** 2-3 hours

| Task | Files |
|------|-------|
| Create NAME_PREFIXES utility | `generators/*.py` |
| Simplify WordBasedNamingStrategy | `generators/naming_schemes.py` |
| Create generic clause checker | `cobol/pic_parser.py` |
| Remove redundant wrapper functions | `main.py` |

---

## Testing Strategy

For each phase:

1. **Before Changes:**
   - Run full test suite: `pytest`
   - Record coverage: `pytest --cov=src/cobol_anonymizer`

2. **During Changes:**
   - Run related tests after each modification
   - Verify no behavior changes

3. **After Phase Completion:**
   - Run full test suite
   - Verify coverage unchanged or improved
   - Run integration tests with sample COBOL files

---

## Risk Assessment

| Phase | Risk Level | Mitigation |
|-------|------------|------------|
| Phase 1 | LOW | Dead code removal; simple deletions |
| Phase 2 | MEDIUM | Create helper methods first; update callers one at a time |
| Phase 3 | MEDIUM | Keep old signatures as deprecated wrappers initially |
| Phase 4 | LOW | Cosmetic changes; low impact on behavior |

---

## Success Metrics

After completing all phases:

- [ ] All tests pass
- [ ] Code coverage >= current level
- [ ] ~150-200 lines of code reduced
- [ ] No duplicate patterns > 3 lines remain
- [ ] All dead code removed
- [ ] Consistent API patterns across modules

---

## Document History

- **Created:** 2026-01-14
- **Author:** Code Review Analysis (3 parallel agents)
- **Version:** 1.0
