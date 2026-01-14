"""
COBOL Name Generator - Generates anonymized identifier names.

This module generates unique, valid COBOL identifiers for anonymization.
Key features:
- Multiple naming schemes (numeric, animals, food, fantasy, corporate)
- Type-specific prefixes for numeric scheme (PG, CP, SC, PA, D, C, FL, IX)
- Length preservation up to 30 characters
- Reserved word collision avoidance
- Deterministic generation with optional seed
"""

import random
from dataclasses import dataclass, field
from typing import Optional

from cobol_anonymizer.cobol.reserved_words import is_reserved_word
from cobol_anonymizer.core.classifier import IdentifierType
from cobol_anonymizer.core.utils import MAX_IDENTIFIER_LENGTH, validate_identifier
from cobol_anonymizer.exceptions import (
    IdentifierLengthError,
    ReservedWordCollisionError,
)
from cobol_anonymizer.generators.naming_schemes import (
    NAME_PREFIXES,
    BaseNamingStrategy,
    NamingScheme,
    format_numeric_name,
    get_naming_strategy,
    get_prefix_for_type,
)

# Re-export NAME_PREFIXES for backward compatibility
# (imported from naming_schemes module)
__all__ = ["NameGenerator", "NameGeneratorConfig", "NAME_PREFIXES", "NamingScheme"]


@dataclass
class NameGeneratorConfig:
    """
    Configuration for name generation.

    Attributes:
        preserve_length: If True, match original name length
        min_length: Minimum length for generated names
        max_length: Maximum length (COBOL limit is 30)
        seed: Random seed for deterministic generation
        naming_scheme: The naming scheme to use (default: NUMERIC)
    """

    preserve_length: bool = True
    min_length: int = 4
    max_length: int = MAX_IDENTIFIER_LENGTH
    seed: Optional[int] = None
    naming_scheme: NamingScheme = NamingScheme.CORPORATE


@dataclass
class NameGenerator:
    """
    Generates unique anonymized COBOL identifiers.

    Usage:
        generator = NameGenerator()
        new_name = generator.generate("WS-CUSTOMER-NAME", IdentifierType.DATA_NAME)

        # With a different naming scheme:
        config = NameGeneratorConfig(naming_scheme=NamingScheme.ANIMALS)
        generator = NameGenerator(config=config)
        new_name = generator.generate("WS-CUSTOMER-NAME", IdentifierType.DATA_NAME)
        # -> "FLUFFY-LLAMA-1"
    """

    config: NameGeneratorConfig = field(default_factory=NameGeneratorConfig)
    _counters: dict[IdentifierType, int] = field(default_factory=dict)
    _generated_names: set[str] = field(default_factory=set)
    _random: Optional[random.Random] = None
    _strategy: Optional[BaseNamingStrategy] = field(default=None, init=False)

    def __post_init__(self):
        # Initialize naming strategy based on config
        self._strategy = get_naming_strategy(self.config.naming_scheme)

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
        # Get the prefix for this type (used for minimum length calculation)
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

        # Get next counter value for this type
        counter = self._get_next_counter(id_type)

        # Generate the name using the strategy
        max_retries = 1000
        for _attempt in range(max_retries):
            # Delegate to the naming strategy
            name = self._strategy.generate_name(original_name, id_type, counter, length)

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

    def get_counter_state(self) -> dict[IdentifierType, int]:
        """Get the current counter state for all types."""
        return dict(self._counters)

    def set_counter_state(self, state: dict[IdentifierType, int]) -> None:
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
    prefix = get_prefix_for_type(id_type)

    if preserve_length:
        target_length = min(len(original_name), MAX_IDENTIFIER_LENGTH)
    else:
        target_length = MAX_IDENTIFIER_LENGTH

    target_length = max(target_length, len(prefix) + 1)
    return format_numeric_name(prefix, counter, target_length)


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
