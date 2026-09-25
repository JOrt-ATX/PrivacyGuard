"""E2 — Anonimización capa 1: regex determinista, local, sin LLM (RF-3, CLAUDE.md restricción 5).

Se ejecuta SIEMPRE antes de cualquier llamada al LLM (E3). Cubre los tipos de
dato explícitamente listados en CLAUDE.md: email, teléfono (+34 y formatos
ES), DNI/NIE/NIF, IBAN, URLs, códigos postales y fechas absolutas. Cada
eliminación se registra con categoría RGPD y tipo (nunca con el valor
original: el propio log debe poder auditarse sin reintroducir el dato
eliminado).

Nombres propios, marcadores de género, datos del art. 9 RGPD y referencias a
terceros NO se tratan aquí: sobreviven a la capa 1 por diseño (no son
detectables de forma fiable por regex) y los elimina la capa 2 (LLM,
``core/anon_layer2.py``), tal como documenta la sección 5.4 del documento de
requisitos.

Supuesto documentado (pendiente de validación en la puerta F1): "fechas
absolutas" se interpreta como fechas completas día-mes-año (p. ej. fecha de
nacimiento o de expedición de un documento), NO como los rangos mes/año que
describen periodos de experiencia laboral en un CV (p. ej. "03/2020 -
07/2024"). Eliminar estos últimos destruiría la información de seniority que
el juicio E4 necesita valorar. Solo se elimina una fecha cuando el texto
incluye explícitamente un día.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CATEGORY_DATO_CONTACTO = "dato_contacto"
CATEGORY_IDENTIFICADOR_OFICIAL = "identificador_oficial"
CATEGORY_DATO_FINANCIERO = "dato_financiero"
CATEGORY_IDENTIFICADOR_WEB = "identificador_web"
CATEGORY_DATO_LOCALIZACION = "dato_localizacion"
CATEGORY_DATO_FECHA = "dato_fecha"

TYPE_EMAIL = "email"
TYPE_TELEFONO = "telefono"
TYPE_DNI_NIE = "dni_nie"
TYPE_IBAN = "iban"
TYPE_URL = "url"
TYPE_CODIGO_POSTAL = "codigo_postal"
TYPE_FECHA_ABSOLUTA = "fecha_absoluta"


@dataclass(frozen=True)
class Layer1Removal:
    category: str
    type: str
    placeholder: str


@dataclass(frozen=True)
class Layer1Result:
    anonymized_text: str
    removals: list[Layer1Removal] = field(default_factory=list)

    @property
    def counts_by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for removal in self.removals:
            counts[removal.category] = counts.get(removal.category, 0) + 1
        return counts

    @property
    def total_removals(self) -> int:
        return len(self.removals)


# ---------------------------------------------------------------------------
# Patrones
# ---------------------------------------------------------------------------

# Email: se permiten espacios/saltos de línea alrededor de "@" y del punto
# final para cubrir el caso límite de email partido por el maquetado del PDF
# (p. ej. "juan.perez@\nempresa.com" o "juan.perez @ empresa . com").
_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+[ \t]*\r?\n?[ \t]*@[ \t]*\r?\n?[ \t]*"
    r"[A-Za-z0-9.-]+[ \t]*\r?\n?[ \t]*\.[ \t]*\r?\n?[ \t]*[A-Za-z]{2,}"
)

# URLs con esquema explícito o con "www." al inicio.
_URL_RE = re.compile(
    r"(?:https?://[^\s]+)|(?:\bwww\.[^\s]+)",
    re.IGNORECASE,
)

# IBAN español: ES + 2 dígitos de control + 20 dígitos, con o sin espacios
# cada 4 caracteres.
_IBAN_RE = re.compile(r"\bES\d{2}(?:[ -]?\d{4}){5}\b", re.IGNORECASE)

# DNI: 8 dígitos + letra. NIE: X/Y/Z + 7 dígitos + letra. Con o sin guion o
# espacio entre el bloque numérico y la letra de control (no se valida el
# dígito/letra de control: para anonimización basta con el patrón).
_DNI_RE = re.compile(r"\b\d{8}[-\s]?[A-Za-z]\b")
_NIE_RE = re.compile(r"\b[XYZxyz]\d{7}[-\s]?[A-Za-z]\b")

# Teléfono español: prefijo +34 opcional, luego 9 dígitos que empiezan por
# 6/7/8/9, admitiendo un separador opcional (espacio, punto o guion) delante
# de cada dígito individual. Esto cubre cualquier agrupación habitual (todo
# junto, 3-3-3, 2-3-2-2, etc.) sin enumerar cada formato por separado.
_PHONE_RE = re.compile(r"(?:\+34[ .\-]?)?\b[6789](?:[ .\-]?\d){8}\b")

# Código postal explícito (precedido por una etiqueta): alta precisión.
_LABELLED_CP_RE = re.compile(
    r"(?:c\.?\s*p\.?|código\s+postal)\s*:?\s*(\d{5})",
    re.IGNORECASE,
)

# Código postal español "suelto": 5 dígitos dentro del rango de provincias
# españolas (01000-52999). Heurística deliberadamente conservadora: en
# anonimización, un falso positivo (eliminar un número que no era un CP) es
# preferible a una fuga de dato personal.
_BARE_CP_RE = re.compile(r"\b\d{5}\b")

_SPANISH_MONTHS = (
    "enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre"
    "|octubre|noviembre|diciembre"
)

# Fecha numérica completa día-mes-año: 10/07/2026, 10-07-2026, 10.07.2026,
# 2026-07-10. Requiere los tres componentes; un simple "07/2026" (periodo de
# experiencia) no coincide porque exige un componente de 3-4 dígitos y otro
# de 1-2 dígitos distintos en la misma fecha en las posiciones correctas.
_DATE_DMY_RE = re.compile(
    r"\b(0?[1-9]|[12]\d|3[01])[/.\-](0?[1-9]|1[0-2])[/.\-](\d{4})\b"
)
_DATE_YMD_RE = re.compile(
    r"\b(\d{4})[/.\-](0?[1-9]|1[0-2])[/.\-](0?[1-9]|[12]\d|3[01])\b"
)
# Fecha textual: "10 de julio de 2026".
_DATE_TEXTUAL_RE = re.compile(
    rf"\b(0?[1-9]|[12]\d|3[01])\s+de\s+(?:{_SPANISH_MONTHS})\s+de\s+(\d{{4}})\b",
    re.IGNORECASE,
)

_CP_MIN = 1000
_CP_MAX = 52999


def anonymize_layer1(text: str) -> Layer1Result:
    """Aplica la anonimización capa 1 y devuelve el texto y el log de eliminaciones.

    El orden de aplicación importa: los patrones más específicos (email,
    URL, IBAN, DNI/NIE, teléfono, fechas) se aplican antes que el código
    postal "suelto", que es el más propenso a falsos positivos y así evita
    consumir dígitos que ya pertenecen a un patrón más específico.
    """
    removals: list[Layer1Removal] = []

    text = _apply(text, _EMAIL_RE, CATEGORY_DATO_CONTACTO, TYPE_EMAIL, removals)
    text = _apply(text, _URL_RE, CATEGORY_IDENTIFICADOR_WEB, TYPE_URL, removals)
    text = _apply(text, _IBAN_RE, CATEGORY_DATO_FINANCIERO, TYPE_IBAN, removals)
    text = _apply(text, _NIE_RE, CATEGORY_IDENTIFICADOR_OFICIAL, TYPE_DNI_NIE, removals)
    text = _apply(text, _DNI_RE, CATEGORY_IDENTIFICADOR_OFICIAL, TYPE_DNI_NIE, removals)
    text = _apply(text, _PHONE_RE, CATEGORY_DATO_CONTACTO, TYPE_TELEFONO, removals)
    text = _apply(text, _DATE_TEXTUAL_RE, CATEGORY_DATO_FECHA, TYPE_FECHA_ABSOLUTA, removals)
    text = _apply(text, _DATE_DMY_RE, CATEGORY_DATO_FECHA, TYPE_FECHA_ABSOLUTA, removals)
    text = _apply(text, _DATE_YMD_RE, CATEGORY_DATO_FECHA, TYPE_FECHA_ABSOLUTA, removals)
    text = _apply(
        text, _LABELLED_CP_RE, CATEGORY_DATO_LOCALIZACION, TYPE_CODIGO_POSTAL, removals
    )
    text = _apply_bare_postal_code(text, removals)

    return Layer1Result(anonymized_text=text, removals=removals)


def _apply(
    text: str,
    pattern: re.Pattern[str],
    category: str,
    type_: str,
    removals: list[Layer1Removal],
) -> str:
    def _replace(match: re.Match[str]) -> str:
        index = sum(1 for r in removals if r.type == type_) + 1
        placeholder = f"[{type_.upper()}_{index}]"
        removals.append(Layer1Removal(category=category, type=type_, placeholder=placeholder))
        return placeholder

    return pattern.sub(_replace, text)


def _apply_bare_postal_code(text: str, removals: list[Layer1Removal]) -> str:
    def _replace(match: re.Match[str]) -> str:
        value = int(match.group(0))
        if not (_CP_MIN <= value <= _CP_MAX):
            return match.group(0)
        index = sum(1 for r in removals if r.type == TYPE_CODIGO_POSTAL) + 1
        placeholder = f"[{TYPE_CODIGO_POSTAL.upper()}_{index}]"
        removals.append(
            Layer1Removal(
                category=CATEGORY_DATO_LOCALIZACION,
                type=TYPE_CODIGO_POSTAL,
                placeholder=placeholder,
            )
        )
        return placeholder

    return _BARE_CP_RE.sub(_replace, text)
