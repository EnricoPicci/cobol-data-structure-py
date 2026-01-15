# CSV Export Implementation Plan

**Status: IMPLEMENTED** (2026-01-14)

## Overview

This document describes the plan to add CSV export functionality for the mappings file, complementing the existing JSON export.

The feature is now implemented:
- `MappingTable.save_to_csv()` method in `core/mapper.py`
- `Anonymizer.save_mappings_csv()` method in `core/anonymizer.py`
- CLI automatically generates both `mappings.json` and `mappings.csv`
- 12 comprehensive tests in `tests/test_csv_export.py`

## Current mappings.json Structure

The current `mappings.json` file contains:

```json
{
  "generated_at": "2026-01-14T09:13:07.223877",
  "naming_scheme": "corporate",
  "mappings": [
    {
      "original_name": "AF64-DATI-INTERFACCIA",
      "anonymized_name": "NIMBLE-PARADIGM-1",
      "id_type": "DATA_NAME",
      "is_external": false,
      "first_seen_file": null,
      "first_seen_line": null,
      "occurrence_count": 2
    }
  ],
  "external_names": ["MSSPA-AREA", "MSMFS-SPAUSER"],
  "generator_state": {
    "DATA_NAME": 3586,
    "CONDITION_NAME": 537
  }
}
```

## Proposed CSV Format

### Primary CSV File: `mappings.csv`

A flat table containing all mapping entries with metadata columns:

| Column | Type | Description |
|--------|------|-------------|
| `original_name` | string | Original COBOL identifier |
| `anonymized_name` | string | Generated anonymized name |
| `id_type` | string | Identifier type (DATA_NAME, PROGRAM_NAME, etc.) |
| `is_external` | boolean | True if marked EXTERNAL |
| `first_seen_file` | string | Source file path (empty if null) |
| `first_seen_line` | integer | Line number (empty if null) |
| `occurrence_count` | integer | Number of occurrences |
| `naming_scheme` | string | Naming scheme used (repeated per row for completeness) |
| `generated_at` | ISO datetime | Timestamp of generation (repeated per row) |

### Example CSV Output

```csv
original_name,anonymized_name,id_type,is_external,first_seen_file,first_seen_line,occurrence_count,naming_scheme,generated_at
AF64-DATI-INTERFACCIA,NIMBLE-PARADIGM-1,DATA_NAME,false,,,2,corporate,2026-01-14T09:13:07.223877
AF64-DATI-INTERFACCIA-R,SYNERGY-CHANNEL-2,DATA_NAME,false,,,2,corporate,2026-01-14T09:13:07.223877
MSSPA-AREA,MSSPA-AREA,EXTERNAL_NAME,true,,,1,corporate,2026-01-14T09:13:07.223877
```

### Design Decisions

1. **Flat structure**: CSV inherently requires flat data. Each mapping entry becomes one row.

2. **External names included**: External names are included in the main CSV with `is_external=true` and `anonymized_name` equal to `original_name`.

3. **Metadata repeated per row**: `naming_scheme` and `generated_at` are repeated in each row. This enables filtering/sorting while keeping all data in one file.

4. **Generator state omitted**: The `generator_state` is internal implementation detail for resuming generation. It's not meaningful for CSV consumers and can be derived from the mappings if needed.

5. **Null handling**: Null values in `first_seen_file` and `first_seen_line` are represented as empty strings.

6. **Boolean format**: `is_external` uses lowercase `true`/`false` strings.

## Implementation Plan

### Phase 1: Add CSV Export Method to MappingTable

**File**: `src/cobol_anonymizer/core/mapper.py`

Add a new method `save_to_csv()` to the `MappingTable` class:

```python
def save_to_csv(self, path: Path) -> None:
    """Save mappings to a CSV file.

    Args:
        path: Output file path for the CSV
    """
    import csv
    from datetime import datetime

    timestamp = datetime.now().isoformat()
    scheme_name = self._generator.scheme.value

    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow([
            'original_name',
            'anonymized_name',
            'id_type',
            'is_external',
            'first_seen_file',
            'first_seen_line',
            'occurrence_count',
            'naming_scheme',
            'generated_at'
        ])

        # Write mapping entries
        for entry in self._mappings.values():
            writer.writerow([
                entry.original_name,
                entry.anonymized_name,
                entry.id_type.name,
                str(entry.is_external).lower(),
                entry.first_seen_file or '',
                entry.first_seen_line if entry.first_seen_line is not None else '',
                entry.occurrence_count,
                scheme_name,
                timestamp
            ])

        # Write external names (that weren't already in mappings)
        for ext_name in self._external_names:
            if ext_name.upper() not in self._mappings:
                writer.writerow([
                    ext_name,
                    ext_name,  # External names keep original
                    'EXTERNAL_NAME',
                    'true',
                    '',
                    '',
                    0,
                    scheme_name,
                    timestamp
                ])
```

### Phase 2: Update CLI to Support CSV Output

**File**: `src/cobol_anonymizer/cli.py`

Add a new CLI option `--csv-mapping-file` or modify existing `--mapping-file` behavior:

**Option A**: New separate flag
```python
@click.option(
    '--csv-mapping-file',
    type=click.Path(dir_okay=False, path_type=Path),
    help='Path to write CSV mapping file (optional)',
)
```

**Option B**: Auto-generate CSV alongside JSON
- When `--mapping-file` is specified, automatically generate both `mappings.json` and `mappings.csv`
- The CSV file uses the same base name with `.csv` extension

**Recommended**: Option B (auto-generate) for simplicity, with the option to disable via `--no-csv`.

### Phase 3: Update Main Pipeline

**File**: `src/cobol_anonymizer/main.py`

After calling `mapping_table.save_to_file()`, also call `mapping_table.save_to_csv()`:

```python
# Save mapping file (existing)
if config.mapping_file:
    mapping_table.save_to_file(config.mapping_file)

    # Save CSV version
    csv_path = config.mapping_file.with_suffix('.csv')
    mapping_table.save_to_csv(csv_path)
```

### Phase 4: Add Tests

**File**: `tests/test_csv_export.py` (new file)

Test cases to add:
1. Basic CSV export with sample mappings
2. CSV export with external names
3. CSV export with null values in first_seen_file/line
4. CSV export with special characters in identifiers
5. Verify CSV is valid and parseable
6. Verify CSV contains all mappings from JSON
7. Round-trip test: JSON -> load -> CSV matches expected

### Phase 5: Update Documentation

**Files to update**:
- `README.md`: Document new CSV output
- `CLAUDE.md`: Add CSV export to quick commands
- CLI help text

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `src/cobol_anonymizer/core/mapper.py` | Modify | Add `save_to_csv()` method |
| `src/cobol_anonymizer/cli.py` | Modify | Add CSV option or auto-generation |
| `src/cobol_anonymizer/main.py` | Modify | Call CSV export in pipeline |
| `src/cobol_anonymizer/config.py` | Modify | Add `csv_mapping_file` config option (if needed) |
| `tests/test_csv_export.py` | New | CSV export tests |
| `README.md` | Modify | Document CSV feature |

## Testing Strategy

1. **Unit tests**: Test `save_to_csv()` method in isolation
2. **Integration tests**: Run full anonymization and verify CSV output
3. **Manual testing**: Run CLI and inspect generated CSV files
4. **Comparison test**: Verify CSV and JSON contain equivalent data

## Rollout Plan

1. Implement `save_to_csv()` method with tests
2. Add CLI support
3. Update pipeline integration
4. Update documentation
5. Release

## Future Considerations

- **CSV import**: Could add `load_from_csv()` for restoring mappings from CSV
- **Excel format**: Could add `.xlsx` export for spreadsheet users
- **Configurable columns**: Could allow users to select which columns to include
- **Statistics CSV**: Separate CSV with aggregated statistics by identifier type
