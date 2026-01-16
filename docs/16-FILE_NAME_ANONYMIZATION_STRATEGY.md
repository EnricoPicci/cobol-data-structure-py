# File Name Anonymization Strategy

## Overview

This document defines the strategy for anonymizing COBOL file names while ensuring the code remains correct and can compile. File name anonymization is the final piece needed to make the anonymized codebase truly unlinkable to the original.

## Problem Statement

The COBOL anonymizer currently transforms:
- Variable names (DATA_NAME)
- Section names (SECTION_NAME)
- Paragraph names (PARAGRAPH_NAME)
- Program IDs (PROGRAM_NAME)
- Copybook references (COPYBOOK_NAME)
- And other identifier types

However, **output file names remain unchanged**, which means:
1. Original file names may reveal business context (e.g., `CUSTOMER_PAYMENT.cob`)
2. File names can be used to correlate anonymized code back to original
3. The anonymization is incomplete from a privacy perspective

## Objectives

1. **Complete anonymization**: File names should be as anonymous as identifiers
2. **Code correctness**: Anonymized code must compile without errors
3. **Consistency**: Use the same naming schemes already available in the tool
4. **Traceability**: Maintain a mapping between original and anonymized file names

---

## Strategy: Naming Scheme Integration

### Core Principle

File names will use the **same naming schemes** (NUMERIC, ANIMALS, FOOD, FANTASY, CORPORATE) already used for identifier anonymization. This ensures:
- Consistency across the anonymized codebase
- Fun, memorable file names (when using non-numeric schemes)
- Deterministic output (same input always produces same output)

### File Type Classification

Files are classified into two categories with different naming approaches:

| File Type | Identifier Type | Detection Method |
|-----------|----------------|------------------|
| Program files (`.cob`, `.cbl`) | `PROGRAM_NAME` | Contains `PROGRAM-ID.` declaration |
| Copybook files (`.cpy`) | `COPYBOOK_NAME` | Referenced in `COPY` statements |

### Naming Scheme Examples

**NUMERIC Scheme** (default):
```
Original                    Anonymized
CUSTOMER-PAYMENT.cob   →   PG000001.cob
ACCOUNT-BALANCE.cob    →   PG000002.cob
COMMON-FIELDS.cpy      →   CP000001.cpy
DATE-ROUTINES.cpy      →   CP000002.cpy
```

**ANIMALS Scheme**:
```
Original                    Anonymized
CUSTOMER-PAYMENT.cob   →   FLUFFY-LLAMA-1.cob
ACCOUNT-BALANCE.cob    →   SNEAKY-PENGUIN-2.cob
COMMON-FIELDS.cpy      →   GRUMPY-KOALA-1.cpy
DATE-ROUTINES.cpy      →   HAPPY-DOLPHIN-2.cpy
```

**FOOD Scheme**:
```
Original                    Anonymized
CUSTOMER-PAYMENT.cob   →   SPICY-TACO-1.cob
ACCOUNT-BALANCE.cob    →   CRISPY-WAFFLE-2.cob
COMMON-FIELDS.cpy      →   TANGY-PICKLE-1.cpy
DATE-ROUTINES.cpy      →   SAVORY-DUMPLING-2.cpy
```

**FANTASY Scheme**:
```
Original                    Anonymized
CUSTOMER-PAYMENT.cob   →   BRAVE-PHOENIX-1.cob
ACCOUNT-BALANCE.cob    →   SNEAKY-DRAGON-2.cob
COMMON-FIELDS.cpy      →   WISE-UNICORN-1.cpy
DATE-ROUTINES.cpy      →   SWIFT-GRIFFIN-2.cpy
```

**CORPORATE Scheme**:
```
Original                    Anonymized
CUSTOMER-PAYMENT.cob   →   AGILE-SYNERGY-1.cob
ACCOUNT-BALANCE.cob    →   LEAN-PIVOT-2.cob
COMMON-FIELDS.cpy      →   DISRUPT-PARADIGM-1.cpy
DATE-ROUTINES.cpy      →   SCALE-LEVERAGE-2.cpy
```

---

## File-to-Identifier Mapping

### Program Files

For files containing a `PROGRAM-ID.` declaration:
1. Extract the PROGRAM-ID value from the source
2. Generate an anonymized name using the configured naming scheme
3. Use the anonymized PROGRAM-ID as the base file name
4. Preserve or standardize the file extension

**Example**:
```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CUSTOMER-PAYMENT.
```
- Original file: `CUSTOMER-PAYMENT.cob`
- PROGRAM-ID: `CUSTOMER-PAYMENT`
- Anonymized PROGRAM-ID: `PG000001` (NUMERIC) or `FLUFFY-LLAMA-1` (ANIMALS)
- Anonymized file: `PG000001.cob` or `FLUFFY-LLAMA-1.cob`

### Copybook Files

For copybook files (no PROGRAM-ID):
1. Identify which COPY statements reference this file
2. Use the copybook name from the COPY statement
3. Generate an anonymized name using COPYBOOK_NAME type
4. Preserve or standardize to `.cpy` extension

**Example**:
```cobol
       COPY COMMON-FIELDS.
```
- Copybook file: `COMMON-FIELDS.cpy`
- Referenced as: `COMMON-FIELDS`
- Anonymized name: `CP000001` (NUMERIC) or `GRUMPY-KOALA-1` (ANIMALS)
- Anonymized file: `CP000001.cpy` or `GRUMPY-KOALA-1.cpy`

### Files Without PROGRAM-ID or COPY Reference

For files that:
- Don't contain a PROGRAM-ID declaration
- Are not referenced by any COPY statement

Use a generic naming approach:
1. Classify based on extension (`.cob`/`.cbl` = program, `.cpy` = copybook)
2. Generate name using appropriate type prefix
3. Flag in report as "orphan" file

---

## COPY Statement Transformation

### The Critical Link

When file names change, COPY statements **must be updated** to reference the new names. Otherwise, the anonymized code won't compile.

### Transformation Process

**Before anonymization**:
```cobol
       COPY COMMON-FIELDS.
       COPY DATE-ROUTINES OF UTILITIES.
       COPY CUSTOMER-REC REPLACING ==:PREFIX:== BY ==WS-==.
```

**After anonymization** (ANIMALS scheme):
```cobol
       COPY GRUMPY-KOALA-1.
       COPY HAPPY-DOLPHIN-2 OF UTILITIES.
       COPY SNEAKY-PENGUIN-3 REPLACING ==:PREFIX:== BY ==D000001-==.
```

### COPY Statement Patterns

The transformer must handle these COPY patterns:

| Pattern | Example | Transformation |
|---------|---------|----------------|
| Simple | `COPY NAME.` | Replace `NAME` with anonymized name |
| With library | `COPY NAME OF LIB.` | Replace `NAME`, keep `LIB` |
| With REPLACING | `COPY NAME REPLACING ...` | Replace `NAME`, anonymize REPLACING patterns |
| Multi-line | `COPY NAME\n    REPLACING ...` | Handle continuation lines |

### REPLACING Clause Handling

The REPLACING clause may contain identifiers that should be anonymized:
```cobol
       COPY TEMPLATE REPLACING ==OLD-PREFIX== BY ==NEW-PREFIX==.
```

Both `OLD-PREFIX` and `NEW-PREFIX` may need anonymization if they represent data names.

---

## Processing Order

### Dependency-Aware Processing

COBOL files have dependencies through COPY statements. The anonymization must process files in the correct order:

1. **Scan all files**: Build complete file inventory
2. **Extract PROGRAM-IDs**: Identify program files and their IDs
3. **Build COPY graph**: Map which files COPY which copybooks
4. **Topological sort**: Order files so copybooks are processed before programs
5. **Generate mappings**: Create file name mappings for all files
6. **Transform code**: Update COPY statements in dependency order
7. **Write files**: Write with anonymized names

### Why Order Matters

```
MAIN-PROGRAM.cob
    └── COPY COMMON-DATA.cpy
             └── COPY BASIC-TYPES.cpy
```

Processing order must be:
1. `BASIC-TYPES.cpy` → `CP000001.cpy`
2. `COMMON-DATA.cpy` → `CP000002.cpy` (update COPY BASIC-TYPES to COPY CP000001)
3. `MAIN-PROGRAM.cob` → `PG000001.cob` (update COPY COMMON-DATA to COPY CP000002)

---

## Edge Cases

### Multiple Extensions

Some codebases use varied extensions:
- Programs: `.cob`, `.cbl`, `.cobol`, `.COB`, `.CBL`
- Copybooks: `.cpy`, `.copy`, `.CPY`, `.COPY`

**Strategy**: Normalize to `.cob` for programs and `.cpy` for copybooks, or preserve original.

### Case Sensitivity

COBOL is case-insensitive, but file systems may be case-sensitive.

**Strategy**:
- Use uppercase for anonymized names (COBOL convention)
- Handle case-insensitive matching when linking COPY statements to files

### Duplicate Names After Anonymization

Different original names could theoretically map to the same anonymized name.

**Prevention**:
- Use unique counters per file type
- Naming schemes already ensure uniqueness via counter suffix

### Circular COPY Dependencies

```
A.cpy COPY B.
B.cpy COPY A.
```

**Strategy**: Detect during scanning (already implemented), raise error with clear message.

### Files Not in Source Directory

COPY statements may reference files in different directories or library paths.

**Strategy**:
- Resolve using copybook search paths
- Only anonymize files in the source directory
- Update COPY statements to reference anonymized names

---

## Configuration Options

### New Configuration Fields

```python
@dataclass
class Config:
    # Existing fields...

    # File name anonymization
    anonymize_file_names: bool = True  # Enable/disable file renaming
    normalize_extensions: bool = False  # Standardize to .cob/.cpy
    preserve_directory_structure: bool = True  # Keep subdirectories
```

### CLI Options

```bash
# Enable file name anonymization (default)
cobol-anonymize --input src/ --output out/

# Disable file name anonymization
cobol-anonymize --input src/ --output out/ --no-file-names

# Normalize extensions
cobol-anonymize --input src/ --output out/ --normalize-extensions
```

---

## Mapping Report

### File Name Mappings

The mapping report should include a dedicated section for file names:

```json
{
  "file_mappings": [
    {
      "original_path": "src/CUSTOMER-PAYMENT.cob",
      "anonymized_name": "PG000001.cob",
      "program_id": "CUSTOMER-PAYMENT",
      "anonymized_program_id": "PG000001"
    },
    {
      "original_path": "src/copybooks/COMMON-FIELDS.cpy",
      "anonymized_name": "CP000001.cpy",
      "copybook_name": "COMMON-FIELDS",
      "referenced_by": ["CUSTOMER-PAYMENT.cob", "ACCOUNT-BALANCE.cob"]
    }
  ]
}
```

### CSV Export

```csv
original_file,anonymized_file,type,identifier
CUSTOMER-PAYMENT.cob,PG000001.cob,program,CUSTOMER-PAYMENT
COMMON-FIELDS.cpy,CP000001.cpy,copybook,COMMON-FIELDS
```

---

## Validation

### Post-Anonymization Checks

1. **COPY reference validity**: Every COPY statement references an existing file
2. **No duplicate file names**: All anonymized names are unique
3. **Valid file names**: No special characters that break file systems
4. **Length limits**: File names don't exceed system limits (typically 255 chars)
5. **COBOL identifier rules**: Base name follows COBOL identifier rules (30 chars, no trailing hyphen)

### Compilation Test

The ultimate validation is that the anonymized code compiles:
```bash
# Example with GnuCOBOL
cobc -x anonymized/*.cob
```

---

## Related Anonymization Refinements

### EXTERNAL Items

**Revised Policy**: EXTERNAL items are **no longer protected** from anonymization.

- **Previous behavior**: EXTERNAL items were preserved unchanged
- **New behavior**: EXTERNAL items are anonymized like any other identifier
- **Consistency**: The mapping table ensures the same original name maps to the same anonymized name across all files
- **Protected names**: Only standard COBOL system names (SQLCA, SQLCODE, EIBXXX, DFHXXX, etc.) remain protected

This change ensures maximum anonymization while maintaining cross-file linkage through consistent mapping.

### String Literal Anonymization

**Revised Policy**: String literals use a **randomly selected naming scheme** (different from the main scheme) with **exact length preservation**.

**Example** (if main scheme is NUMERIC):
```cobol
* Before:
           MOVE 'CUSTOMER ACCOUNT BALANCE' TO WS-TITLE.

* After (using ANIMALS scheme for literals):
           MOVE 'FLUFFY-LLAMA-GRUMPY-PEN' TO WS-TITLE.
```

**Implementation Details**:
1. At anonymization start, randomly select a naming scheme for literals (different from main scheme)
2. Use words from the selected scheme to generate replacement text
3. Pad or truncate to match exact original length
4. Maintain determinism using seed parameter (if provided)

This ensures string literals don't reveal business context while maintaining visual consistency.

---

## Summary

| Aspect | Strategy |
|--------|----------|
| Naming approach | Use same naming schemes as identifiers |
| Program files | Name based on anonymized PROGRAM-ID |
| Copybook files | Name based on anonymized copybook reference |
| COPY statements | Transform to reference new file names |
| Processing order | Topological sort (dependencies first) |
| Extensions | Preserve or normalize based on config |
| EXTERNAL items | Anonymized (not protected) |
| String literals | Random naming scheme, same length |
| Validation | Check COPY references, compile test |

This strategy ensures complete anonymization while maintaining code correctness and providing traceability through the mapping report.
