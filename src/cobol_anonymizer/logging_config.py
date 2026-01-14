"""
Logging configuration for the COBOL Anonymizer.

This module provides logging setup and configuration utilities.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Default log format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
SIMPLE_FORMAT = "%(levelname)s: %(message)s"


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    verbose: bool = False,
) -> logging.Logger:
    """Configure logging for the anonymizer.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        verbose: If True, use detailed format; otherwise use simple format

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("cobol_anonymizer")

    # Clear any existing handlers
    logger.handlers.clear()

    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Choose format based on verbosity
    log_format = DEFAULT_FORMAT if verbose else SIMPLE_FORMAT
    formatter = logging.Formatter(log_format)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Optional name for the logger. If None, returns the main logger.

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"cobol_anonymizer.{name}")
    return logging.getLogger("cobol_anonymizer")


class LogContext:
    """Context manager for temporarily changing log level."""

    def __init__(self, logger: logging.Logger, level: int):
        self.logger = logger
        self.new_level = level
        self.old_level = logger.level

    def __enter__(self):
        self.logger.setLevel(self.new_level)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.old_level)
        return False
