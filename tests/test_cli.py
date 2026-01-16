"""
Tests for Phase 10: CLI and Configuration.

Tests for command-line interface and configuration handling.
"""

import json
from pathlib import Path

import pytest

from unittest.mock import patch

from cobol_anonymizer.cli import (
    args_to_config,
    clear_directory,
    create_parser,
    is_directory_non_empty,
    main,
    parse_args,
    prompt_user_confirmation,
)
from cobol_anonymizer.config import (
    Config,
    create_default_config,
    merge_configs,
)
from cobol_anonymizer.main import (
    AnonymizationPipeline,
    AnonymizationResult,
    anonymize_directory,
    validate_directory,
)


class TestConfig:
    """Tests for Config dataclass."""

    def test_create_default_config(self):
        """Create config with default values."""
        config = create_default_config()
        assert config is not None
        assert config.encoding == "latin-1"
        assert config.preserve_external is False

    def test_config_to_dict(self):
        """Convert config to dictionary."""
        config = Config(
            input_dir=Path("/input"),
            output_dir=Path("/output"),
        )
        data = config.to_dict()
        assert data["input_dir"] == "/input"
        assert data["output_dir"] == "/output"

    def test_config_from_dict(self):
        """Create config from dictionary."""
        data = {
            "input_dir": "/input",
            "output_dir": "/output",
            "encoding": "utf-8",
        }
        config = Config.from_dict(data)
        assert config.input_dir == Path("/input")
        assert config.encoding == "utf-8"

    def test_config_save_and_load(self, tmp_path):
        """Save and load config from file."""
        config = Config(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            encoding="utf-8",
            verbose=True,
        )

        config_file = tmp_path / "config.json"
        config.save_to_file(config_file)

        loaded = Config.load_from_file(config_file)
        assert loaded.encoding == "utf-8"
        assert loaded.verbose is True

    def test_config_validate_valid(self, tmp_path):
        """Valid config passes validation."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        config = Config(
            input_dir=input_dir,
            output_dir=tmp_path / "output",
        )
        errors = config.validate()
        assert len(errors) == 0

    def test_config_validate_missing_input(self, tmp_path):
        """Missing input directory fails validation."""
        config = Config(
            input_dir=tmp_path / "nonexistent",
            output_dir=tmp_path / "output",
        )
        errors = config.validate()
        assert len(errors) > 0
        assert any("does not exist" in e for e in errors)

    def test_config_is_valid(self, tmp_path):
        """is_valid returns correct status."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        config = Config(
            input_dir=input_dir,
            output_dir=tmp_path / "output",
        )
        assert config.is_valid()


class TestMergeConfigs:
    """Tests for config merging."""

    def test_merge_override_wins(self):
        """Override config takes precedence."""
        base = Config(encoding="latin-1", verbose=False)
        override = Config(encoding="utf-8", verbose=True)

        merged = merge_configs(base, override)
        assert merged.encoding == "utf-8"
        assert merged.verbose is True

    def test_merge_keeps_base_defaults(self):
        """Base values kept when override is default."""
        base = Config(encoding="utf-8")
        override = Config()  # All defaults

        merged = merge_configs(base, override)
        assert merged.encoding == "utf-8"


class TestArgParser:
    """Tests for argument parser."""

    def test_create_parser(self):
        """Create argument parser."""
        parser = create_parser()
        assert parser is not None

    def test_parse_required_args(self, tmp_path):
        """Parse required arguments."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        args = parse_args(
            [
                "--input",
                str(input_dir),
                "--output",
                str(tmp_path / "output"),
            ]
        )
        assert args.input == input_dir
        assert args.output == tmp_path / "output"

    def test_parse_verbose(self, tmp_path):
        """Parse verbose flag."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        args = parse_args(
            [
                "--input",
                str(input_dir),
                "--output",
                str(tmp_path / "output"),
                "--verbose",
            ]
        )
        assert args.verbose is True

    def test_parse_dry_run(self, tmp_path):
        """Parse dry-run flag."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        args = parse_args(
            [
                "--input",
                str(input_dir),
                "--output",
                str(tmp_path / "output"),
                "--dry-run",
            ]
        )
        assert args.dry_run is True

    def test_parse_validate_only(self, tmp_path):
        """Parse validate-only flag."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        args = parse_args(
            [
                "--input",
                str(input_dir),
                "--output",
                str(tmp_path / "output"),
                "--validate-only",
            ]
        )
        assert args.validate_only is True

    def test_parse_no_comments(self, tmp_path):
        """Parse no-comments flag."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        args = parse_args(
            [
                "--input",
                str(input_dir),
                "--output",
                str(tmp_path / "output"),
                "--no-comments",
            ]
        )
        assert args.no_comments is True

    def test_parse_encoding(self, tmp_path):
        """Parse encoding option."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        args = parse_args(
            [
                "--input",
                str(input_dir),
                "--output",
                str(tmp_path / "output"),
                "--encoding",
                "utf-8",
            ]
        )
        assert args.encoding == "utf-8"

    def test_parse_seed(self, tmp_path):
        """Parse seed option."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        args = parse_args(
            [
                "--input",
                str(input_dir),
                "--output",
                str(tmp_path / "output"),
                "--seed",
                "42",
            ]
        )
        assert args.seed == 42


class TestArgsToConfig:
    """Tests for converting args to config."""

    def test_basic_conversion(self, tmp_path):
        """Convert basic args to config."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        args = parse_args(
            [
                "--input",
                str(input_dir),
                "--output",
                str(tmp_path / "output"),
            ]
        )
        config = args_to_config(args)

        assert config.input_dir == input_dir
        assert config.output_dir == tmp_path / "output"

    def test_flags_conversion(self, tmp_path):
        """Convert flags to config."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        args = parse_args(
            [
                "--input",
                str(input_dir),
                "--output",
                str(tmp_path / "output"),
                "--no-programs",
                "--no-comments",
                "--dry-run",
                "--verbose",
            ]
        )
        config = args_to_config(args)

        assert config.anonymize_programs is False
        assert config.anonymize_comments is False
        assert config.dry_run is True
        assert config.verbose is True


class TestMainFunction:
    """Tests for main CLI entry point."""

    def test_main_missing_args(self):
        """Main returns error for missing args."""
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code != 0

    def test_main_missing_input(self, tmp_path):
        """Main returns error for missing input dir."""
        result = main(
            [
                "--input",
                str(tmp_path / "nonexistent"),
                "--output",
                str(tmp_path / "output"),
            ]
        )
        assert result == 1

    def test_main_validate_only(self, tmp_path):
        """Main runs validation only mode."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create a simple file
        test_file = input_dir / "test.cob"
        test_file.write_text("       01 WS-FIELD PIC X.\n")

        result = main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(tmp_path / "output"),
                "--validate-only",
                "--quiet",
            ]
        )
        assert result == 0

    def test_main_dry_run(self, tmp_path):
        """Main runs dry-run mode."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create a simple file
        test_file = input_dir / "test.cob"
        test_file.write_text("       01 WS-FIELD PIC X.\n")

        output_dir = tmp_path / "output"

        result = main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
                "--dry-run",
                "--quiet",
            ]
        )

        assert result == 0
        # Output directory should not be created in dry-run
        # (depends on implementation)


class TestAnonymizationPipeline:
    """Tests for AnonymizationPipeline class."""

    def test_create_pipeline(self):
        """Create pipeline with default config."""
        pipeline = AnonymizationPipeline()
        assert pipeline is not None

    def test_pipeline_with_config(self, tmp_path):
        """Create pipeline with custom config."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        config = Config(
            input_dir=input_dir,
            output_dir=tmp_path / "output",
        )
        pipeline = AnonymizationPipeline(config)
        assert pipeline.config == config

    def test_pipeline_run_basic(self, tmp_path):
        """Run pipeline on basic files."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        # Create a simple COBOL file
        test_file = input_dir / "test.cob"
        test_file.write_text(
            """       IDENTIFICATION DIVISION.
       PROGRAM-ID. TESTPROG.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-FIELD PIC X(10).
       PROCEDURE DIVISION.
       MAIN-PARA.
           STOP RUN.
"""
        )

        config = Config(
            input_dir=input_dir,
            output_dir=output_dir,
            overwrite=True,
        )
        pipeline = AnonymizationPipeline(config)
        result = pipeline.run()

        assert result.success
        assert len(result.errors) == 0


class TestAnonymizeDirectoryFunction:
    """Tests for convenience function."""

    def test_anonymize_directory_basic(self, tmp_path):
        """Anonymize directory with default options."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        # Create a simple file
        test_file = input_dir / "test.cob"
        test_file.write_text("       01 WS-FIELD PIC X.\n")

        result = anonymize_directory(
            input_dir,
            output_dir,
            overwrite=True,
        )

        assert result.success


class TestValidateDirectoryFunction:
    """Tests for validation function."""

    def test_validate_directory_valid(self, tmp_path):
        """Validate directory with valid files."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create valid file
        test_file = input_dir / "test.cob"
        test_file.write_text("       01 WS-FIELD PIC X(10).\n")

        result = validate_directory(input_dir)
        assert result.is_valid

    def test_validate_directory_with_errors(self, tmp_path):
        """Validate directory with invalid files."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create file with line too long
        test_file = input_dir / "test.cob"
        test_file.write_text("A" * 100 + "\n")

        result = validate_directory(input_dir)
        assert not result.is_valid


class TestAnonymizationResult:
    """Tests for AnonymizationResult dataclass."""

    def test_create_result(self):
        """Create result with default values."""
        result = AnonymizationResult(success=True)
        assert result.success
        assert len(result.file_results) == 0
        assert len(result.errors) == 0

    def test_result_with_errors(self):
        """Create result with errors."""
        result = AnonymizationResult(
            success=False,
            errors=["Error 1", "Error 2"],
        )
        assert not result.success
        assert len(result.errors) == 2


class TestMappingsFileGeneration:
    """Tests for mappings.json file generation."""

    def test_mappings_file_generated_by_default(self, tmp_path):
        """Mappings file is generated in output directory by default."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        # Create a simple COBOL file
        test_file = input_dir / "test.cob"
        test_file.write_text(
            """       IDENTIFICATION DIVISION.
       PROGRAM-ID. TESTPROG.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-FIELD PIC X(10).
       PROCEDURE DIVISION.
       MAIN-PARA.
           STOP RUN.
"""
        )

        result = main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
                "--quiet",
            ]
        )

        assert result == 0
        mappings_file = output_dir / "mappings.json"
        assert mappings_file.exists(), "mappings.json should be created by default"

        # Verify it's valid JSON with expected structure
        mappings_data = json.loads(mappings_file.read_text())
        assert "mappings" in mappings_data
        assert "external_names" in mappings_data
        assert "generated_at" in mappings_data

    def test_mappings_file_with_custom_path(self, tmp_path):
        """Mappings file is saved to custom path when specified."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        custom_mappings = tmp_path / "custom_mappings.json"

        # Create a simple COBOL file
        test_file = input_dir / "test.cob"
        test_file.write_text(
            """       IDENTIFICATION DIVISION.
       PROGRAM-ID. TESTPROG.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-FIELD PIC X(10).
"""
        )

        result = main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
                "--mapping-file",
                str(custom_mappings),
                "--quiet",
            ]
        )

        assert result == 0
        assert custom_mappings.exists(), "mappings should be saved to custom path"
        # Default location should not exist
        default_mappings = output_dir / "mappings.json"
        assert not default_mappings.exists()

    def test_mappings_file_not_generated_in_dry_run(self, tmp_path):
        """Mappings file is not generated in dry-run mode."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        # Create a simple COBOL file
        test_file = input_dir / "test.cob"
        test_file.write_text(
            """       01 WS-FIELD PIC X(10).
"""
        )

        result = main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
                "--dry-run",
                "--quiet",
            ]
        )

        assert result == 0
        mappings_file = output_dir / "mappings.json"
        assert not mappings_file.exists(), "mappings.json should not be created in dry-run"

    def test_mappings_file_contains_anonymized_names(self, tmp_path):
        """Mappings file contains original to anonymized name mappings."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        # Create a COBOL file with identifiable names
        test_file = input_dir / "test.cob"
        test_file.write_text(
            """       IDENTIFICATION DIVISION.
       PROGRAM-ID. MYPROG.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 CUSTOMER-NAME PIC X(30).
       01 ACCOUNT-NUMBER PIC 9(10).
       PROCEDURE DIVISION.
       INIT-PROCESS.
           STOP RUN.
"""
        )

        result = main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
                "--quiet",
            ]
        )

        assert result == 0
        mappings_file = output_dir / "mappings.json"
        mappings_data = json.loads(mappings_file.read_text())

        # Check that mappings exist
        assert len(mappings_data["mappings"]) > 0

        # Find original names in mappings
        original_names = {m["original_name"].upper() for m in mappings_data["mappings"]}
        assert "CUSTOMER-NAME" in original_names
        assert "ACCOUNT-NUMBER" in original_names

    def test_mappings_file_with_naming_scheme(self, tmp_path):
        """Mappings file works with different naming schemes."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        # Create a simple COBOL file
        test_file = input_dir / "test.cob"
        test_file.write_text(
            """       01 WS-TEST-FIELD PIC X(10).
"""
        )

        # Test with numeric scheme
        result = main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
                "--naming-scheme",
                "numeric",
                "--quiet",
            ]
        )

        assert result == 0
        mappings_file = output_dir / "mappings.json"
        mappings_data = json.loads(mappings_file.read_text())

        # With numeric scheme, names should start with type prefix
        for mapping in mappings_data["mappings"]:
            anon_name = mapping["anonymized_name"]
            # Numeric scheme produces names like D0000001, PG000001, etc.
            assert anon_name[0].isalpha()

    def test_mappings_file_with_animals_scheme(self, tmp_path):
        """Mappings file with animals naming scheme."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        test_file = input_dir / "test.cob"
        test_file.write_text(
            """       01 WS-CUSTOMER-DATA PIC X(20).
"""
        )

        result = main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
                "--naming-scheme",
                "animals",
                "--quiet",
            ]
        )

        assert result == 0
        mappings_file = output_dir / "mappings.json"
        assert mappings_file.exists()
        mappings_data = json.loads(mappings_file.read_text())
        assert len(mappings_data["mappings"]) > 0

    def test_mappings_file_with_corporate_scheme(self, tmp_path):
        """Mappings file with corporate naming scheme (default)."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        test_file = input_dir / "test.cob"
        test_file.write_text(
            """       01 WS-ACCOUNT-INFO PIC X(15).
"""
        )

        result = main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
                "--naming-scheme",
                "corporate",
                "--quiet",
            ]
        )

        assert result == 0
        mappings_file = output_dir / "mappings.json"
        assert mappings_file.exists()
        mappings_data = json.loads(mappings_file.read_text())
        assert len(mappings_data["mappings"]) > 0


class TestIsDirectoryNonEmpty:
    """Tests for is_directory_non_empty helper function."""

    def test_non_existent_directory(self, tmp_path):
        """Return False for non-existent directory."""
        non_existent = tmp_path / "does_not_exist"
        assert is_directory_non_empty(non_existent) is False

    def test_empty_directory(self, tmp_path):
        """Return False for empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        assert is_directory_non_empty(empty_dir) is False

    def test_directory_with_file(self, tmp_path):
        """Return True for directory with file."""
        dir_with_file = tmp_path / "with_file"
        dir_with_file.mkdir()
        (dir_with_file / "file.txt").write_text("content")
        assert is_directory_non_empty(dir_with_file) is True

    def test_directory_with_subdirectory(self, tmp_path):
        """Return True for directory with subdirectory."""
        dir_with_subdir = tmp_path / "with_subdir"
        dir_with_subdir.mkdir()
        (dir_with_subdir / "subdir").mkdir()
        assert is_directory_non_empty(dir_with_subdir) is True

    def test_file_not_directory(self, tmp_path):
        """Return False when path is a file, not a directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        assert is_directory_non_empty(file_path) is False


class TestClearDirectory:
    """Tests for clear_directory helper function."""

    def test_clear_non_existent_directory(self, tmp_path):
        """Clearing non-existent directory does nothing."""
        non_existent = tmp_path / "does_not_exist"
        clear_directory(non_existent)  # Should not raise
        assert not non_existent.exists()

    def test_clear_empty_directory(self, tmp_path):
        """Clearing empty directory leaves it empty."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        clear_directory(empty_dir)
        assert empty_dir.exists()
        assert list(empty_dir.iterdir()) == []

    def test_clear_directory_with_files(self, tmp_path):
        """Clearing directory removes all files."""
        dir_path = tmp_path / "dir"
        dir_path.mkdir()
        (dir_path / "file1.txt").write_text("content1")
        (dir_path / "file2.txt").write_text("content2")

        clear_directory(dir_path)

        assert dir_path.exists()
        assert list(dir_path.iterdir()) == []

    def test_clear_directory_with_subdirectories(self, tmp_path):
        """Clearing directory removes subdirectories recursively."""
        dir_path = tmp_path / "dir"
        dir_path.mkdir()
        subdir = dir_path / "subdir"
        subdir.mkdir()
        (subdir / "nested_file.txt").write_text("nested content")
        (dir_path / "file.txt").write_text("content")

        clear_directory(dir_path)

        assert dir_path.exists()
        assert list(dir_path.iterdir()) == []


class TestPromptUserConfirmation:
    """Tests for prompt_user_confirmation helper function."""

    def test_yes_response(self):
        """Return True when user enters 'y'."""
        with patch("builtins.input", return_value="y"):
            assert prompt_user_confirmation("Continue?") is True

    def test_yes_full_response(self):
        """Return True when user enters 'yes'."""
        with patch("builtins.input", return_value="yes"):
            assert prompt_user_confirmation("Continue?") is True

    def test_yes_uppercase_response(self):
        """Return True when user enters 'Y' (uppercase)."""
        with patch("builtins.input", return_value="Y"):
            assert prompt_user_confirmation("Continue?") is True

    def test_no_response(self):
        """Return False when user enters 'n'."""
        with patch("builtins.input", return_value="n"):
            assert prompt_user_confirmation("Continue?") is False

    def test_empty_response(self):
        """Return False when user enters empty string."""
        with patch("builtins.input", return_value=""):
            assert prompt_user_confirmation("Continue?") is False

    def test_other_response(self):
        """Return False for any other input."""
        with patch("builtins.input", return_value="maybe"):
            assert prompt_user_confirmation("Continue?") is False

    def test_eof_error(self):
        """Return False when EOFError is raised (non-interactive)."""
        with patch("builtins.input", side_effect=EOFError):
            assert prompt_user_confirmation("Continue?") is False

    def test_keyboard_interrupt(self):
        """Return False when KeyboardInterrupt is raised (Ctrl+C)."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            assert prompt_user_confirmation("Continue?") is False


class TestNonEmptyOutputDirectory:
    """Tests for handling non-empty output directory."""

    def test_force_flag_clears_directory(self, tmp_path):
        """With --force, non-empty output directory is cleared without prompt."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create existing file in output directory
        existing_file = output_dir / "existing.txt"
        existing_file.write_text("existing content")

        # Create a simple COBOL file
        test_file = input_dir / "test.cob"
        test_file.write_text("       01 WS-FIELD PIC X.\n")

        result = main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
                "--force",
                "--quiet",
            ]
        )

        assert result == 0
        # Existing file should be removed
        assert not existing_file.exists()
        # New files should be created
        assert output_dir.exists()

    def test_user_confirms_clears_directory(self, tmp_path):
        """When user confirms, non-empty output directory is cleared."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create existing file in output directory
        existing_file = output_dir / "existing.txt"
        existing_file.write_text("existing content")

        # Create a simple COBOL file
        test_file = input_dir / "test.cob"
        test_file.write_text("       01 WS-FIELD PIC X.\n")

        # Mock user confirmation to return True
        with patch("cobol_anonymizer.cli.prompt_user_confirmation", return_value=True):
            result = main(
                [
                    "--input",
                    str(input_dir),
                    "--output",
                    str(output_dir),
                    "--quiet",
                ]
            )

        assert result == 0
        # Existing file should be removed
        assert not existing_file.exists()

    def test_user_declines_aborts(self, tmp_path):
        """When user declines, process is aborted."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create existing file in output directory
        existing_file = output_dir / "existing.txt"
        existing_file.write_text("existing content")

        # Create a simple COBOL file
        test_file = input_dir / "test.cob"
        test_file.write_text("       01 WS-FIELD PIC X.\n")

        # Mock user confirmation to return False
        with patch("cobol_anonymizer.cli.prompt_user_confirmation", return_value=False):
            result = main(
                [
                    "--input",
                    str(input_dir),
                    "--output",
                    str(output_dir),
                    "--quiet",
                ]
            )

        assert result == 0  # Graceful exit
        # Existing file should remain
        assert existing_file.exists()
        # No anonymization should have happened
        assert not (output_dir / "mappings.json").exists()

    def test_empty_output_directory_no_prompt(self, tmp_path):
        """Empty output directory does not trigger prompt."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()  # Create empty directory

        # Create a simple COBOL file
        test_file = input_dir / "test.cob"
        test_file.write_text("       01 WS-FIELD PIC X.\n")

        # If prompt was called, it would fail the test
        with patch("cobol_anonymizer.cli.prompt_user_confirmation") as mock_prompt:
            result = main(
                [
                    "--input",
                    str(input_dir),
                    "--output",
                    str(output_dir),
                    "--quiet",
                ]
            )
            mock_prompt.assert_not_called()

        assert result == 0

    def test_non_existent_output_directory_no_prompt(self, tmp_path):
        """Non-existent output directory does not trigger prompt."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        # Don't create output directory

        # Create a simple COBOL file
        test_file = input_dir / "test.cob"
        test_file.write_text("       01 WS-FIELD PIC X.\n")

        # If prompt was called, it would fail the test
        with patch("cobol_anonymizer.cli.prompt_user_confirmation") as mock_prompt:
            result = main(
                [
                    "--input",
                    str(input_dir),
                    "--output",
                    str(output_dir),
                    "--quiet",
                ]
            )
            mock_prompt.assert_not_called()

        assert result == 0

    def test_dry_run_skips_check(self, tmp_path):
        """Dry run mode skips output directory check."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create existing file in output directory
        existing_file = output_dir / "existing.txt"
        existing_file.write_text("existing content")

        # Create a simple COBOL file
        test_file = input_dir / "test.cob"
        test_file.write_text("       01 WS-FIELD PIC X.\n")

        # If prompt was called, it would fail the test
        with patch("cobol_anonymizer.cli.prompt_user_confirmation") as mock_prompt:
            result = main(
                [
                    "--input",
                    str(input_dir),
                    "--output",
                    str(output_dir),
                    "--dry-run",
                    "--quiet",
                ]
            )
            mock_prompt.assert_not_called()

        assert result == 0
        # Existing file should remain (dry run doesn't modify)
        assert existing_file.exists()

    def test_validate_only_skips_check(self, tmp_path):
        """Validate only mode skips output directory check."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create existing file in output directory
        existing_file = output_dir / "existing.txt"
        existing_file.write_text("existing content")

        # Create a simple COBOL file
        test_file = input_dir / "test.cob"
        test_file.write_text("       01 WS-FIELD PIC X.\n")

        # If prompt was called, it would fail the test
        with patch("cobol_anonymizer.cli.prompt_user_confirmation") as mock_prompt:
            result = main(
                [
                    "--input",
                    str(input_dir),
                    "--output",
                    str(output_dir),
                    "--validate-only",
                    "--quiet",
                ]
            )
            mock_prompt.assert_not_called()

        assert result == 0
        # Existing file should remain (validate only doesn't modify)
        assert existing_file.exists()


class TestParseForceFlag:
    """Tests for --force flag parsing."""

    def test_parse_force_flag(self, tmp_path):
        """Parse --force flag."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        args = parse_args(
            [
                "--input",
                str(input_dir),
                "--output",
                str(tmp_path / "output"),
                "--force",
            ]
        )
        assert args.force is True

    def test_parse_no_force_flag(self, tmp_path):
        """Default force flag is False."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        args = parse_args(
            [
                "--input",
                str(input_dir),
                "--output",
                str(tmp_path / "output"),
            ]
        )
        assert args.force is False
