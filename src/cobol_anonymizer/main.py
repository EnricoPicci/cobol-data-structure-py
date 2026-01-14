"""
Main entry point for COBOL Anonymizer.

This module orchestrates the full anonymization pipeline and provides
a programmatic API for the anonymization process.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from cobol_anonymizer.config import Config, create_default_config
from cobol_anonymizer.core.anonymizer import Anonymizer, FileTransformResult
from cobol_anonymizer.core.mapper import MappingTable
from cobol_anonymizer.generators.comment_generator import CommentTransformer, CommentConfig, CommentMode
from cobol_anonymizer.output.writer import OutputWriter, WriterConfig
from cobol_anonymizer.output.validator import OutputValidator, ValidationResult
from cobol_anonymizer.output.report import AnonymizationReport, ReportGenerator

# Type aliases for callbacks
OnFileStartCallback = Callable[[Path, int, int], None]  # (file_path, index, total)
OnFileCompleteCallback = Callable[[Path, Optional[FileTransformResult]], None]
OnFilesDiscoveredCallback = Callable[[List[Path]], None]


@dataclass
class AnonymizationResult:
    """Result of running the full anonymization pipeline."""
    success: bool
    file_results: List[FileTransformResult] = field(default_factory=list)
    mapping_table: Optional[MappingTable] = None
    mapping_file: Optional[Path] = None
    report: Optional[AnonymizationReport] = None
    validation_result: Optional[ValidationResult] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0


class AnonymizationPipeline:
    """
    Orchestrates the full COBOL anonymization pipeline.

    Usage:
        pipeline = AnonymizationPipeline(config)
        result = pipeline.run()
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the pipeline.

        Args:
            config: Configuration object (uses defaults if not provided)
        """
        self.config = config or create_default_config()
        self.anonymizer: Optional[Anonymizer] = None
        self.comment_transformer: Optional[CommentTransformer] = None
        self.writer: Optional[OutputWriter] = None
        self.validator: Optional[OutputValidator] = None

    def setup(self) -> None:
        """Set up pipeline components."""
        # Create anonymizer with naming scheme from config
        self.anonymizer = Anonymizer(
            source_directory=self.config.input_dir,
            output_directory=self.config.output_dir if not self.config.dry_run else None,
            naming_scheme=self.config.naming_scheme,
        )

        # Add copybook search paths
        for path in self.config.copybook_paths:
            self.anonymizer.copy_resolver.add_search_path(path)

        # Load existing mappings if specified
        if self.config.load_mappings and self.config.load_mappings.exists():
            self.anonymizer.load_mappings(self.config.load_mappings)

        # Create comment transformer
        comment_mode = CommentMode.ANONYMIZE
        if self.config.strip_comments:
            comment_mode = CommentMode.STRIP
        elif not self.config.anonymize_comments:
            comment_mode = CommentMode.PRESERVE

        comment_config = CommentConfig(mode=comment_mode)
        self.comment_transformer = CommentTransformer(comment_config)

        # Create writer
        writer_config = WriterConfig(
            output_directory=self.config.output_dir,
            default_encoding=self.config.encoding,
            overwrite_existing=self.config.overwrite,
        )
        self.writer = OutputWriter(writer_config)

        # Create validator
        self.validator = OutputValidator()

    def run(
        self,
        on_file_start: Optional[OnFileStartCallback] = None,
        on_file_complete: Optional[OnFileCompleteCallback] = None,
        on_files_discovered: Optional[OnFilesDiscoveredCallback] = None,
    ) -> AnonymizationResult:
        """
        Run the full anonymization pipeline.

        Args:
            on_file_start: Callback before processing each file (file_path, index, total)
            on_file_complete: Callback after processing each file (file_path, result)
            on_files_discovered: Callback after file discovery (list of files)

        Returns:
            AnonymizationResult with all details
        """
        start_time = time.time()
        result = AnonymizationResult(success=True)

        try:
            # Validate config
            config_errors = self.config.validate()
            if config_errors:
                result.success = False
                result.errors.extend(config_errors)
                return result

            # Set up components
            self.setup()

            # Discover files
            files = self.anonymizer.discover_files()

            # Notify about discovered files
            if on_files_discovered:
                on_files_discovered(files)

            # Process each file
            for i, file_path in enumerate(files, 1):
                # Notify file start
                if on_file_start:
                    on_file_start(file_path, i, len(files))

                try:
                    file_result = self._process_file(file_path)
                    if file_result:
                        result.file_results.append(file_result)

                    # Notify file complete
                    if on_file_complete:
                        on_file_complete(file_path, file_result)
                except Exception as e:
                    result.errors.append(f"Error processing {file_path}: {e}")
                    if self.config.verbose:
                        import traceback
                        result.errors.append(traceback.format_exc())

            # Save mappings (JSON and CSV) - use default path if not specified
            if not self.config.dry_run:
                mapping_file = self.config.mapping_file
                if mapping_file is None:
                    mapping_file = self.config.output_dir / "mappings.json"

                self.anonymizer.save_mappings(mapping_file)
                # Also save CSV version
                csv_file = mapping_file.with_suffix('.csv')
                self.anonymizer.save_mappings_csv(csv_file)

                # Store the actual mapping file path used
                result.mapping_file = mapping_file

            # Validate output
            if not self.config.dry_run and self.config.output_dir.exists():
                result.validation_result = self.validator.validate_directory(
                    self.config.output_dir
                )
                if not result.validation_result.is_valid:
                    result.warnings.extend(
                        str(issue) for issue in result.validation_result.issues
                    )

            # Store mapping table
            result.mapping_table = self.anonymizer.mapping_table

            # Generate report
            elapsed = time.time() - start_time
            result.processing_time = elapsed

            report_generator = ReportGenerator(
                mapping_table=self.anonymizer.mapping_table,
                source_directory=self.config.input_dir,
                output_directory=self.config.output_dir,
            )
            result.report = report_generator.generate_report(
                result.file_results,
                processing_time=elapsed,
            )

        except Exception as e:
            result.success = False
            result.errors.append(f"Pipeline error: {e}")
            result.processing_time = time.time() - start_time

        return result

    def _process_file(self, file_path: Path) -> Optional[FileTransformResult]:
        """Process a single file through the pipeline."""
        # Classify identifiers
        identifiers = self.anonymizer.classify_file(file_path)

        # Build mappings
        self.anonymizer.build_mappings(identifiers)

        # Transform file
        if not self.config.validate_only:
            return self.anonymizer.anonymize_file(file_path)

        return None


def anonymize_directory(
    input_dir: Path,
    output_dir: Path,
    **kwargs,
) -> AnonymizationResult:
    """
    Convenience function to anonymize a directory.

    Args:
        input_dir: Input directory with COBOL files
        output_dir: Output directory for anonymized files
        **kwargs: Additional configuration options

    Returns:
        AnonymizationResult with details
    """
    config = Config(
        input_dir=input_dir,
        output_dir=output_dir,
        **kwargs,
    )
    pipeline = AnonymizationPipeline(config)
    return pipeline.run()


def validate_directory(input_dir: Path) -> ValidationResult:
    """
    Validate COBOL files in a directory.

    Args:
        input_dir: Directory to validate

    Returns:
        ValidationResult with any issues
    """
    validator = OutputValidator()
    return validator.validate_directory(input_dir)
