"""Motor puro de política versionada."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_ACTIONS = frozenset({"KEEP", "GENERALIZE", "REDACT", "REVIEW"})


@dataclass(frozen=True)
class Policy:
    policy_id: str
    version: str
    default_action: str
    rules: dict[str, str]
    review_provisional_action: str = "REDACT"

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "Policy":
        if not isinstance(value, dict):
            raise ValueError("policy_object_required")
        policy_id = value.get("policy_id")
        version = value.get("version")
        default_action = value.get("default_action")
        rules = value.get("rules")
        review = value.get("review", {})
        if not all(isinstance(item, str) and item for item in (policy_id, version)):
            raise ValueError("policy_identity_invalid")
        if default_action not in _ACTIONS:
            raise ValueError("policy_default_action_invalid")
        if not isinstance(rules, dict):
            raise ValueError("policy_rules_invalid")
        if any(not isinstance(label, str) or action not in _ACTIONS for label, action in rules.items()):
            raise ValueError("policy_rule_invalid")
        provisional = review.get("provisional_action", "REDACT")
        if provisional not in {"GENERALIZE", "REDACT", "REVIEW"}:
            raise ValueError("policy_review_action_invalid")
        return cls(policy_id, version, default_action, dict(rules), provisional)

    @classmethod
    def load(cls, path: str | Path) -> "Policy":
        try:
            with Path(path).open(encoding="utf-8") as handle:
                value = json.load(handle)
        except (OSError, ValueError) as exc:
            raise ValueError("policy_load_failed") from exc
        return cls.from_mapping(value)


@dataclass(frozen=True)
class PolicyDecision:
    label: str
    action: str
    overridden: bool = False
    provisional: bool = False


def decide(
    label: str,
    policy: Policy,
    *,
    policy_override: dict[str, str] | None = None,
) -> PolicyDecision:
    if not isinstance(label, str) or not label:
        raise ValueError("label_invalid")
    if policy_override is not None:
        if not isinstance(policy_override, dict):
            raise ValueError("policy_override_invalid")
        invalid = [action for action in policy_override.values() if action not in _ACTIONS]
        if invalid:
            raise ValueError("policy_override_action_invalid")
        if label in policy_override:
            action = policy_override[label]
            if action == "REVIEW":
                action = policy.review_provisional_action
                return PolicyDecision(label, action, overridden=True, provisional=True)
            return PolicyDecision(label, action, overridden=True)

    action = policy.rules.get(label, policy.default_action)
    if action == "REVIEW":
        return PolicyDecision(
            label,
            policy.review_provisional_action,
            provisional=True,
        )
    return PolicyDecision(label, action)
