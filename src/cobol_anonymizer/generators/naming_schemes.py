"""
COBOL Naming Schemes - Strategy pattern for identifier anonymization.

This module provides different naming schemes for anonymizing COBOL identifiers.
Available schemes:
- NUMERIC: Traditional prefix + counter (D00000001, SC00000001)
- ANIMALS: Adjective + animal (FLUFFY-LLAMA-1)
- FOOD: Adjective + food (SPICY-TACO-1)
- FANTASY: Adjective + creature (SNEAKY-DRAGON-1)
- CORPORATE: Business buzzwords (AGILE-SYNERGY-1)
"""

import hashlib
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Type

from cobol_anonymizer.core.classifier import IdentifierType
from cobol_anonymizer.exceptions import IdentifierLengthError


# Type-specific prefixes for numeric naming (used by NumericNamingStrategy)
NAME_PREFIXES: Dict[IdentifierType, str] = {
    IdentifierType.PROGRAM_NAME: "PG",
    IdentifierType.COPYBOOK_NAME: "CP",
    IdentifierType.SECTION_NAME: "SC",
    IdentifierType.PARAGRAPH_NAME: "PA",
    IdentifierType.DATA_NAME: "D",
    IdentifierType.CONDITION_NAME: "C",
    IdentifierType.FILE_NAME: "FL",
    IdentifierType.INDEX_NAME: "IX",
    IdentifierType.EXTERNAL_NAME: "EX",
    IdentifierType.UNKNOWN: "X",
}


class NamingScheme(str, Enum):
    """Available naming schemes for identifier anonymization."""
    NUMERIC = "numeric"
    ANIMALS = "animals"
    FOOD = "food"
    FANTASY = "fantasy"
    CORPORATE = "corporate"


class BaseNamingStrategy(ABC):
    """Abstract base class for naming strategies."""

    @abstractmethod
    def generate_name(
        self,
        original_name: str,
        id_type: IdentifierType,
        counter: int,
        target_length: int
    ) -> str:
        """
        Generate an anonymized name.

        Args:
            original_name: The original identifier name
            id_type: The type of identifier
            counter: Unique counter for this identifier type
            target_length: Target length for the generated name

        Returns:
            A valid COBOL identifier
        """
        pass

    @abstractmethod
    def get_scheme(self) -> NamingScheme:
        """Return the scheme identifier."""
        pass


class NumericNamingStrategy(BaseNamingStrategy):
    """
    Numeric naming strategy: PREFIX + zero-padded counter.

    Examples: D00000001, SC00000001, PA00000001
    """

    def generate_name(
        self,
        original_name: str,
        id_type: IdentifierType,
        counter: int,
        target_length: int
    ) -> str:
        """Generate a numeric name like D00000001."""
        prefix = NAME_PREFIXES.get(id_type, "X")
        available_digits = target_length - len(prefix)

        if available_digits < 1:
            return f"{prefix}{counter}"

        counter_str = str(counter).zfill(available_digits)

        # If counter overflows available digits, just use unpadded
        if len(counter_str) > available_digits:
            counter_str = str(counter)

        return f"{prefix}{counter_str}"

    def get_scheme(self) -> NamingScheme:
        return NamingScheme.NUMERIC


class WordBasedNamingStrategy(BaseNamingStrategy):
    """
    Base class for adjective-noun naming schemes.

    Generates names in format: ADJECTIVE-NOUN-COUNTER
    Uses deterministic hashing to select adjective/noun from word lists.
    """

    ADJECTIVES: List[str] = []
    NOUNS: List[str] = []

    # Minimum length for word-based names: "A-B-1" = 5 chars
    MIN_WORD_BASED_LENGTH = 5

    def generate_name(
        self,
        original_name: str,
        id_type: IdentifierType,
        counter: int,
        target_length: int
    ) -> str:
        """Generate a word-based name like FLUFFY-LLAMA-1."""
        # Check minimum length constraint
        min_required = 4 + len(str(counter))  # "A-B-" + counter
        if target_length < min_required:
            # Fall back to numeric scheme for very short names
            return self._fallback_to_numeric(id_type, counter, target_length)

        # Deterministic hash-based selection
        hash_val = self._hash_name(original_name)
        adj = self.ADJECTIVES[hash_val % len(self.ADJECTIVES)]
        noun = self.NOUNS[(hash_val // len(self.ADJECTIVES)) % len(self.NOUNS)]

        base_name = f"{adj}-{noun}-{counter}"

        # Truncate if exceeds target length (max 30 for COBOL)
        if len(base_name) > target_length:
            try:
                return self._truncate_name(adj, noun, counter, target_length)
            except IdentifierLengthError:
                # If truncation fails, fall back to numeric
                return self._fallback_to_numeric(id_type, counter, target_length)

        return base_name

    def _fallback_to_numeric(
        self,
        id_type: IdentifierType,
        counter: int,
        target_length: int
    ) -> str:
        """Fall back to numeric scheme when word-based cannot fit."""
        prefix = NAME_PREFIXES.get(id_type, "X")
        available_digits = target_length - len(prefix)
        if available_digits < 1:
            return f"{prefix}{counter}"
        return f"{prefix}{str(counter).zfill(available_digits)}"

    def _hash_name(self, name: str) -> int:
        """
        Generate deterministic hash from name.

        Uses MD5 for stability - DO NOT CHANGE without migration plan.
        """
        hash_bytes = hashlib.md5(name.upper().encode()).digest()
        return int.from_bytes(hash_bytes[:8], byteorder='big')

    def _truncate_name(
        self,
        adj: str,
        noun: str,
        counter: int,
        max_len: int
    ) -> str:
        """
        Truncate name to fit within max length.

        Raises:
            IdentifierLengthError: If counter is too large to fit in max_len
        """
        counter_str = str(counter)

        # Minimum required: 1-char adj + hyphen + 1-char noun + hyphen + counter
        # Example minimum: "A-B-1" = 5 characters
        min_required = 4 + len(counter_str)  # "A-B-" + counter

        if max_len < min_required:
            raise IdentifierLengthError(
                f"Cannot generate word-based name: max_len={max_len} "
                f"< min_required={min_required} for counter={counter}",
                max_len
            )

        # Reserve space for: ADJ- + NOUN- + counter
        available = max_len - len(counter_str) - 2  # 2 hyphens
        adj_len = max(1, available // 2)
        noun_len = max(1, available - adj_len)

        result = f"{adj[:adj_len]}-{noun[:noun_len]}-{counter_str}"

        # Final validation: ensure no double hyphens were created
        if "--" in result:
            raise IdentifierLengthError(
                f"Truncation produced invalid name with double hyphen: {result}",
                max_len
            )

        return result

    @abstractmethod
    def get_scheme(self) -> NamingScheme:
        pass


class AnimalNamingStrategy(WordBasedNamingStrategy):
    """Animal-themed naming: FLUFFY-LLAMA-1, GRUMPY-PENGUIN-2"""

    ADJECTIVES = [
        "FLUFFY", "GRUMPY", "SNEAKY", "WOBBLY", "DIZZY",
        "SLEEPY", "JUMPY", "FUZZY", "CHUNKY", "SPEEDY",
        "MIGHTY", "CLEVER", "SWIFT", "BRAVE", "SILLY"
    ]

    NOUNS = [
        "LLAMA", "PENGUIN", "WOMBAT", "PLATYPUS", "BADGER",
        "OTTER", "SLOTH", "KOALA", "LEMUR", "PANDA",
        "FERRET", "MARMOT", "BEAVER", "FALCON", "TOUCAN"
    ]

    def get_scheme(self) -> NamingScheme:
        return NamingScheme.ANIMALS


class FoodNamingStrategy(WordBasedNamingStrategy):
    """Food-themed naming: SPICY-TACO-1, CRISPY-WAFFLE-2"""

    ADJECTIVES = [
        "SPICY", "CRISPY", "SOGGY", "CHUNKY", "TANGY",
        "ZESTY", "GOOEY", "CRUNCHY", "SAVORY", "SIZZLY",
        "SMOKY", "CHEESY", "FRESH", "TOASTY", "SAUCY"
    ]

    NOUNS = [
        "TACO", "WAFFLE", "NOODLE", "PICKLE", "MUFFIN",
        "PRETZEL", "BURRITO", "DUMPLING", "PANCAKE", "NACHO",
        "BAGEL", "DONUT", "BISCUIT", "CRUMPET", "CHURRO"
    ]

    def get_scheme(self) -> NamingScheme:
        return NamingScheme.FOOD


class FantasyNamingStrategy(WordBasedNamingStrategy):
    """Fantasy-themed naming: SNEAKY-DRAGON-1, ANCIENT-GOBLIN-2"""

    ADJECTIVES = [
        "SNEAKY", "ANCIENT", "MIGHTY", "SLEEPY", "GRUMPY",
        "MYSTIC", "SHADOW", "FIERCE", "CLEVER", "NOBLE",
        "ARCANE", "GOLDEN", "SILVER", "WILD", "COSMIC"
    ]

    NOUNS = [
        "DRAGON", "GOBLIN", "UNICORN", "TROLL", "PHOENIX",
        "WIZARD", "SPHINX", "GRIFFIN", "OGRE", "FAIRY",
        "KRAKEN", "HYDRA", "CENTAUR", "CYCLOPS", "CHIMERA"
    ]

    def get_scheme(self) -> NamingScheme:
        return NamingScheme.FANTASY


class CorporateNamingStrategy(WordBasedNamingStrategy):
    """Corporate buzzword naming: AGILE-SYNERGY-1, LEAN-PARADIGM-2"""

    ADJECTIVES = [
        "AGILE", "SYNERGY", "PIVOT", "DISRUPT", "LEVERAGE",
        "SCALABLE", "ROBUST", "DYNAMIC", "HOLISTIC", "LEAN",
        "PROACTIVE", "NIMBLE", "OPTIMAL", "ALIGNED", "ELASTIC"
    ]

    NOUNS = [
        "PARADIGM", "BANDWIDTH", "SILO", "ROADMAP", "STAKEHOLDER",
        "TOUCHPOINT", "PIPELINE", "MINDSHARE", "VERTICAL", "METRICS",
        "SYNERGY", "ECOSYSTEM", "PLATFORM", "FRAMEWORK", "CHANNEL"
    ]

    def get_scheme(self) -> NamingScheme:
        return NamingScheme.CORPORATE


# Strategy registry
_STRATEGY_REGISTRY: Dict[NamingScheme, Type[BaseNamingStrategy]] = {
    NamingScheme.NUMERIC: NumericNamingStrategy,
    NamingScheme.ANIMALS: AnimalNamingStrategy,
    NamingScheme.FOOD: FoodNamingStrategy,
    NamingScheme.FANTASY: FantasyNamingStrategy,
    NamingScheme.CORPORATE: CorporateNamingStrategy,
}


def get_naming_strategy(scheme: NamingScheme) -> BaseNamingStrategy:
    """
    Factory function to get naming strategy by scheme.

    Args:
        scheme: The naming scheme enum value

    Returns:
        A concrete naming strategy instance

    Raises:
        ValueError: If scheme is not a valid NamingScheme
        KeyError: If scheme is valid but not implemented
    """
    # Validate input type
    if not isinstance(scheme, NamingScheme):
        raise ValueError(
            f"Invalid naming scheme: {scheme!r}. "
            f"Expected NamingScheme enum, got {type(scheme).__name__}"
        )

    if scheme not in _STRATEGY_REGISTRY:
        raise KeyError(f"No strategy implemented for scheme: {scheme}")

    return _STRATEGY_REGISTRY[scheme]()
