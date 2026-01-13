"""
COBOL Name Generator - Generates anonymized identifier names.

This module generates unique, valid COBOL identifiers for anonymization.
Key features:
- Type-specific prefixes (PG, CP, SC, PA, D, C, FL, IX)
- Zero-padded counters (no hyphens in generated names)
- Length preservation up to 30 characters
- Reserved word collision avoidance
- Deterministic generation with optional seed
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Set
import random

from cobol_anonymizer.core.classifier import IdentifierType
from cobol_anonymizer.cobol.reserved_words import is_reserved_word
from cobol_anonymizer.core.utils import validate_identifier, MAX_IDENTIFIER_LENGTH
from cobol_anonymizer.exceptions import (
    ReservedWordCollisionError,
    IdentifierLengthError,
)


# Type-specific prefixes for generated names
# Short prefixes maximize available digits for counter
NAME_PREFIXES: Dict[IdentifierType, str] = {
    IdentifierType.PROGRAM_NAME: "PG",
    IdentifierType.COPYBOOK_NAME: "CP",
    IdentifierType.SECTION_NAME: "SC",
    IdentifierType.PARAGRAPH_NAME: "PA",
    IdentifierType.DATA_NAME: "D",
    IdentifierType.CONDITION_NAME: "C",
    IdentifierType.FILE_NAME: "FL",
    IdentifierType.INDEX_NAME: "IX",
    IdentifierType.EXTERNAL_NAME: "EX",  # Should not be used normally
    IdentifierType.UNKNOWN: "X",
}


@dataclass
class NameGeneratorConfig:
    """
    Configuration for name generation.

    Attributes:
        preserve_length: If True, match original name length
        min_length: Minimum length for generated names
        max_length: Maximum length (COBOL limit is 30)
        seed: Random seed for deterministic generation
    """
    preserve_length: bool = True
    min_length: int = 4
    max_length: int = MAX_IDENTIFIER_LENGTH
    seed: Optional[int] = None


@dataclass
class NameGenerator:
    """
    Generates unique anonymized COBOL identifiers.

    Usage:
        generator = NameGenerator()
        new_name = generator.generate("WS-CUSTOMER-NAME", IdentifierType.DATA_NAME)
    """
    config: NameGeneratorConfig = field(default_factory=NameGeneratorConfig)
    _counters: Dict[IdentifierType, int] = field(default_factory=dict)
    _generated_names: Set[str] = field(default_factory=set)
    _random: Optional[random.Random] = None

    def __post_init__(self):
        if self.config.seed is not None:
            self._random = random.Random(self.config.seed)

    def generate(
        self,
        original_name: str,
        id_type: IdentifierType,
        target_length: Optional[int] = None,
    ) -> str:
        """
        Generate a new anonymized name.

        Args:
            original_name: The original identifier name
            id_type: The type of identifier
            target_length: Optional specific length (overrides preserve_length)

        Returns:
            A unique, valid COBOL identifier
        """
        # Get the prefix for this type
        prefix = NAME_PREFIXES.get(id_type, "X")

        # Determine target length
        if target_length is not None:
            length = min(target_length, self.config.max_length)
        elif self.config.preserve_length:
            length = min(len(original_name), self.config.max_length)
        else:
            length = self.config.max_length

        # Ensure minimum length
        length = max(length, self.config.min_length)
        length = max(length, len(prefix) + 1)  # At least prefix + 1 digit

        # Calculate available digits for counter
        available_digits = length - len(prefix)

        # Get next counter value for this type
        counter = self._get_next_counter(id_type)

        # Generate the name
        max_retries = 1000
        for attempt in range(max_retries):
            name = self._format_name(prefix, counter, available_digits)

            # Validate the generated name
            if self._is_valid_name(name):
                self._generated_names.add(name.upper())
                return name

            # If invalid, try next counter
            counter = self._get_next_counter(id_type)

        raise RuntimeError(f"Could not generate valid name after {max_retries} attempts")

    def _get_next_counter(self, id_type: IdentifierType) -> int:
        """Get the next counter value for a type."""
        if id_type not in self._counters:
            self._counters[id_type] = 0
        self._counters[id_type] += 1
        return self._counters[id_type]

    def _format_name(self, prefix: str, counter: int, available_digits: int) -> str:
        """
        Format a name with zero-padded counter.

        Args:
            prefix: The type prefix (e.g., "D", "PG")
            counter: The counter value
            available_digits: Number of digits available

        Returns:
            Formatted name like "D0000001" or "PG000001"
        """
        if available_digits < 1:
            return f"{prefix}1"

        # Zero-pad the counter to fill available space
        counter_str = str(counter).zfill(available_digits)

        # If counter is too large, just use it without padding
        if len(counter_str) > available_digits:
            counter_str = str(counter)

        return f"{prefix}{counter_str}"

    def _is_valid_name(self, name: str) -> bool:
        """
        Check if a generated name is valid.

        Args:
            name: The generated name to validate

        Returns:
            True if the name is valid
        """
        # Check for collisions with reserved words
        if is_reserved_word(name):
            return False

        # Check for uniqueness
        if name.upper() in self._generated_names:
            return False

        # Validate COBOL identifier rules
        try:
            is_valid, _ = validate_identifier(name, raise_on_error=False)
            return is_valid
        except Exception:
            return False

    def get_counter_state(self) -> Dict[IdentifierType, int]:
        """Get the current counter state for all types."""
        return dict(self._counters)

    def set_counter_state(self, state: Dict[IdentifierType, int]) -> None:
        """Set the counter state (for resuming generation)."""
        self._counters = dict(state)

    def reset(self) -> None:
        """Reset all counters and generated names."""
        self._counters.clear()
        self._generated_names.clear()


def generate_anonymized_name(
    original_name: str,
    id_type: IdentifierType,
    counter: int,
    preserve_length: bool = True,
) -> str:
    """
    Generate a single anonymized name.

    This is a convenience function for one-off generation.
    For batch generation, use the NameGenerator class.

    Args:
        original_name: The original identifier
        id_type: The identifier type
        counter: The counter value to use
        preserve_length: Whether to match original length

    Returns:
        An anonymized name
    """
    prefix = NAME_PREFIXES.get(id_type, "X")

    if preserve_length:
        target_length = min(len(original_name), MAX_IDENTIFIER_LENGTH)
    else:
        target_length = MAX_IDENTIFIER_LENGTH

    target_length = max(target_length, len(prefix) + 1)
    available_digits = target_length - len(prefix)

    counter_str = str(counter).zfill(available_digits)
    if len(counter_str) > available_digits:
        counter_str = str(counter)

    return f"{prefix}{counter_str}"


def validate_generated_name(name: str) -> None:
    """
    Validate a generated name meets COBOL requirements.

    Args:
        name: The name to validate

    Raises:
        IdentifierLengthError: If name exceeds 30 characters
        ReservedWordCollisionError: If name is a reserved word
    """
    # Check length
    if len(name) > MAX_IDENTIFIER_LENGTH:
        raise IdentifierLengthError(name, len(name))

    # Check for reserved word collision
    if is_reserved_word(name):
        raise ReservedWordCollisionError(name, name)

    # Validate identifier format
    validate_identifier(name)
