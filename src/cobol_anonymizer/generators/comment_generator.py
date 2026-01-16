"""
Comment Handler - Anonymizes COBOL comments while preserving structure.

This module handles:
- Detecting comment lines (column 7 = `*`)
- Generating meaningless filler text to replace comment content
- Preserving comment structure, indentation, and dividers
- Option to strip all comments
"""

import random
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CommentMode(Enum):
    """Comment anonymization modes."""

    ANONYMIZE = "anonymize"  # Replace content with meaningless filler text
    STRIP = "strip"  # Remove comment content entirely
    PRESERVE = "preserve"  # Keep comments unchanged


# Generic filler words for generating meaningless comment text
# These are neutral COBOL-like terms with no business meaning
FILLER_WORDS = [
    "BLAH",
    "DATA",
    "PROCESS",
    "VALUE",
    "FIELD",
    "ITEM",
    "CODE",
    "TEXT",
    "NOTE",
    "INFO",
    "WORK",
    "TEMP",
    "AREA",
    "LINE",
    "STEP",
    "TASK",
    "UNIT",
    "PART",
    "ELEM",
    "SECT",
    "BLOCK",
]


def generate_filler_text(length: int, seed: Optional[int] = None) -> str:
    """
    Generate meaningless filler text of exactly the specified length.

    Args:
        length: Target length for the generated text
        seed: Optional random seed for reproducibility

    Returns:
        Meaningless filler text of exact length
    """
    if length <= 0:
        return ""

    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()

    words = []
    current_length = 0

    # Sort filler words by length to find words that fit
    sorted(FILLER_WORDS, key=len)

    while current_length < length:
        # Find words that can fit in remaining space
        remaining = length - current_length
        if current_length > 0:
            remaining -= 1  # Account for space separator

        # Filter words that fit
        fitting_words = [w for w in FILLER_WORDS if len(w) <= remaining]
        if not fitting_words:
            break

        word = rng.choice(fitting_words)
        if current_length > 0:
            current_length += 1  # space
        words.append(word)
        current_length += len(word)

    result = " ".join(words)

    # Pad with spaces if needed to match exact length
    if len(result) < length:
        result = result.ljust(length)

    return result


@dataclass
class CommentConfig:
    """Configuration for comment handling."""

    mode: CommentMode = CommentMode.ANONYMIZE
    preserve_dividers: bool = True  # Keep lines like *------- or ******
    seed: Optional[int] = None  # Random seed for reproducible output


# Italian to English term mappings for business domain
ITALIAN_TERMS: dict[str, str] = {
    # Insurance terms
    "POLIZZA": "POLICY",
    "CONTRATTO": "CONTRACT",
    "ASSICURATO": "INSURED",
    "BENEFICIARIO": "BENEFICIARY",
    "PREMIO": "PREMIUM",
    "SINISTRO": "CLAIM",
    "DENUNCIA": "REPORT",
    "RISCHIO": "RISK",
    "COPERTURA": "COVERAGE",
    "GARANZIA": "WARRANTY",
    "QUIETANZA": "RECEIPT",
    "SCADENZA": "EXPIRY",
    "RINNOVO": "RENEWAL",
    "DISDETTA": "CANCELLATION",
    "RECESSO": "WITHDRAWAL",
    "LIQUIDAZIONE": "SETTLEMENT",
    "INDENNIZZO": "COMPENSATION",
    "FRANCHIGIA": "DEDUCTIBLE",
    "MASSIMALE": "MAXIMUM",
    "CAPITALE": "CAPITAL",
    # Business terms
    "CLIENTE": "CLIENT",
    "AGENZIA": "AGENCY",
    "AGENTE": "AGENT",
    "PRODUTTORE": "PRODUCER",
    "INTESTATARIO": "HOLDER",
    "CONTRAENTE": "CONTRACTOR",
    "TITOLARE": "OWNER",
    "ANAGRAFICA": "REGISTRY",
    "PORTAFOGLIO": "PORTFOLIO",
    "SISTEMA": "SYSTEM",
    "PROCEDURA": "PROCEDURE",
    "PROGRAMMA": "PROGRAM",
    "MODULO": "MODULE",
    "FUNZIONE": "FUNCTION",
    "ROUTINE": "ROUTINE",
    "ELABORAZIONE": "PROCESSING",
    "CALCOLO": "CALCULATION",
    "VERIFICA": "VERIFICATION",
    "CONTROLLO": "CONTROL",
    "GESTIONE": "MANAGEMENT",
    # Date/time terms
    "DATA": "DATE",
    "GIORNO": "DAY",
    "MESE": "MONTH",
    "ANNO": "YEAR",
    "DECORRENZA": "START-DATE",
    "EFFETTO": "EFFECT",
    # General terms
    "NUMERO": "NUMBER",
    "CODICE": "CODE",
    "TIPO": "TYPE",
    "STATO": "STATUS",
    "IMPORTO": "AMOUNT",
    "VALORE": "VALUE",
    "TOTALE": "TOTAL",
    "ERRORE": "ERROR",
    "MESSAGGIO": "MESSAGE",
    "RISPOSTA": "RESPONSE",
    "RICHIESTA": "REQUEST",
    "RISULTATO": "RESULT",
    "ESITO": "OUTCOME",
    "INIZIO": "START",
    "FINE": "END",
    "PRINCIPALE": "MAIN",
    "SECONDARIO": "SECONDARY",
    "PRECEDENTE": "PREVIOUS",
    "SUCCESSIVO": "NEXT",
    "NUOVO": "NEW",
    "VECCHIO": "OLD",
    "ATTIVO": "ACTIVE",
    "INATTIVO": "INACTIVE",
    "VALIDO": "VALID",
    "INVALIDO": "INVALID",
    # Technical terms
    "AREA": "AREA",
    "CAMPO": "FIELD",
    "RECORD": "RECORD",
    "TABELLA": "TABLE",
    "CHIAVE": "KEY",
    "INDICE": "INDEX",
    "CONTATORE": "COUNTER",
    "FLAG": "FLAG",
    "INDICATORE": "INDICATOR",
    "DESCRIZIONE": "DESCRIPTION",
    "LUNGHEZZA": "LENGTH",
    "POSIZIONE": "POSITION",
    "FORMATO": "FORMAT",
    "SEZIONE": "SECTION",
    "DIVISIONE": "DIVISION",
    "PARAGRAFO": "PARAGRAPH",
    "RIGA": "LINE",
    "COLONNA": "COLUMN",
    "CARATTERE": "CHARACTER",
    "STRINGA": "STRING",
    "NUMERICO": "NUMERIC",
    "ALFABETICO": "ALPHABETIC",
}

# Common Italian personal names to remove
PERSONAL_NAMES: set[str] = {
    "MASON",
    "LUPO",
    "ROSSI",
    "BIANCHI",
    "FERRARI",
    "RUSSO",
    "ESPOSITO",
    "ROMANO",
    "COLOMBO",
    "RICCI",
    "MARINO",
    "GRECO",
    "BRUNO",
    "GALLO",
    "CONTI",
    "LEONE",
    "COSTA",
    "GIORDANO",
    "MANCINI",
    "RIZZO",
    "LOMBARDI",
    "MORETTI",
    "BARBIERI",
    "FONTANA",
    "SANTORO",
    "CARUSO",
    "MARIANI",
    "RINALDI",
    "MARCO",
    "LUCA",
    "ANDREA",
    "FRANCESCO",
    "GIUSEPPE",
    "GIOVANNI",
    "ANTONIO",
    "LUIGI",
    "MARIO",
    "PAOLO",
    "MARIA",
    "ANNA",
    "GIULIA",
    "SARA",
    "LAURA",
    "ELENA",
    "FRANCESCA",
    "CHIARA",
    "SILVIA",
    "VALENTINA",
}

# Regex patterns for system identifiers
SYSTEM_ID_PATTERNS = [
    r"\bCRQ\d{9,15}\b",  # CRQ numbers (e.g., CRQ000002478171)
    r"\bINC\d{9,15}\b",  # Incident numbers
    r"\bCHG\d{9,15}\b",  # Change numbers
    r"\bPRB\d{9,15}\b",  # Problem numbers
    r"\bREQ\d{9,15}\b",  # Request numbers
    r"\bSR\d{9,15}\b",  # Service request numbers
    r"\b\d{2}/\d{2}/\d{4}\b",  # Dates DD/MM/YYYY
    r"\b\d{4}/\d{2}/\d{2}\b",  # Dates YYYY/MM/DD
    r"\b\d{2}-\d{2}-\d{4}\b",  # Dates DD-MM-YYYY
    r"\b\d{8}\b",  # 8-digit dates YYYYMMDD
]


@dataclass
class CommentTransformResult:
    """Result of transforming a comment."""

    original_text: str
    transformed_text: str
    is_divider: bool = False
    is_stripped: bool = False
    changes_made: list[tuple[str, str]] = field(default_factory=list)


def is_comment_line(line: str) -> bool:
    """
    Check if a line is a COBOL comment.

    For fixed-format: Column 7 must contain '*' or '/'.
    For free-format: Line starts with '*>' or '*' (after optional whitespace).

    Args:
        line: The source line to check

    Returns:
        True if this is a comment line
    """
    # Check for fixed-format comment (column 7 = * or /)
    if len(line) >= 7 and line[6] in ("*", "/"):
        return True

    # Check for free-format comment (*> or * at start of line)
    stripped = line.lstrip()
    if stripped.startswith("*>") or (stripped.startswith("*") and len(stripped) > 1):
        return True

    return False


def is_free_format_comment(line: str) -> bool:
    """
    Check if a line is a free-format COBOL comment (*> style).

    Args:
        line: The source line to check

    Returns:
        True if this is a free-format comment line
    """
    stripped = line.lstrip()
    # Free-format: *> comment or * at start (but not in column 7 position)
    if stripped.startswith("*>"):
        return True
    if stripped.startswith("*"):
        # It's free-format if it's not a fixed-format comment
        # Fixed format has exactly 6 chars before the *
        if len(line) < 7 or line[6] != "*":
            return True
    return False


def is_divider_line(comment_text: str) -> bool:
    """
    Check if a comment is a structural divider.

    Dividers are lines like:
    - All dashes: *-----------
    - All asterisks: ***********
    - All equals: *===========
    - Mixed patterns: *-*-*-*-*-*
    - Box borders with mostly whitespace: *                    *

    Args:
        comment_text: The comment text (after column 7)

    Returns:
        True if this is a divider line
    """
    text = comment_text.strip()
    if not text:
        return True  # Empty comment is a divider

    # Check if text contains only non-alphanumeric characters (divider symbols)
    alphanumeric_count = sum(1 for c in text if c.isalnum())
    if alphanumeric_count == 0:
        # Only non-alphanumeric chars - this is a divider (e.g., "*", "---", "*-*-*")
        return True

    # Check if it's mostly non-alphanumeric (2 or fewer letters/digits in 3+ chars)
    if alphanumeric_count <= 2 and len(text) >= 3:
        return True

    # Check for repeating patterns
    if len(set(text)) <= 3 and len(text) >= 5:
        # Only a few unique characters, likely a divider
        if all(c in "-*=+#_|/" for c in text):
            return True

    return False


def remove_personal_names(text: str, counter: int = 0) -> tuple[str, list[tuple[str, str]]]:
    """
    Remove personal names from comment text.

    Args:
        text: The comment text
        counter: Counter for generating replacement text

    Returns:
        Tuple of (transformed text, list of changes)
    """
    changes = []
    result = text

    for name in PERSONAL_NAMES:
        pattern = re.compile(rf"\b{name}\b", re.IGNORECASE)
        if pattern.search(result):
            replacement = f"USER{counter:03d}"
            result = pattern.sub(replacement, result)
            changes.append((name, replacement))
            counter += 1

    return result, changes


def remove_system_ids(text: str) -> tuple[str, list[tuple[str, str]]]:
    """
    Remove system identifiers from comment text.

    Args:
        text: The comment text

    Returns:
        Tuple of (transformed text, list of changes)
    """
    changes = []
    result = text

    for pattern_str in SYSTEM_ID_PATTERNS:
        pattern = re.compile(pattern_str)
        matches = pattern.findall(result)
        for match in matches:
            if len(match) >= 8:  # Only replace significant IDs
                replacement = "XXXXXXXX"
                result = result.replace(match, replacement, 1)
                changes.append((match, replacement))

    return result, changes


def translate_italian_terms(text: str) -> tuple[str, list[tuple[str, str]]]:
    """
    Translate Italian business terms to English.

    Args:
        text: The comment text

    Returns:
        Tuple of (transformed text, list of changes)
    """
    changes = []
    result = text

    # Sort by length (longest first) to avoid partial replacements
    sorted_terms = sorted(ITALIAN_TERMS.items(), key=lambda x: len(x[0]), reverse=True)

    for italian, english in sorted_terms:
        pattern = re.compile(rf"\b{italian}\b", re.IGNORECASE)
        if pattern.search(result):
            result = pattern.sub(english, result)
            changes.append((italian, english))

    return result, changes


def strip_comment(comment_text: str, preserve_dividers: bool = True) -> str:
    """
    Strip comment content, optionally preserving dividers.

    Args:
        comment_text: The comment text (after column 7)
        preserve_dividers: If True, keep divider lines

    Returns:
        Stripped or preserved comment text
    """
    if preserve_dividers and is_divider_line(comment_text):
        return comment_text
    return ""


class CommentTransformer:
    """
    Transforms COBOL comments according to configuration.

    Usage:
        transformer = CommentTransformer(config)
        result = transformer.transform_comment(comment_text)
    """

    def __init__(self, config: Optional[CommentConfig] = None):
        """
        Initialize the comment transformer.

        Args:
            config: Configuration options (uses defaults if not provided)
        """
        self.config = config or CommentConfig()
        self._line_counter = 0

    def transform_comment(self, comment_text: str) -> CommentTransformResult:
        """
        Transform a comment according to configuration.

        Args:
            comment_text: The comment text (after column 7)

        Returns:
            CommentTransformResult with transformation details
        """
        result = CommentTransformResult(
            original_text=comment_text,
            transformed_text=comment_text,
        )

        # Check for divider lines
        if is_divider_line(comment_text):
            result.is_divider = True
            if self.config.preserve_dividers:
                return result

        # Handle different modes
        if self.config.mode == CommentMode.PRESERVE:
            return result

        if self.config.mode == CommentMode.STRIP:
            if self.config.preserve_dividers and result.is_divider:
                return result
            result.transformed_text = ""
            result.is_stripped = True
            return result

        # Anonymize mode - generate meaningless filler text
        # Preserve leading whitespace
        stripped = comment_text.lstrip()
        leading_spaces = len(comment_text) - len(stripped)

        if not stripped:
            # Empty or whitespace-only comment
            return result

        # Calculate seed for this line (for reproducibility)
        seed = None
        if self.config.seed is not None:
            seed = self.config.seed + self._line_counter

        # Generate filler text matching the length of the actual content
        content_length = len(stripped)
        filler = generate_filler_text(content_length, seed)

        # Reconstruct with original leading whitespace
        transformed = " " * leading_spaces + filler

        self._line_counter += 1
        result.transformed_text = transformed
        result.changes_made = [(comment_text.strip(), filler.strip())]
        return result

    def transform_line(self, line: str) -> tuple[str, CommentTransformResult]:
        """
        Transform a complete COBOL line if it's a comment.

        Handles both fixed-format (column 7 = *) and free-format (*> style) comments.

        Args:
            line: The complete COBOL source line

        Returns:
            Tuple of (transformed line, result details)
        """
        if not is_comment_line(line):
            # Not a comment, return unchanged
            return line, CommentTransformResult(
                original_text="",
                transformed_text="",
            )

        # Check if this is a free-format comment
        if is_free_format_comment(line):
            return self._transform_free_format_comment(line)

        # Fixed-format: Extract comment text (everything after column 7)
        prefix = line[:7]  # Columns 1-7 (including the *)
        comment_text = line[7:] if len(line) > 7 else ""

        # Transform the comment
        result = self.transform_comment(comment_text)

        # Reconstruct the line
        if result.is_stripped and not result.is_divider:
            # Empty comment
            transformed_line = prefix
        else:
            transformed_line = prefix + result.transformed_text

        return transformed_line, result

    def _transform_free_format_comment(self, line: str) -> tuple[str, CommentTransformResult]:
        """
        Transform a free-format COBOL comment (*> style).

        Args:
            line: The complete source line with free-format comment

        Returns:
            Tuple of (transformed line, result details)
        """
        stripped = line.lstrip()
        leading_spaces = line[: len(line) - len(stripped)]

        # Determine the comment prefix (*> or *)
        if stripped.startswith("*>"):
            prefix = "*>"
            comment_text = stripped[2:]
        else:
            prefix = "*"
            comment_text = stripped[1:]

        # Check for space after prefix
        if comment_text.startswith(" "):
            prefix += " "
            comment_text = comment_text[1:]

        # Transform the comment text
        result = self.transform_comment(comment_text)

        # Reconstruct the line
        if result.is_stripped and not result.is_divider:
            # Empty comment - keep just the prefix
            transformed_line = leading_spaces + prefix.rstrip()
        else:
            transformed_line = leading_spaces + prefix + result.transformed_text

        return transformed_line, result

    def reset(self) -> None:
        """Reset the transformer state."""
        self._line_counter = 0


def anonymize_comment(
    comment_text: str,
    config: Optional[CommentConfig] = None,
) -> str:
    """
    Convenience function to anonymize a single comment.

    Args:
        comment_text: The comment text
        config: Optional configuration

    Returns:
        Anonymized comment text
    """
    transformer = CommentTransformer(config)
    result = transformer.transform_comment(comment_text)
    return result.transformed_text


def detect_comment_lines(lines: list[str]) -> list[int]:
    """
    Find all comment line numbers in a file.

    Args:
        lines: List of source lines

    Returns:
        List of 1-based line numbers that are comments
    """
    return [i + 1 for i, line in enumerate(lines) if is_comment_line(line)]


def get_comment_statistics(lines: list[str]) -> dict[str, int]:
    """
    Get statistics about comments in a file.

    Args:
        lines: List of source lines

    Returns:
        Dictionary with comment statistics
    """
    comment_lines = [line for line in lines if is_comment_line(line)]
    divider_lines = [
        line for line in comment_lines if is_divider_line(line[7:] if len(line) > 7 else "")
    ]

    return {
        "total_lines": len(lines),
        "comment_lines": len(comment_lines),
        "divider_lines": len(divider_lines),
        "content_comments": len(comment_lines) - len(divider_lines),
        "comment_percentage": round(100 * len(comment_lines) / max(len(lines), 1), 1),
    }
