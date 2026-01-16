"""
String Literal Anonymizer - Anonymizes string literals with length preservation.

This module provides functionality to anonymize string literals in COBOL code
using a randomly selected naming scheme (different from the main scheme) while
preserving the exact length of the original string.
"""

import random
import re
from typing import Optional

from cobol_anonymizer.generators.naming_schemes import NamingScheme


# Word lists for each scheme (extracted from naming_schemes.py)
_SCHEME_WORDS: dict[NamingScheme, tuple[list[str], list[str]]] = {
    NamingScheme.ANIMALS: (
        [
            "FLUFFY",
            "GRUMPY",
            "SNEAKY",
            "WOBBLY",
            "DIZZY",
            "SLEEPY",
            "JUMPY",
            "FUZZY",
            "CHUNKY",
            "SPEEDY",
            "MIGHTY",
            "CLEVER",
            "SWIFT",
            "BRAVE",
            "SILLY",
        ],
        [
            "LLAMA",
            "PENGUIN",
            "BADGER",
            "OTTER",
            "KOALA",
            "WALRUS",
            "FERRET",
            "PARROT",
            "WOMBAT",
            "GIBBON",
            "MANTIS",
            "IGUANA",
            "FALCON",
            "COBRA",
            "SALMON",
        ],
    ),
    NamingScheme.FOOD: (
        [
            "SPICY",
            "CRISPY",
            "TANGY",
            "SMOKY",
            "ZESTY",
            "CHEWY",
            "CREAMY",
            "CRUNCHY",
            "SAVORY",
            "SWEET",
            "SALTY",
            "FRESH",
            "GRILLED",
            "BAKED",
            "FRIED",
        ],
        [
            "TACO",
            "WAFFLE",
            "PICKLE",
            "BAGEL",
            "NACHO",
            "MUFFIN",
            "PRETZEL",
            "BRISKET",
            "CHURRO",
            "RAMEN",
            "DONUT",
            "BURGER",
            "PIZZA",
            "PASTA",
            "SALAD",
        ],
    ),
    NamingScheme.FANTASY: (
        [
            "SNEAKY",
            "ANCIENT",
            "MYSTIC",
            "SHADOW",
            "FROST",
            "FLAME",
            "STORM",
            "IRON",
            "SILVER",
            "GOLDEN",
            "DARK",
            "LIGHT",
            "WILD",
            "BRAVE",
            "WISE",
        ],
        [
            "DRAGON",
            "GOBLIN",
            "WIZARD",
            "GRIFFIN",
            "PHOENIX",
            "TROLL",
            "PIXIE",
            "DWARF",
            "SPRITE",
            "WRAITH",
            "KNIGHT",
            "RANGER",
            "MAGE",
            "ROGUE",
            "CLERIC",
        ],
    ),
    NamingScheme.CORPORATE: (
        [
            "AGILE",
            "LEAN",
            "CORE",
            "PRIME",
            "SMART",
            "RAPID",
            "CLOUD",
            "CYBER",
            "DATA",
            "FLEX",
            "ULTRA",
            "MEGA",
            "SUPER",
            "HYPER",
            "TURBO",
        ],
        [
            "SYNERGY",
            "PARADIGM",
            "MATRIX",
            "NEXUS",
            "VERTEX",
            "QUANTUM",
            "FUSION",
            "DYNAMIC",
            "VORTEX",
            "STREAM",
            "SUMMIT",
            "BRIDGE",
            "ALPHA",
            "OMEGA",
            "DELTA",
        ],
    ),
    NamingScheme.NUMERIC: (
        # For numeric scheme, we use letter combinations
        ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O"],
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "X", "Y", "Z", "W", "V"],
    ),
}


class LiteralAnonymizer:
    """
    Anonymizes string literals using a naming scheme with length preservation.

    The anonymizer generates replacement text by combining words from the
    selected naming scheme, ensuring the result has the exact same length
    as the original string.
    """

    def __init__(self, scheme: NamingScheme, seed: Optional[int] = None):
        """
        Initialize the literal anonymizer.

        Args:
            scheme: The naming scheme to use for generating replacement text
            seed: Optional seed for deterministic output
        """
        self.scheme = scheme
        self.rng = random.Random(seed)
        self.adjectives, self.nouns = _SCHEME_WORDS.get(scheme, _SCHEME_WORDS[NamingScheme.ANIMALS])
        self._word_index = 0

    def anonymize_literal(self, original: str) -> str:
        """
        Replace literal content with naming scheme words, preserving length.

        Args:
            original: The original literal content (without quotes)

        Returns:
            Anonymized string of exactly the same length
        """
        target_length = len(original)

        if target_length == 0:
            return ""

        if target_length == 1:
            # Single character - use a random character
            return self.rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

        # Generate words until we have enough characters
        words = []
        current_length = 0

        while current_length < target_length:
            # Alternate between adjectives and nouns
            if len(words) % 2 == 0:
                word = self.rng.choice(self.adjectives)
            else:
                word = self.rng.choice(self.nouns)

            words.append(word)
            # +1 for separator (space or hyphen)
            current_length += len(word) + (1 if words else 0)

        # Join words with spaces (more natural for literals)
        result = " ".join(words)

        # Adjust to exact length
        if len(result) > target_length:
            result = result[:target_length]
        elif len(result) < target_length:
            # Pad with spaces (common in COBOL literals)
            result = result.ljust(target_length)

        # Ensure no trailing spaces if original didn't have them
        # but maintain length
        if not original.endswith(" ") and result.endswith(" "):
            # Replace trailing spaces with dashes or other chars
            trailing_spaces = len(result) - len(result.rstrip())
            if trailing_spaces > 0:
                result = result.rstrip() + "-" * trailing_spaces

        return result


def select_literal_scheme(main_scheme: NamingScheme, seed: Optional[int] = None) -> NamingScheme:
    """
    Select a random naming scheme for literals, different from the main scheme.

    Args:
        main_scheme: The main naming scheme used for identifiers
        seed: Optional seed for deterministic selection

    Returns:
        A NamingScheme different from main_scheme
    """
    rng = random.Random(seed)
    available = [s for s in NamingScheme if s != main_scheme]
    return rng.choice(available)


# Pattern for matching string literals in COBOL
LITERAL_PATTERN = re.compile(r"'([^']*)'|\"([^\"]*)\"")


def transform_literals(
    line: str,
    anonymizer: LiteralAnonymizer,
    enabled: bool = True,
) -> str:
    """
    Transform string literals in a line using the literal anonymizer.

    Args:
        line: The COBOL line to transform
        anonymizer: The LiteralAnonymizer instance
        enabled: Whether literal anonymization is enabled

    Returns:
        The line with literals transformed
    """
    if not enabled:
        return line

    def replace_literal(match: re.Match) -> str:
        # Determine which group matched (single or double quotes)
        if match.group(1) is not None:
            quote = "'"
            content = match.group(1)
        else:
            quote = '"'
            content = match.group(2)

        anonymized = anonymizer.anonymize_literal(content)
        return f"{quote}{anonymized}{quote}"

    return LITERAL_PATTERN.sub(replace_literal, line)
