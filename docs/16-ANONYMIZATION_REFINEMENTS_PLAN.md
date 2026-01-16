# Anonymization Refinements Implementation Plan

## Overview

This document provides the implementation plan for two key anonymization refinements:

1. **EXTERNAL Item Anonymization** - Remove protection for EXTERNAL items, anonymize them like regular identifiers
2. **String Literal Anonymization** - Use a randomly selected naming scheme (different from main) with exact length preservation

These refinements ensure maximum anonymization while maintaining code correctness.

---

## Phase 1: EXTERNAL Item Anonymization

### 1.1 Remove EXTERNAL Protection

**File**: `src/cobol_anonymizer/core/classifier.py` and related files

**Current Behavior**: EXTERNAL items are protected (returned unchanged)

**New Behavior**: EXTERNAL items are anonymized like any other identifier

**Tasks**:
1. Remove EXTERNAL protection logic from classifier
2. Ensure EXTERNAL items are passed to name generator
3. Mapping table already ensures cross-file consistency
4. Update documentation

**Implementation**:
```python
# Remove protection - anonymize EXTERNAL items normally
# Only system identifiers (SQLCA, EIB*, DFH*) remain protected
def classify_identifier(self, name: str, context: Context) -> IdentifierType:
    # Check for system identifiers first (these remain protected)
    if self._is_system_identifier(name):
        return IdentifierType.SYSTEM  # Protected

    # EXTERNAL items are now classified normally (no longer protected)
    # ... normal classification logic
```

### 1.2 Test Cases

```python
# tests/test_external_anonymization.py
def test_external_items_anonymized():
    """EXTERNAL items should be anonymized (not protected)."""
    code = """
       01 EXT-RECORD EXTERNAL.
          05 EXT-FIELD PIC X(10).
    """
    result = anonymize(code)
    assert "EXT-RECORD" not in result
    assert "EXT-FIELD" not in result

def test_external_consistency_across_files():
    """Same EXTERNAL name maps to same anonymized name in all files."""
    # Test cross-file consistency
```

---

## Phase 2: String Literal Anonymization

### 2.1 Add Literal Naming Scheme Selection

**File**: `src/cobol_anonymizer/core/anonymizer.py`

**Tasks**:
1. At initialization, randomly select a naming scheme for literals (different from main scheme)
2. Create a literal-specific name generator
3. Ensure determinism with seed parameter

**Implementation**:
```python
import random

def _select_literal_scheme(self, main_scheme: NamingScheme) -> NamingScheme:
    """Select a random naming scheme for literals, different from main scheme."""
    available = [s for s in NamingScheme if s != main_scheme]
    # Use seeded random for determinism
    rng = random.Random(self.config.seed)
    return rng.choice(available)
```

### 2.2 Length-Preserving Literal Replacement

**File**: `src/cobol_anonymizer/core/literal_anonymizer.py` (new file)

**Tasks**:
1. Generate replacement text using naming scheme words
2. Pad or truncate to match exact original length
3. Handle edge cases (very short strings, special characters)

**Implementation**:
```python
class LiteralAnonymizer:
    """Anonymizes string literals using a naming scheme with length preservation."""

    def __init__(self, scheme: NamingScheme, seed: int = None):
        self.scheme = scheme
        self.word_generator = WordBasedNamingStrategy.get_strategy(scheme)
        self.rng = random.Random(seed)

    def anonymize_literal(self, original: str) -> str:
        """Replace literal content with naming scheme words, preserving length."""
        target_length = len(original)

        # Generate words until we have enough characters
        words = []
        current_length = 0
        while current_length < target_length:
            word = self.word_generator.get_next_word()
            words.append(word)
            current_length += len(word) + 1  # +1 for separator

        # Join and truncate/pad to exact length
        result = "-".join(words)
        if len(result) > target_length:
            result = result[:target_length]
        elif len(result) < target_length:
            result = result.ljust(target_length, "-")

        return result
```

### 2.3 Integrate into Transform Pipeline

**File**: `src/cobol_anonymizer/core/anonymizer.py`

**Tasks**:
1. Detect string literals in code
2. Apply literal anonymizer
3. Preserve quote characters

**Implementation**:
```python
LITERAL_PATTERN = re.compile(r"'([^']*)'|\"([^\"]*)\"")

def transform_literals(self, line: str) -> str:
    """Transform string literals using literal naming scheme."""
    if not self.config.anonymize_literals:
        return line

    def replace_literal(match: re.Match) -> str:
        quote = "'" if match.group(1) is not None else '"'
        content = match.group(1) or match.group(2)
        anonymized = self.literal_anonymizer.anonymize_literal(content)
        return f"{quote}{anonymized}{quote}"

    return LITERAL_PATTERN.sub(replace_literal, line)
```

### 2.4 Test Cases

```python
# tests/test_literal_anonymization.py
def test_literal_length_preserved():
    """Anonymized literal has same length as original."""
    original = "'CUSTOMER ACCOUNT BALANCE'"
    result = anonymize(original)
    assert len(result) == len(original)

def test_literal_uses_different_scheme():
    """Literals use a different naming scheme than identifiers."""
    config = Config(naming_scheme=NamingScheme.NUMERIC)
    # Verify literals don't use NUMERIC scheme

def test_literal_deterministic_with_seed():
    """Same seed produces same literal anonymization."""
    result1 = anonymize(code, seed=42)
    result2 = anonymize(code, seed=42)
    assert result1 == result2
```

---

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `src/cobol_anonymizer/core/literal_anonymizer.py` | String literal anonymization with naming schemes |
| `tests/test_literal_anonymization.py` | Tests for string literal anonymization |

### Modified Files

| File | Changes |
|------|---------|
| `src/cobol_anonymizer/core/anonymizer.py` | Integrate literal anonymizer, select random scheme |
| `src/cobol_anonymizer/core/classifier.py` | Remove EXTERNAL protection logic |

---

## Verification Checklist

### EXTERNAL Item Anonymization
- [ ] EXTERNAL items are anonymized (not protected)
- [ ] EXTERNAL items are consistent across files (same name → same anonymized name)
- [ ] System identifiers (SQLCA, EIB*, DFH*) remain protected
- [ ] Cross-program linkage still works after anonymization

### String Literal Anonymization
- [ ] Literals use a different naming scheme than identifiers
- [ ] Literal replacement preserves exact original length
- [ ] Literal anonymization is deterministic with seed
- [ ] All quote styles handled (single and double quotes)

### General
- [ ] Tests pass with >90% coverage for new code

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| EXTERNAL cross-file inconsistency | Mapping table ensures consistency |
| String literal length mismatch | Strict length preservation with padding/truncation |
| Breaking existing tests | Run full test suite after each phase |
