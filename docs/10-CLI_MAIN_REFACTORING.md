# CLI and Main Module Refactoring

## Problem

The `cli.py` and `main.py` modules contain duplicated logic for running the anonymization pipeline. This violates the DRY principle and creates maintenance burden - changes must be made in two places.

## Current Duplication

### cli.py `run_anonymization()` (lines 264-361)

```python
def run_anonymization(config: Config) -> int:
    anonymizer = Anonymizer(
        source_directory=config.input_dir,
        output_directory=config.output_dir if not config.dry_run else None,
        naming_scheme=config.naming_scheme,
    )
    for path in config.copybook_paths:
        anonymizer.copy_resolver.add_search_path(path)
    files = anonymizer.discover_files()
    for file_path in files:
        identifiers = anonymizer.classify_file(file_path)
        anonymizer.build_mappings(identifiers)
        result = anonymizer.anonymize_file(file_path)
    anonymizer.save_mappings(mapping_file)
    anonymizer.save_mappings_csv(csv_file)
    # ... report generation
```

### main.py `AnonymizationPipeline.run()` (lines 90-165)

```python
def run(self) -> AnonymizationResult:
    self.anonymizer = Anonymizer(
        source_directory=self.config.input_dir,
        output_directory=self.config.output_dir if not self.config.dry_run else None,
    )
    for path in self.config.copybook_paths:
        self.anonymizer.copy_resolver.add_search_path(path)
    files = self.anonymizer.discover_files()
    for file_path in files:
        identifiers = self.anonymizer.classify_file(file_path)
        self.anonymizer.build_mappings(identifiers)
        result = self.anonymizer.anonymize_file(file_path)
    self.anonymizer.save_mappings(self.config.mapping_file)
    self.anonymizer.save_mappings_csv(csv_file)
    # ... report generation
```

### Differences

| Feature | cli.py | main.py |
|---------|--------|---------|
| Naming scheme | Passes to Anonymizer | Does not pass |
| Load mappings | Supports `--load-mappings` | Does not support |
| Default mapping file | `output_dir/mappings.json` | Only if config.mapping_file set |
| Output validation | No | Yes |
| Return type | `int` (exit code) | `AnonymizationResult` |
| Console output | Verbose printing | None |

## Refactoring Design

### Approach: Single Pipeline Implementation

Make `AnonymizationPipeline` the single source of truth. Update `cli.py` to use the pipeline instead of reimplementing the logic.

### Changes to main.py

1. **Add naming_scheme support to AnonymizationPipeline.setup()**:
   ```python
   self.anonymizer = Anonymizer(
       source_directory=self.config.input_dir,
       output_directory=self.config.output_dir if not self.config.dry_run else None,
       naming_scheme=self.config.naming_scheme,  # Add this
   )
   ```

2. **Add load_mappings support**:
   ```python
   if self.config.load_mappings and self.config.load_mappings.exists():
       self.anonymizer.load_mappings(self.config.load_mappings)
   ```

3. **Add default mapping file behavior**:
   ```python
   mapping_file = self.config.mapping_file
   if mapping_file is None and not self.config.dry_run:
       mapping_file = self.config.output_dir / "mappings.json"
   ```

4. **Add progress callback for verbose output**:
   ```python
   def run(self, on_file_start=None, on_file_complete=None) -> AnonymizationResult:
       for file_path in files:
           if on_file_start:
               on_file_start(file_path, i, len(files))
           # ... process file
           if on_file_complete:
               on_file_complete(file_path, file_result)
   ```

### Changes to cli.py

Replace `run_anonymization()` implementation with:

```python
def run_anonymization(config: Config) -> int:
    start_time = time.time()

    if not config.quiet:
        print(f"COBOL Anonymizer v{__version__}")
        print(f"Input: {config.input_dir}")
        print(f"Output: {config.output_dir}")
        print()

    # Callbacks for verbose output
    def on_file_start(file_path, index, total):
        if config.verbose:
            print(f"Processing [{index}/{total}] {file_path.name}...")

    def on_file_complete(file_path, result):
        if config.verbose and result:
            print(f"  Transformed {result.transformed_lines}/{result.total_lines} lines")

    def on_files_discovered(files):
        if not config.quiet:
            print(f"Found {len(files)} files to process")
        if config.verbose:
            for f in files:
                print(f"  {f}")

    try:
        pipeline = AnonymizationPipeline(config)
        result = pipeline.run(
            on_file_start=on_file_start,
            on_file_complete=on_file_complete,
            on_files_discovered=on_files_discovered,
        )

        if result.errors:
            for error in result.errors:
                print(f"Error: {error}", file=sys.stderr)
            return 1

        # Print summary
        if not config.quiet and result.file_results:
            summary = create_summary_report(result.file_results, result.mapping_table)
            print()
            print(summary)
            print(f"\nCompleted in {result.processing_time:.2f} seconds")

        return 0

    except Exception as e:
        if config.verbose:
            traceback.print_exc()
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1
```

### Changes to config.py

Add `load_mappings` field if not already present:

```python
@dataclass
class Config:
    # ... existing fields
    load_mappings: Optional[Path] = None
```

## Benefits

1. **Single Source of Truth**: All pipeline logic in `AnonymizationPipeline`
2. **Easier Maintenance**: Changes only need to be made in one place
3. **Testability**: Pipeline can be tested independently of CLI
4. **Flexibility**: Callbacks allow CLI-specific behavior without duplicating core logic
5. **Consistency**: Both CLI and programmatic API use identical processing

## File Changes Summary

| File | Change |
|------|--------|
| `src/cobol_anonymizer/main.py` | Add naming_scheme, load_mappings, default mapping file, callbacks |
| `src/cobol_anonymizer/cli.py` | Replace `run_anonymization()` to use `AnonymizationPipeline` |
| `src/cobol_anonymizer/config.py` | Add `load_mappings` field (if needed) |

## Testing Strategy

1. Run existing test suite to ensure no regressions
2. Manually test CLI with various options
3. Verify both JSON and CSV mapping files are generated
4. Test verbose and quiet modes
