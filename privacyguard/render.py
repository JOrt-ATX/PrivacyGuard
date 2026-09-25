"""Renderizado determinista sobre el texto original."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .placeholders import PlaceholderAllocator


@dataclass(frozen=True)
class RenderFinding:
    start: int
    end: int
    label: str
    action: str
    replacement: str | None = None


def render(
    original_text: str,
    findings: list[RenderFinding],
    allocator: PlaceholderAllocator,
    *,
    generalize: Callable[[str, str], str | None] | None = None,
) -> str:
    output: list[str] = []
    cursor = 0
    for finding in sorted(findings, key=lambda item: (item.start, item.end)):
        if finding.start < cursor or not 0 <= finding.start <= finding.end <= len(original_text):
            raise ValueError("render_span_invalid")
        output.append(original_text[cursor:finding.start])
        value = original_text[finding.start:finding.end]
        if finding.action == "KEEP":
            replacement = value
        elif finding.action in {"REDACT", "REVIEW"}:
            replacement = allocator.allocate(finding.label, value)
        elif finding.action == "GENERALIZE":
            if generalize is None:
                raise ValueError("generalization_missing")
            replacement = generalize(finding.label, value)
            if replacement is None:
                replacement = allocator.allocate(finding.label, value)
        else:
            raise ValueError("render_action_invalid")
        output.append(replacement)
        cursor = finding.end
    output.append(original_text[cursor:])
    return "".join(output)
