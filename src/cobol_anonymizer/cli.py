"""
Command-Line Interface for COBOL Anonymizer.

This module provides the command-line interface for the COBOL anonymization tool.

Usage:
    cobol-anonymize --input original/ --output anonymized/
    cobol-anonymize --input original/ --output anonymized/ --verbose
    cobol-anonymize --input original/ --output anonymized/ --validate-only
    cobol-anonymize --input original/ --output anonymized/ --dry-run
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional

from cobol_anonymizer import __version__
from cobol_anonymizer.config import Config, create_default_config
from cobol_anonymizer.core.anonymizer import Anonymizer
from cobol_anonymizer.output.validator import OutputValidator
from cobol_anonymizer.output.report import ReportGenerator, create_summary_report


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="cobol-anonymize",
        description="Anonymize COBOL source code while preserving structure and logic.",
        epilog="For more information, see the project documentation.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    # Input/Output
    parser.add_argument(
        "-i", "--input",
        type=Path,
        required=True,
        help="Input directory containing COBOL source files",
        metavar="DIR",
    )

    parser.add_argument(
        "-o", "--output",
        type=Path,
        required=True,
        help="Output directory for anonymized files",
        metavar="DIR",
    )

    parser.add_argument(
        "-c", "--config",
        type=Path,
        help="Configuration file (JSON)",
        metavar="FILE",
    )

    parser.add_argument(
        "--copybook-path",
        type=Path,
        action="append",
        default=[],
        help="Additional path to search for copybooks (can be specified multiple times)",
        metavar="DIR",
    )

    # Mapping options
    parser.add_argument(
        "--mapping-file",
        type=Path,
        help="Path to save/load mapping table (JSON)",
        metavar="FILE",
    )

    parser.add_argument(
        "--load-mappings",
        type=Path,
        help="Load existing mappings from file",
        metavar="FILE",
    )

    # Anonymization options
    parser.add_argument(
        "--no-programs",
        action="store_true",
        help="Don't anonymize program names",
    )

    parser.add_argument(
        "--no-copybooks",
        action="store_true",
        help="Don't anonymize copybook names",
    )

    parser.add_argument(
        "--no-data",
        action="store_true",
        help="Don't anonymize data names",
    )

    parser.add_argument(
        "--no-paragraphs",
        action="store_true",
        help="Don't anonymize paragraph names",
    )

    parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Don't anonymize comments",
    )

    parser.add_argument(
        "--strip-comments",
        action="store_true",
        help="Remove comment content entirely",
    )

    parser.add_argument(
        "--no-preserve-external",
        action="store_true",
        help="Don't preserve EXTERNAL item names",
    )

    # Run modes
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process files but don't write output",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate files, don't transform",
    )

    # Output options
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress normal output",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files",
    )

    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for deterministic output",
        metavar="N",
    )

    parser.add_argument(
        "--encoding",
        default="latin-1",
        help="File encoding (default: latin-1)",
    )

    return parser


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = create_parser()
    return parser.parse_args(args)


def args_to_config(args: argparse.Namespace) -> Config:
    """Convert parsed arguments to Config object."""
    config = create_default_config()

    config.input_dir = args.input
    config.output_dir = args.output
    config.copybook_paths = args.copybook_path or []
    config.mapping_file = args.mapping_file

    config.anonymize_programs = not args.no_programs
    config.anonymize_copybooks = not args.no_copybooks
    config.anonymize_data = not args.no_data
    config.anonymize_paragraphs = not args.no_paragraphs
    config.anonymize_comments = not args.no_comments
    config.strip_comments = args.strip_comments
    config.preserve_external = not args.no_preserve_external

    config.dry_run = args.dry_run
    config.validate_only = args.validate_only
    config.verbose = args.verbose
    config.quiet = args.quiet
    config.overwrite = args.overwrite
    config.seed = args.seed
    config.encoding = args.encoding

    # Load config file if provided
    if args.config and args.config.exists():
        file_config = Config.load_from_file(args.config)
        # Command-line args override file config
        from cobol_anonymizer.config import merge_configs
        config = merge_configs(file_config, config)

    return config


def run_validation(config: Config) -> int:
    """
    Run validation only.

    Returns:
        Exit code (0 for success, 1 for errors)
    """
    if not config.quiet:
        print(f"Validating files in {config.input_dir}...")

    validator = OutputValidator()
    result = validator.validate_directory(config.input_dir)

    if not config.quiet:
        print(f"Validated {result.files_validated} files, {result.lines_validated} lines")
        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for error in result.errors:
                print(f"  {error}")
        if result.warnings:
            print(f"\nWarnings ({len(result.warnings)}):")
            for warning in result.warnings[:10]:  # Limit to first 10
                print(f"  {warning}")
            if len(result.warnings) > 10:
                print(f"  ... and {len(result.warnings) - 10} more")

    return 0 if result.is_valid else 1


def run_anonymization(config: Config) -> int:
    """
    Run the full anonymization pipeline.

    Returns:
        Exit code (0 for success, 1 for errors)
    """
    start_time = time.time()

    if not config.quiet:
        print(f"COBOL Anonymizer v{__version__}")
        print(f"Input: {config.input_dir}")
        print(f"Output: {config.output_dir}")
        print()

    try:
        # Create anonymizer
        anonymizer = Anonymizer(
            source_directory=config.input_dir,
            output_directory=config.output_dir if not config.dry_run else None,
        )

        # Add copybook search paths
        for path in config.copybook_paths:
            anonymizer.copy_resolver.add_search_path(path)

        # Load existing mappings if specified
        if hasattr(config, 'load_mappings') and config.load_mappings:
            if config.load_mappings.exists():
                anonymizer.load_mappings(config.load_mappings)
                if config.verbose:
                    print(f"Loaded mappings from {config.load_mappings}")

        # Discover files
        if config.verbose:
            print("Discovering files...")
        files = anonymizer.discover_files()

        if not config.quiet:
            print(f"Found {len(files)} files to process")

        if config.verbose:
            for f in files:
                print(f"  {f}")

        # Process files
        results = []
        for i, file_path in enumerate(files, 1):
            if config.verbose:
                print(f"Processing [{i}/{len(files)}] {file_path.name}...")

            # Classify identifiers
            identifiers = anonymizer.classify_file(file_path)

            # Build mappings
            anonymizer.build_mappings(identifiers)

            # Transform file
            if not config.validate_only:
                result = anonymizer.anonymize_file(file_path)
                results.append(result)

                if config.verbose:
                    print(f"  Transformed {result.transformed_lines}/{result.total_lines} lines")

        # Save mappings
        if config.mapping_file and not config.dry_run:
            anonymizer.save_mappings(config.mapping_file)
            if not config.quiet:
                print(f"Saved mappings to {config.mapping_file}")

        # Generate report
        elapsed = time.time() - start_time
        if not config.quiet and results:
            summary = create_summary_report(results, anonymizer.mapping_table)
            print()
            print(summary)
            print(f"\nCompleted in {elapsed:.2f} seconds")

        return 0

    except Exception as e:
        if config.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for CLI.

    Args:
        args: Command-line arguments (uses sys.argv if None)

    Returns:
        Exit code
    """
    parsed = parse_args(args)
    config = args_to_config(parsed)

    # Validate configuration
    errors = config.validate()
    if errors:
        for error in errors:
            print(f"Configuration error: {error}", file=sys.stderr)
        return 1

    # Run appropriate mode
    if config.validate_only:
        return run_validation(config)
    else:
        return run_anonymization(config)


if __name__ == "__main__":
    sys.exit(main())
