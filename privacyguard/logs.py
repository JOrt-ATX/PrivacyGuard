"""Logs JSON de contadores y metadatos, sin valores del documento."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from typing import TextIO, Any


_ALLOWED = {
    "event",
    "request_id",
    "consumer",
    "status_code",
    "detections_total",
    "by_action",
    "latency_ms",
    "error_code",
}


def write_event(event: Mapping[str, Any], *, stream: TextIO | None = None) -> None:
    safe = {key: value for key, value in event.items() if key in _ALLOWED}
    target = sys.stderr if stream is None else stream
    target.write(json.dumps(safe, ensure_ascii=True, sort_keys=True) + "\n")
    target.flush()
