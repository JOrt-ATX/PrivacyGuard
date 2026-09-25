"""Normalización determinista con mapa de offsets al texto original."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


_EMAIL_SPACING_RE = re.compile(
    r"[A-Za-z0-9._%+-]+(?:[ \t\r\n]+[A-Za-z0-9._%+-]+)*"
    r"[ \t\r\n]*@[ \t\r\n]*"
    r"[A-Za-z0-9.-]+[ \t\r\n]*\.[ \t\r\n]*[A-Za-z]{2,}",
)


@dataclass(frozen=True)
class NormalizedText:
    """Texto normalizado y correspondencia de cada carácter con el original."""

    text: str
    offsets: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        if len(self.text) != len(self.offsets):
            raise ValueError("text_offsets_length_mismatch")
        previous_end = 0
        for start, end in self.offsets:
            if start < previous_end or end <= start:
                raise ValueError("offsets_not_monotonic")
            previous_end = end

    def original_span(self, start: int, end: int) -> tuple[int, int]:
        """Devuelve el span original que cubre ``[start:end]`` normalizado."""
        if not 0 <= start <= end <= len(self.text):
            raise IndexError("normalized_offset_out_of_range")
        if start == end:
            if start == len(self.offsets):
                boundary = self.offsets[-1][1] if self.offsets else 0
            else:
                boundary = self.offsets[start][0]
            return boundary, boundary
        return self.offsets[start][0], self.offsets[end - 1][1]


def normalize(text: str) -> NormalizedText:
    """Normaliza ``text`` sin perder la localización en el original."""
    if not isinstance(text, str):
        raise TypeError("text_must_be_string")
    chars: list[str] = []
    offsets: list[tuple[int, int]] = []
    cluster: list[str] = []
    cluster_start = 0
    for index, character in enumerate(text):
        if cluster and not unicodedata.combining(character):
            _append_cluster(chars, offsets, cluster, cluster_start, index)
            cluster = []
        if not cluster:
            cluster_start = index
        cluster.append(character)
    _append_cluster(chars, offsets, cluster, cluster_start, len(text))

    _remove_line_break_hyphens(chars, offsets)
    _remove_email_spacing(chars, offsets)
    return NormalizedText("".join(chars), tuple(offsets))


def _append_cluster(
    chars: list[str],
    offsets: list[tuple[int, int]],
    cluster: list[str],
    start: int,
    end: int,
) -> None:
    if not cluster:
        return
    normalized = unicodedata.normalize("NFC", "".join(cluster)).replace("\u00a0", " ")
    if normalized == "\u00ad":
        return
    for output in normalized:
        chars.append(output)
        offsets.append((start, end))


def _remove_line_break_hyphens(chars: list[str], offsets: list[tuple[int, int]]) -> None:
    remove: set[int] = set()
    index = 0
    while index < len(chars):
        if chars[index] == "-" and index + 1 < len(chars) and chars[index + 1] in "\r\n":
            remove.add(index)
            cursor = index + 1
            while cursor < len(chars) and chars[cursor] in "\r\n ":
                remove.add(cursor)
                cursor += 1
        index += 1
    _remove_indices(chars, offsets, remove)


def _remove_email_spacing(chars: list[str], offsets: list[tuple[int, int]]) -> None:
    text = "".join(chars)
    remove: set[int] = set()
    for match in _EMAIL_SPACING_RE.finditer(text):
        for index in range(match.start(), match.end()):
            if chars[index].isspace() and (
                _near_symbol(chars, index, "@") or _near_symbol(chars, index, ".")
            ):
                remove.add(index)
    _remove_indices(chars, offsets, remove)


def _near_symbol(chars: list[str], index: int, symbol: str) -> bool:
    cursor = index - 1
    while cursor >= 0 and chars[cursor].isspace():
        cursor -= 1
    if cursor >= 0 and chars[cursor] == symbol:
        return True
    cursor = index + 1
    while cursor < len(chars) and chars[cursor].isspace():
        cursor += 1
    return cursor < len(chars) and chars[cursor] == symbol


def _remove_indices(
    chars: list[str], offsets: list[tuple[int, int]], remove: set[int]
) -> None:
    if not remove:
        return
    retained = [(char, offset) for index, (char, offset) in enumerate(zip(chars, offsets)) if index not in remove]
    chars[:] = [char for char, _ in retained]
    offsets[:] = [offset for _, offset in retained]
