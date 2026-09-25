"""Validadores stdlib para el contrato HTTP v1.

Los validadores rechazan campos desconocidos y no incluyen valores recibidos
en los mensajes de error, para evitar fugas accidentales.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class SchemaError(ValueError):
    """Error de validación sin datos literales de la petición."""

    def __init__(self, code: str, path: str = "$") -> None:
        super().__init__(code + ":" + path)
        self.code = code
        self.path = path


_ACTIONS = {"KEEP", "GENERALIZE", "REDACT", "REVIEW"}
_SOURCES = {"RULE", "MODEL"}
_STATUSES = {"OK", "REVIEW_REQUIRED"}
_MODES = {"enforce", "dry_run"}
_HEALTH_STATES = {"ok", "degraded", "loading"}


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaError("object_required", path)
    return value


def _fields(value: Mapping[str, Any], required: set[str], allowed: set[str], path: str) -> None:
    missing = required - value.keys()
    if missing:
        raise SchemaError("required_field", path)
    if set(value) - allowed:
        raise SchemaError("unknown_field", path)


def _string(value: Any, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value):
        raise SchemaError("string_required", path)
    return value


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaError("number_required", path)
    return float(value)


def _integer(value: Any, path: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SchemaError("integer_invalid", path)
    return value


def validate_minimize_request(value: Any, *, max_text_bytes: int = 200 * 1024) -> dict[str, Any]:
    data = _object(value, "$")
    _fields(
        data,
        {"request_id", "document_ref", "text", "policy_id"},
        {
            "request_id",
            "document_ref",
            "text",
            "language_hint",
            "policy_id",
            "policy_version",
            "mode",
            "policy_override",
        },
        "$",
    )
    result = dict(data)
    for field in ("request_id", "document_ref", "policy_id"):
        _string(data[field], "$." + field)
    text = _string(data["text"], "$.text")
    if len(text.encode("utf-8")) > max_text_bytes:
        raise SchemaError("text_too_large", "$.text")
    if "language_hint" in data:
        _string(data["language_hint"], "$.language_hint")
    if "policy_version" in data:
        _string(data["policy_version"], "$.policy_version")
    if "mode" in data and data["mode"] not in _MODES:
        raise SchemaError("enum_invalid", "$.mode")
    override = data.get("policy_override")
    if override is not None:
        override_data = _object(override, "$.policy_override")
        for label, action in override_data.items():
            _string(label, "$.policy_override")
            if action not in _ACTIONS:
                raise SchemaError("enum_invalid", "$.policy_override")
    return result


def _validate_detection(value: Any, index: int, text_length: int | None) -> None:
    path = "$.detections[" + str(index) + "]"
    data = _object(value, path)
    _fields(
        data,
        {"index", "label", "start", "end", "action", "confidence", "risk", "source", "reason"},
        {
            "index",
            "label",
            "start",
            "end",
            "action",
            "placeholder",
            "replacement",
            "confidence",
            "risk",
            "source",
            "reason",
        },
        path,
    )
    _integer(data["index"], path + ".index")
    start = _integer(data["start"], path + ".start")
    end = _integer(data["end"], path + ".end")
    if end < start or (text_length is not None and end > text_length):
        raise SchemaError("offset_invalid", path)
    _string(data["label"], path + ".label")
    if data["action"] not in _ACTIONS:
        raise SchemaError("enum_invalid", path + ".action")
    confidence = _number(data["confidence"], path + ".confidence")
    if not 0 <= confidence <= 1:
        raise SchemaError("confidence_invalid", path)
    _string(data["risk"], path + ".risk")
    if data["source"] not in _SOURCES:
        raise SchemaError("enum_invalid", path + ".source")
    _string(data["reason"], path + ".reason")
    for field in ("placeholder", "replacement"):
        if field in data:
            _string(data[field], path + "." + field)


def _validate_review_item(value: Any, index: int, text_length: int | None) -> None:
    path = "$.review_items[" + str(index) + "]"
    data = _object(value, path)
    _fields(
        data,
        {"index", "start", "end", "label", "confidence", "reason", "provisional_action", "options"},
        {
            "index",
            "start",
            "end",
            "label",
            "confidence",
            "reason",
            "provisional_action",
            "options",
        },
        path,
    )
    _integer(data["index"], path + ".index")
    start = _integer(data["start"], path + ".start")
    end = _integer(data["end"], path + ".end")
    if end < start or (text_length is not None and end > text_length):
        raise SchemaError("offset_invalid", path)
    _string(data["label"], path + ".label")
    confidence = _number(data["confidence"], path + ".confidence")
    if not 0 <= confidence <= 1:
        raise SchemaError("confidence_invalid", path)
    _string(data["reason"], path + ".reason")
    if data["provisional_action"] not in {"REDACT", "GENERALIZE", "REVIEW"}:
        raise SchemaError("enum_invalid", path + ".provisional_action")
    options = data["options"]
    if not isinstance(options, list) or not all(isinstance(option, str) and option for option in options):
        raise SchemaError("string_list_required", path + ".options")


def _validate_versions(value: Any) -> None:
    data = _object(value, "$.versions")
    _fields(
        data,
        {"service", "rules", "policy", "preprocessing", "placeholders", "llm_model", "prompt_version", "llm_endpoint_id"},
        set(data),
        "$.versions",
    )
    for field in data:
        if data[field] is not None:
            _string(data[field], "$.versions." + field)


def validate_minimize_response(value: Any) -> dict[str, Any]:
    data = _object(value, "$")
    _fields(
        data,
        {"request_id", "status", "sanitized_text", "detections", "review_items", "stats", "versions", "timing_ms"},
        set(data),
        "$",
    )
    _string(data["request_id"], "$.request_id")
    if data["status"] not in _STATUSES:
        raise SchemaError("enum_invalid", "$.status")
    if data["sanitized_text"] is not None:
        _string(data["sanitized_text"], "$.sanitized_text", allow_empty=True)
    detections = data["detections"]
    if not isinstance(detections, list):
        raise SchemaError("list_required", "$.detections")
    for index, detection in enumerate(detections):
        _validate_detection(detection, index, None)
    review_items = data["review_items"]
    if not isinstance(review_items, list):
        raise SchemaError("list_required", "$.review_items")
    for index, item in enumerate(review_items):
        _validate_review_item(item, index, None)
    _object(data["stats"], "$.stats")
    _validate_versions(data["versions"])
    _number(data["timing_ms"], "$.timing_ms")
    if data["timing_ms"] < 0:
        raise SchemaError("number_invalid", "$.timing_ms")
    if bool(review_items) != (data["status"] == "REVIEW_REQUIRED"):
        raise SchemaError("status_inconsistent", "$.status")
    return dict(data)


def validate_error_response(value: Any) -> dict[str, Any]:
    data = _object(value, "$")
    _fields(data, {"error_code", "message", "request_id"}, {"error_code", "message", "request_id"}, "$")
    for field in data:
        _string(data[field], "$." + field)
    return dict(data)


def validate_health_response(value: Any) -> dict[str, Any]:
    data = _object(value, "$")
    _fields(data, {"status", "versions"}, {"status", "versions", "model_loaded", "uptime_s"}, "$")
    if data["status"] not in _HEALTH_STATES:
        raise SchemaError("enum_invalid", "$.status")
    _validate_versions(data["versions"])
    if "model_loaded" in data and not isinstance(data["model_loaded"], bool):
        raise SchemaError("boolean_required", "$.model_loaded")
    if "uptime_s" in data:
        _number(data["uptime_s"], "$.uptime_s")
    return dict(data)


def validate_version_response(value: Any) -> dict[str, Any]:
    data = _object(value, "$")
    _fields(data, {"versions"}, {"versions"}, "$")
    _validate_versions(data["versions"])
    return dict(data)


def validate_catalog_response(value: Any, *, catalog: str) -> dict[str, Any]:
    data = _object(value, "$")
    _fields(data, {"version", catalog}, {"version", catalog}, "$")
    _string(data["version"], "$.version")
    _object(data[catalog], "$." + catalog)
    return dict(data)
