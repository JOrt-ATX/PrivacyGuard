"""Detectores deterministas de identificadores estructurados."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    start: int
    end: int
    label: str
    rule: str
    confidence: float = 1.0
    source: str = "RULE"


_EMAIL = re.compile(
    r"[A-Za-z0-9._%+-]+[ \t]*\r?\n?[ \t]*@[ \t]*\r?\n?[ \t]*"
    r"[A-Za-z0-9.-]+[ \t]*\r?\n?[ \t]*\.[ \t]*\r?\n?[ \t]*[A-Za-z]{2,}"
)
_URL = re.compile(r"(?:https?://[^\s]+)|(?:\bwww\.[^\s]+)", re.IGNORECASE)
_IBAN = re.compile(r"\bES\d{2}(?:[ -]?\d{4}){5}\b", re.IGNORECASE)
_NIE = re.compile(r"\b[XYZxyz]\d{7}[-\s]?[A-Za-z]\b")
_DNI = re.compile(r"\b\d{8}[-\s]?[A-Za-z]\b")
_PHONE = re.compile(r"(?:\+34[ .\-]?)?\b[6789](?:[ .\-]?\d){8}\b")
_LABELLED_POSTAL = re.compile(
    r"(?:c\.?\s*p\.?|código\s+postal)\s*:?\s*\d{5}", re.IGNORECASE
)
_POSTAL = re.compile(r"\b\d{5}\b")
_DATE_DMY = re.compile(
    r"\b(?:0?[1-9]|[12]\d|3[01])[/.\-](?:0?[1-9]|1[0-2])[/.\-]\d{4}\b"
)
_DATE_YMD = re.compile(
    r"\b\d{4}[/.\-](?:0?[1-9]|1[0-2])[/.\-](?:0?[1-9]|[12]\d|3[01])\b"
)
_DATE_TEXT = re.compile(
    r"\b(?:0?[1-9]|[12]\d|3[01])\s+de\s+(?:enero|febrero|marzo|abril|mayo|"
    r"junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)"
    r"\s+de\s+\d{4}\b",
    re.IGNORECASE,
)
_STANDARD_PREFIX = re.compile(r"\b(?:ISO|UNE|EN|IEC)\s*$", re.IGNORECASE)
_EMAIL_DOMAIN = re.compile(
    r"[A-Za-z0-9-]+[ \t\r\n]*\.[ \t\r\n]*[A-Za-z]{2,}"
)

_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("EMAIL", "email", _EMAIL),
    ("URL", "url", _URL),
    ("IBAN", "iban", _IBAN),
    ("DNI_NIE", "nie", _NIE),
    ("DNI_NIE", "dni", _DNI),
    ("PHONE", "phone", _PHONE),
    ("DATE_FULL", "date_text", _DATE_TEXT),
    ("DATE_FULL", "date_dmy", _DATE_DMY),
    ("DATE_FULL", "date_ymd", _DATE_YMD),
    ("POSTAL_CODE", "postal_labelled", _LABELLED_POSTAL),
    ("POSTAL_CODE", "postal_bare", _POSTAL),
)


def detect(text: str, *, exclude_standard_numbers: bool = False) -> list[Detection]:
    """Devuelve spans de reglas, ordenados de forma estable y sin solaparse.

    ``exclude_standard_numbers`` implementa la propuesta D-15. Se deja
    desactivado por defecto hasta que JJO apruebe la excepción de normas.
    """
    if not isinstance(text, str):
        raise TypeError("text_must_be_string")
    candidates: list[Detection] = []
    for label, rule, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            end = match.end()
            if label == "EMAIL":
                at = text.find("@", match.start(), match.end())
                domain = _EMAIL_DOMAIN.search(text, at + 1, match.end())
                if domain is None:
                    continue
                end = domain.end()
            if (
                label == "POSTAL_CODE"
                and rule == "postal_bare"
                and not 1000 <= int(match.group()) <= 52999
            ):
                continue
            if (
                exclude_standard_numbers
                and label == "POSTAL_CODE"
                and rule == "postal_bare"
                and _STANDARD_PREFIX.search(text[: match.start()])
            ):
                continue
            candidates.append(
                Detection(match.start(), end, label, rule)
            )
    candidates.sort(key=lambda item: (item.start, -(item.end - item.start), item.rule))
    selected: list[Detection] = []
    for candidate in candidates:
        if any(candidate.start < item.end and item.start < candidate.end for item in selected):
            continue
        selected.append(candidate)
    return selected
