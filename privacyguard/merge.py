"""Fusión determinista de hallazgos de reglas y modelo."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    start: int
    end: int
    label: str
    source: str
    risk: str
    confidence: float = 1.0
    reason: str = ""

    @property
    def span_length(self) -> int:
        return self.end - self.start


_SOURCE_PRIORITY = {"RULE": 0, "MODEL": 1}
_RISK_PRIORITY = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def merge_findings(findings: list[Finding]) -> list[Finding]:
    """Selecciona spans no solapados según la precedencia de RF-5."""
    ordered = sorted(
        findings,
        key=lambda item: (
            item.start,
            -item.span_length,
            _SOURCE_PRIORITY.get(item.source, 99),
            _RISK_PRIORITY.get(item.risk, 99),
            item.label,
            item.end,
        ),
    )
    selected: list[Finding] = []
    for candidate in ordered:
        overlaps = [
            item for item in selected
            if candidate.start < item.end and item.start < candidate.end
        ]
        if not overlaps:
            selected.append(candidate)
            continue
        winner = min(
            [candidate, *overlaps],
            key=lambda item: (
                -item.span_length,
                _SOURCE_PRIORITY.get(item.source, 99),
                _RISK_PRIORITY.get(item.risk, 99),
                item.label,
                item.start,
                item.end,
            ),
        )
        if winner is candidate:
            selected = [item for item in selected if item not in overlaps]
            selected.append(candidate)
    return sorted(selected, key=lambda item: (item.start, item.end, item.label))
