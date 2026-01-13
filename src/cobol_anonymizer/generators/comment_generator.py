"""
Comment Handler - Anonymizes COBOL comments while preserving structure.

This module handles:
- Detecting comment lines (column 7 = `*`)
- Replacing Italian business terms with generic text
- Removing personal names, dates, and system identifiers
- Preserving comment structure and indentation
- Option to strip all comments
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum


class CommentMode(Enum):
    """Comment anonymization modes."""
    ANONYMIZE = "anonymize"  # Replace content with generic text
    STRIP = "strip"  # Remove comment content entirely
    PRESERVE = "preserve"  # Keep comments unchanged


@dataclass
class CommentConfig:
    """Configuration for comment handling."""
    mode: CommentMode = CommentMode.ANONYMIZE
    remove_personal_names: bool = True
    remove_system_ids: bool = True
    translate_italian: bool = True
    preserve_structural_markers: bool = True
    preserve_dividers: bool = True  # Keep lines like *------- or ******


# Italian to English term mappings for business domain
ITALIAN_TERMS: Dict[str, str] = {
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
PERSONAL_NAMES: Set[str] = {
    "MASON", "LUPO", "ROSSI", "BIANCHI", "FERRARI", "RUSSO",
    "ESPOSITO", "ROMANO", "COLOMBO", "RICCI", "MARINO", "GRECO",
    "BRUNO", "GALLO", "CONTI", "LEONE", "COSTA", "GIORDANO",
    "MANCINI", "RIZZO", "LOMBARDI", "MORETTI", "BARBIERI",
    "FONTANA", "SANTORO", "CARUSO", "MARIANI", "RINALDI",
    "MARCO", "LUCA", "ANDREA", "FRANCESCO", "GIUSEPPE",
    "GIOVANNI", "ANTONIO", "LUIGI", "MARIO", "PAOLO",
    "MARIA", "ANNA", "GIULIA", "SARA", "LAURA", "ELENA",
    "FRANCESCA", "CHIARA", "SILVIA", "VALENTINA",
}

# Regex patterns for system identifiers
SYSTEM_ID_PATTERNS = [
    r'\bCRQ\d{9,15}\b',  # CRQ numbers (e.g., CRQ000002478171)
    r'\bINC\d{9,15}\b',  # Incident numbers
    r'\bCHG\d{9,15}\b',  # Change numbers
    r'\bPRB\d{9,15}\b',  # Problem numbers
    r'\bREQ\d{9,15}\b',  # Request numbers
    r'\bSR\d{9,15}\b',   # Service request numbers
    r'\b\d{2}/\d{2}/\d{4}\b',  # Dates DD/MM/YYYY
    r'\b\d{4}/\d{2}/\d{2}\b',  # Dates YYYY/MM/DD
    r'\b\d{2}-\d{2}-\d{4}\b',  # Dates DD-MM-YYYY
    r'\b\d{8}\b',  # 8-digit dates YYYYMMDD
]


@dataclass
class CommentTransformResult:
    """Result of transforming a comment."""
    original_text: str
    transformed_text: str
    is_divider: bool = False
    is_stripped: bool = False
    changes_made: List[Tuple[str, str]] = field(default_factory=list)


def is_comment_line(line: str) -> bool:
    """
    Check if a line is a COBOL comment.

    Column 7 must contain '*' for a comment line.

    Args:
        line: The source line to check

    Returns:
        True if this is a comment line
    """
    if len(line) < 7:
        return False
    return line[6] == '*'


def is_divider_line(comment_text: str) -> bool:
    """
    Check if a comment is a structural divider.

    Dividers are lines like:
    - All dashes: *-----------
    - All asterisks: ***********
    - All equals: *===========
    - Mixed patterns: *-*-*-*-*-*

    Args:
        comment_text: The comment text (after column 7)

    Returns:
        True if this is a divider line
    """
    text = comment_text.strip()
    if not text:
        return True  # Empty comment is a divider

    # Check if it's mostly non-alphanumeric
    alphanumeric_count = sum(1 for c in text if c.isalnum())
    if alphanumeric_count <= 2 and len(text) >= 3:
        return True

    # Check for repeating patterns
    if len(set(text)) <= 3 and len(text) >= 5:
        # Only a few unique characters, likely a divider
        if all(c in '-*=+#_|/' for c in text):
            return True

    return False


def remove_personal_names(text: str, counter: int = 0) -> Tuple[str, List[Tuple[str, str]]]:
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
        pattern = re.compile(rf'\b{name}\b', re.IGNORECASE)
        if pattern.search(result):
            replacement = f"USER{counter:03d}"
            result = pattern.sub(replacement, result)
            changes.append((name, replacement))
            counter += 1

    return result, changes


def remove_system_ids(text: str) -> Tuple[str, List[Tuple[str, str]]]:
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


def translate_italian_terms(text: str) -> Tuple[str, List[Tuple[str, str]]]:
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
        pattern = re.compile(rf'\b{italian}\b', re.IGNORECASE)
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
        self._name_counter = 0

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

        # Anonymize mode
        transformed = comment_text
        all_changes = []

        # Remove system IDs first (before they get partially modified)
        if self.config.remove_system_ids:
            transformed, changes = remove_system_ids(transformed)
            all_changes.extend(changes)

        # Remove personal names
        if self.config.remove_personal_names:
            transformed, changes = remove_personal_names(transformed, self._name_counter)
            all_changes.extend(changes)
            self._name_counter += len(changes)

        # Translate Italian terms
        if self.config.translate_italian:
            transformed, changes = translate_italian_terms(transformed)
            all_changes.extend(changes)

        result.transformed_text = transformed
        result.changes_made = all_changes
        return result

    def transform_line(self, line: str) -> Tuple[str, CommentTransformResult]:
        """
        Transform a complete COBOL line if it's a comment.

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

        # Extract comment text (everything after column 7)
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

    def reset(self) -> None:
        """Reset the transformer state."""
        self._name_counter = 0


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


def detect_comment_lines(lines: List[str]) -> List[int]:
    """
    Find all comment line numbers in a file.

    Args:
        lines: List of source lines

    Returns:
        List of 1-based line numbers that are comments
    """
    return [i + 1 for i, line in enumerate(lines) if is_comment_line(line)]


def get_comment_statistics(lines: List[str]) -> Dict[str, int]:
    """
    Get statistics about comments in a file.

    Args:
        lines: List of source lines

    Returns:
        Dictionary with comment statistics
    """
    comment_lines = [line for line in lines if is_comment_line(line)]
    divider_lines = [
        line for line in comment_lines
        if is_divider_line(line[7:] if len(line) > 7 else "")
    ]

    return {
        "total_lines": len(lines),
        "comment_lines": len(comment_lines),
        "divider_lines": len(divider_lines),
        "content_comments": len(comment_lines) - len(divider_lines),
        "comment_percentage": round(100 * len(comment_lines) / max(len(lines), 1), 1),
    }
