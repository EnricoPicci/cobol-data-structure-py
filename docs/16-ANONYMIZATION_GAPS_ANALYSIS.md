# Anonymization Gaps Analysis

## Overview

This document identifies gaps in the current COBOL anonymization logic that could allow correlation between anonymized code and original source. The objective of anonymization is to make it very difficult to link anonymized code to its original source.

## Gap Categories

Gaps are categorized by priority:
- **High Priority**: Directly undermines anonymization intent
- **Medium Priority**: Edge cases that could leak information
- **Low Priority**: Rare scenarios with minimal risk

---

## High Priority Gaps

### 1. File Names Not Anonymized

**Status**: Planned for implementation (see `16-FILE_NAME_ANONYMIZATION_PLAN.md`)

**Issue**: Output files retain their original names (e.g., `CUSTOMER-PAYMENT.cob`), revealing business context even when all identifiers inside are anonymized.

**Risk Level**: Critical - File names alone can reveal the purpose and domain of the code.

**Example**:
```
Original: LOAN-CALCULATION.cob → Output: LOAN-CALCULATION.cob (unchanged)
```

**Recommendation**: Implement file name anonymization using naming schemes.

---

### 2. CALL Statement Targets Not Anonymized

**Status**: Not implemented

**Issue**: The `CALL` statement invokes other programs by name. These program names are not specifically classified or anonymized.

**Risk Level**: High - CALL targets reveal program relationships and can identify specific functionality.

**Example**:
```cobol
           CALL 'CALCULATE-INTEREST' USING WS-PARAMS.
           CALL WS-PROGRAM-NAME USING WS-DATA.
```

**Current Behavior**:
- Literal program names in quotes (`'CALCULATE-INTEREST'`) are treated as string literals
- Variable program names (`WS-PROGRAM-NAME`) are anonymized as data names
- No tracking of cross-program relationships

**Recommendation**:
1. Add `CALLED_PROGRAM` identifier type to classifier
2. Detect CALL statements: `CALL 'program-name'` and `CALL variable`
3. For literal names: Replace with anonymized version or generic placeholder
4. For variable names: Already handled as DATA_NAME
5. Track cross-program dependencies in mapping report

**Implementation Complexity**: Medium

---

## Medium Priority Gaps

### 3. EXTERNAL and GLOBAL Items Currently Protected

**Status**: Needs revision

**Issue**: The current implementation protects EXTERNAL items from anonymization. However, for complete anonymization, **no user-defined names should be protected** - only standard COBOL system names (like SQLCA, EIBAID, etc.) should remain unchanged.

**Current Behavior**:
- `has_global_clause()` in `pic_parser.py` detects GLOBAL keyword
- GLOBAL items are NOT protected from anonymization
- EXTERNAL items ARE protected (returned unchanged)

**Revised Requirement**:
- **EXTERNAL items SHOULD be anonymized** (not protected)
- **GLOBAL items SHOULD be anonymized** (already the case)
- **Standard COBOL system names** (SQLCA, SQLCODE, EIBXXX, DFHXXX) SHOULD remain protected
- Mapping must be maintained for cross-file consistency of EXTERNAL items

**Rationale**: The goal of anonymization is maximum obfuscation. Only truly system-level identifiers that would break compilation should be protected.

**Recommendation**:
1. Remove EXTERNAL protection logic
2. Anonymize EXTERNAL items like any other identifier
3. Ensure mapping table maintains consistency for EXTERNAL items across files
4. Keep system prefix protection (SQLCA, EIB*, DFH*, etc.)

**Implementation Complexity**: Low

---

### 4. COPY REPLACING Parameters Not Tracked

**Status**: Partially implemented

**Issue**: The REPLACING clause in COPY statements contains identifier patterns that are transformed. These transformations are not fully tracked in the mapping table.

**Risk Level**: Medium - Could cause inconsistent naming if same pattern is used differently.

**Example**:
```cobol
       COPY TEMPLATE REPLACING ==:PREFIX:== BY ==WS-CUSTOMER-==.
       COPY TEMPLATE REPLACING ==:PREFIX:== BY ==WS-ACCOUNT-==.
```

**Current Behavior**:
- COPY statement is parsed
- Copybook name is classified as COPYBOOK_NAME
- REPLACING patterns are NOT specifically classified
- Substitutions happen during copy expansion, not during anonymization

**Gap**: The replacement patterns (`WS-CUSTOMER-`, `WS-ACCOUNT-`) are likely data name prefixes that should be anonymized consistently.

**Recommendation**:
1. Parse REPLACING clause patterns as potential identifiers
2. Classify patterns that look like identifier prefixes
3. Add to mapping table for consistent transformation
4. Handle pseudo-text syntax (`==pattern==`)

**Implementation Complexity**: Medium

---

### 5. EXTERNAL Items Should Be Anonymized (Not Protected)

**Status**: Needs revision

**Issue**: With the revised requirement that EXTERNAL items should be anonymized (see Gap #3), the inheritance logic needs to change. Instead of "protecting" EXTERNAL items, we need to ensure **consistent anonymization** across files.

**Example**:
```cobol
       01 EXT-RECORD EXTERNAL.
          05 EXT-HEADER.
             10 EXT-TYPE PIC X(2).
             10 EXT-CODE PIC X(4).
          05 EXT-DETAIL OCCURS 10.
             10 EXT-ITEM PIC X(10).
```

**Revised Behavior**:
- All items (`EXT-RECORD`, `EXT-HEADER`, `EXT-TYPE`, etc.) SHOULD be anonymized
- The mapping table must ensure the same original name maps to the same anonymized name across all files
- Cross-file consistency is critical for EXTERNAL items to maintain runtime linkage

**Recommendation**:
1. Remove EXTERNAL protection logic entirely
2. Anonymize EXTERNAL items like regular identifiers
3. Mapping table already ensures cross-file consistency
4. Add tests to verify EXTERNAL items are anonymized consistently

**Implementation Complexity**: Low (simpler than before - just remove protection)

---

## Low Priority Gaps

### 6. ALTER Statement Targets Not Tracked

**Status**: Not implemented

**Issue**: The ALTER statement modifies GO TO targets at runtime. Paragraph names in ALTER statements should be anonymized consistently.

**Risk Level**: Low - ALTER is deprecated and rarely used in modern COBOL.

**Example**:
```cobol
           ALTER GO-TO-PARAGRAPH TO PROCEED TO NEW-TARGET.
```

**Current Behavior**: ALTER statement is not specifically parsed. Paragraph names may or may not be recognized depending on context.

**Recommendation**:
1. Add ALTER detection pattern
2. Classify paragraph names in ALTER as PARAGRAPH_NAME
3. Low priority due to rarity of ALTER usage

**Implementation Complexity**: Low

---

### 7. RENAMES (66-Level) Not Specially Handled

**Status**: Not implemented

**Issue**: The RENAMES clause (66-level) creates alternative names for data items or ranges. These have special semantics that may need consideration.

**Risk Level**: Low - RENAMES is uncommon and the basic case works.

**Example**:
```cobol
       01 WS-RECORD.
          05 WS-FIELD-A PIC X(10).
          05 WS-FIELD-B PIC X(20).
       66 WS-COMBINED RENAMES WS-FIELD-A THRU WS-FIELD-B.
```

**Current Behavior**:
- 66-level items are classified as DATA_NAME
- RENAMES targets are tracked (similar to REDEFINES)
- Basic case works correctly

**Gap**: Complex RENAMES scenarios may not be fully tested.

**Recommendation**:
1. Add comprehensive tests for RENAMES scenarios
2. Ensure RENAMES target references are mapped correctly
3. Document any limitations

**Implementation Complexity**: Low

---

### 8. System Identifier Prefixes Hardcoded

**Status**: Implemented with hardcoded list

**Issue**: System identifiers (EIBXXX, DFHXXX, SQLXXX) are excluded from anonymization based on a hardcoded prefix list. Custom system identifiers may not be recognized.

**Risk Level**: Low - Hardcoded list covers common cases.

**Example**:
- CICS: `DFHCOMMAREA`, `EIBAID`, `EIBTRNID`
- DB2: `SQLCA`, `SQLCODE`, `SQLSTATE`
- Custom: `MYCO-SYSTEM-VAR` (not recognized)

**Current Behavior**:
- `SYSTEM_PREFIXES` set in `reserved_words.py`
- Items matching prefixes are not anonymized
- Custom prefixes are not configurable

**Recommendation**:
1. Add config option: `system_prefixes: list[str]`
2. Allow users to add custom prefixes
3. Document default prefixes in configuration

**Implementation Complexity**: Low

---

## Additional Considerations

### 10. Literal Strings

**Status**: Needs revision

**Issue**: String literals may contain business-specific text that reveals context.

**Example**:
```cobol
           MOVE 'CUSTOMER ACCOUNT BALANCE' TO WS-TITLE.
           DISPLAY 'Processing loan application...'.
```

**Current Behavior**:
- Option `anonymize_literals` controls this
- When enabled, literals are replaced with generic text
- Length is preserved to maintain data structure

**Revised Requirement**:
String literals should be anonymized using a **naming scheme chosen randomly** but **different from the main naming scheme** used for identifiers. The replacement must maintain the **exact same length** as the original string.

**Example** (if main scheme is NUMERIC, literals might use ANIMALS):
```cobol
           MOVE 'FLUFFY-LLAMA-GRUMPY-PEN' TO WS-TITLE.
           DISPLAY 'SNEAKY-PENGUIN-HAPPY-DOL...'.
```

**Implementation Details**:
1. When anonymization starts, randomly select a naming scheme for literals that is different from the main scheme
2. Generate replacement text using the selected scheme
3. Pad or truncate to match exact original length
4. Maintain determinism using seed (if provided)

**Recommendation**:
1. Add `literal_naming_scheme` internal selection (random, different from main)
2. Implement length-preserving literal replacement using naming scheme words
3. Ensure deterministic output with seed parameter

---

### 11. Numeric Literals

**Status**: Not anonymized

**Issue**: Specific numeric values (especially large ones) could be identifying.

**Example**:
```cobol
           IF WS-ACCOUNT > 1234567890
           IF WS-AMOUNT > 999999.99
```

**Risk Level**: Very Low - Numbers rarely identify specific code.

**Recommendation**: No action needed. Numeric literals are typically structural.

---

### 12. PERFORM...THRU Ranges

**Status**: Implemented

**Issue**: PERFORM...THRU specifies a range of paragraphs to execute.

**Example**:
```cobol
           PERFORM 1000-INIT THRU 1000-INIT-EXIT.
```

**Current Behavior**: Both paragraph names are classified and anonymized.

**Recommendation**: Verify with tests that both endpoints are consistently mapped.

---

## Summary Table

| # | Gap | Priority | Status | Complexity |
|---|-----|----------|--------|------------|
| 1 | File names not anonymized | High | Planned | Medium |
| 2 | CALL statement targets | High | Not implemented | Medium |
| 3 | EXTERNAL items protected (should be anonymized) | High | Needs revision | Low |
| 4 | COPY REPLACING parameters | Medium | Partial | Medium |
| 5 | EXTERNAL consistency across files | Medium | Needs revision | Low |
| 6 | ALTER statement targets | Low | Not implemented | Low |
| 7 | RENAMES (66-level) | Low | Basic only | Low |
| 8 | System identifier prefixes | Low | Hardcoded | Low |
| 10 | String literals (use random naming scheme) | Medium | Needs revision | Medium |

---

## Recommended Action Plan

### Immediate (with file name anonymization)
1. Implement file name anonymization (Gap #1)
2. Add COPY statement transformation (required for #1)
3. **Remove EXTERNAL protection** - anonymize EXTERNAL items (Gap #3, #5)
4. Implement string literal anonymization with random naming scheme (Gap #10)

### Short-term
5. Implement CALL statement target anonymization (Gap #2)
6. Track COPY REPLACING parameters (Gap #4)

### Medium-term
7. Add configurable system prefixes (Gap #8)

### Long-term / As-needed
8. ALTER statement handling (Gap #6)
9. Enhanced RENAMES testing (Gap #7)

---

## Verification Approach

For each gap addressed:
1. Write unit tests covering the gap scenario
2. Add integration test with real-world sample
3. Update mapping report to track the fix
4. Document the change in release notes
5. Run full regression test suite

---

## Conclusion

The current COBOL anonymizer provides strong anonymization for most identifier types, including proper handling of comments. The most significant remaining gaps are:

1. **File names** - Critical for complete anonymization
2. **CALL targets** - Important for cross-program references
3. **EXTERNAL items** - Currently protected but should be anonymized
4. **String literals** - Should use a random naming scheme (different from main scheme) with same length

### Key Refinements

Based on review, the anonymization strategy has been refined:

- **No user-defined names should be protected** - Only standard COBOL system names (SQLCA, EIBXXX, DFHXXX, etc.) should remain unchanged
- **EXTERNAL items must be anonymized** - The mapping table ensures cross-file consistency
- **String literals use a different naming scheme** - Randomly selected at runtime, different from the main scheme, with exact length preservation

Addressing these gaps will significantly strengthen the anonymization and make it much harder to link anonymized code to its original source.
