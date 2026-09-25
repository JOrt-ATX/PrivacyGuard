"""Orquestación P1: normalización, reglas, política y renderizado."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .merge import Finding, merge_findings
from .normalize import normalize
from .placeholders import PlaceholderAllocator, PlaceholderCatalog
from .policy import Policy, decide
from .render import RenderFinding, render
from .rules import detect
from .schemas import validate_minimize_request, validate_minimize_response


class ContextualDetector(Protocol):
    def detect(self, text: str) -> list[Finding]:
        ...


class NullContextualDetector:
    """Implementación P1: no llama a ningún modelo contextual."""

    def detect(self, text: str) -> list[Finding]:
        return []


@dataclass(frozen=True)
class PipelineVersions:
    service: str = "1.0.0"
    rules: str = "1.0"
    preprocessing: str = "1.0"
    prompt_version: str | None = None
    llm_model: str | None = None
    llm_endpoint_id: str | None = None


class Pipeline:
    def __init__(
        self,
        *,
        policy: Policy,
        catalog: PlaceholderCatalog,
        labels: dict[str, dict[str, str]],
        generalization: dict[str, dict[str, str]] | None = None,
        contextual_detector: ContextualDetector | None = None,
        versions: PipelineVersions | None = None,
    ) -> None:
        self.policy = policy
        self.catalog = catalog
        self.labels = labels
        self.generalization = generalization or {}
        self.contextual_detector = contextual_detector or NullContextualDetector()
        self.versions = versions or PipelineVersions()

    @classmethod
    def from_files(
        cls,
        *,
        policy_path: str | Path,
        placeholders_path: str | Path,
        labels_path: str | Path,
        generalization_path: str | Path | None = None,
    ) -> "Pipeline":
        policy = Policy.load(policy_path)
        catalog = PlaceholderCatalog.load(placeholders_path)
        labels = _load_json(labels_path).get("labels")
        if not isinstance(labels, dict):
            raise ValueError("labels_catalog_invalid")
        generalization: dict[str, dict[str, str]] = {}
        if generalization_path is not None:
            raw = _load_json(generalization_path)
            entries = raw.get("format", {}).get("entries", {})
            if isinstance(entries, dict):
                generalization = {"LOCATION_CITY": entries}
        return cls(policy=policy, catalog=catalog, labels=labels, generalization=generalization)

    def minimize(
        self,
        request: dict[str, Any],
        *,
        max_text_bytes: int = 200 * 1024,
    ) -> dict[str, Any]:
        data = validate_minimize_request(
            request,
            max_text_bytes=max_text_bytes,
        )
        if data.get("policy_id") != self.policy.policy_id:
            raise ValueError("policy_id_unavailable")
        requested_version = data.get("policy_version")
        if requested_version is not None and requested_version != self.policy.version:
            raise ValueError("policy_version_unavailable")

        original_text = data["text"]
        normalized = normalize(original_text)
        rule_findings: list[Finding] = []
        for detection in detect(normalized.text):
            start, end = normalized.original_span(detection.start, detection.end)
            metadata = self.labels.get(detection.label, {})
            rule_findings.append(
                Finding(
                    start=start,
                    end=end,
                    label=detection.label,
                    source="RULE",
                    risk=metadata.get("risk", "HIGH"),
                    confidence=detection.confidence,
                    reason="STRUCTURED_IDENTIFIER",
                )
            )
        model_findings = self.contextual_detector.detect(normalized.text)
        findings = merge_findings([*rule_findings, *model_findings])
        allocator = PlaceholderAllocator(self.catalog)
        render_findings: list[RenderFinding] = []
        detections: list[dict[str, Any]] = []
        review_items: list[dict[str, Any]] = []
        for index, finding in enumerate(findings):
            decision = decide(
                finding.label,
                self.policy,
                policy_override=data.get("policy_override"),
            )
            metadata = self.labels.get(finding.label, {})
            render_findings.append(
                RenderFinding(
                    finding.start,
                    finding.end,
                    finding.label,
                    decision.action,
                )
            )
            item: dict[str, Any] = {
                "index": index,
                "label": finding.label,
                "start": finding.start,
                "end": finding.end,
                "action": decision.action,
                "confidence": finding.confidence,
                "risk": metadata.get("risk", finding.risk),
                "source": finding.source,
                "reason": finding.reason or "POLICY",
            }
            if decision.action in {"REDACT", "REVIEW"}:
                item["placeholder"] = allocator.allocate(
                    finding.label,
                    original_text[finding.start:finding.end],
                )
            detections.append(item)
            if decision.provisional:
                review_items.append(
                    {
                        "index": index,
                        "start": finding.start,
                        "end": finding.end,
                        "label": finding.label,
                        "confidence": finding.confidence,
                        "reason": "POLICY_REVIEW",
                        "provisional_action": decision.action,
                        "options": ["REDACT", "GENERALIZE", "KEEP"],
                    }
                )

        mode = data.get("mode", "enforce")
        sanitized = None
        if mode != "dry_run":
            sanitized = render(
                original_text,
                render_findings,
                allocator,
                generalize=self._generalize,
            )
        counts = Counter(item["action"] for item in detections)
        categories = Counter(
            self.labels.get(item["label"], {}).get("category_rgpd", "desconocida")
            for item in detections
        )
        response = {
            "request_id": data["request_id"],
            "status": "REVIEW_REQUIRED" if review_items else "OK",
            "sanitized_text": sanitized,
            "detections": detections,
            "review_items": review_items,
            "stats": {
                "detections_total": len(detections),
                "by_action": {action: counts.get(action, 0) for action in ("KEEP", "GENERALIZE", "REDACT", "REVIEW")},
                "by_category_rgpd": dict(sorted(categories.items())),
            },
            "versions": {
                "service": self.versions.service,
                "rules": self.versions.rules,
                "policy": self.policy.policy_id + "@" + self.policy.version,
                "preprocessing": self.versions.preprocessing,
                "placeholders": self.catalog.version,
                "llm_model": self.versions.llm_model,
                "prompt_version": self.versions.prompt_version,
                "llm_endpoint_id": self.versions.llm_endpoint_id,
            },
            "timing_ms": 0,
        }
        return validate_minimize_response(response)

    def _generalize(self, label: str, value: str) -> str | None:
        return self.generalization.get(label, {}).get(value.casefold())


def _load_json(path: str | Path) -> dict[str, Any]:
    try:
        with Path(path).open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, ValueError) as exc:
        raise ValueError("data_load_failed") from exc
    if not isinstance(value, dict):
        raise ValueError("data_object_required")
    return value
