"""Carga y validación de configuración TOML del Servicio."""

from __future__ import annotations

import hashlib
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    tls_cert: str | None
    tls_key: str | None
    llm_base_url: str
    llm_model: str
    llm_ca_file: str | None
    llm_timeout_s: float
    llm_seed: int
    max_concurrency: int
    max_text_bytes: int
    diagnostic_mode: bool
    consumer_tokens: dict[str, str]
    llm_api_key: str | None

    @property
    def llm_endpoint_id(self) -> str:
        return hashlib.sha256(self.llm_base_url.encode("utf-8")).hexdigest()[:16]


def load_settings(path: str | Path, *, environ: dict[str, str] | None = None) -> Settings:
    environment = os.environ if environ is None else environ
    try:
        with Path(path).open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError("config_load_failed") from exc
    consumer_tokens = raw.get("consumer_tokens", {})
    if not isinstance(consumer_tokens, dict):
        raise ValueError("consumer_tokens_invalid")
    tokens = {}
    for name, digest in consumer_tokens.items():
        if not isinstance(name, str) or not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("consumer_token_hash_invalid")
        try:
            int(digest, 16)
        except ValueError as exc:
            raise ValueError("consumer_token_hash_invalid") from exc
        tokens[name] = digest.lower()
    host = _string(raw, "host")
    port = _integer(raw, "port", 1, 65535)
    if host not in {"127.0.0.1", "localhost", "::1"} and not raw.get("tls_cert") and not raw.get("tls_key"):
        raise ValueError("tls_required_for_non_loopback")
    tls_cert = _optional_string(raw.get("tls_cert"), "tls_cert")
    tls_key = _optional_string(raw.get("tls_key"), "tls_key")
    if (tls_cert is None) != (tls_key is None):
        raise ValueError("tls_pair_required")
    return Settings(
        host=host,
        port=port,
        tls_cert=tls_cert,
        tls_key=tls_key,
        llm_base_url=_string(raw, "llm_base_url"),
        llm_model=_string(raw, "llm_model"),
        llm_ca_file=_optional_string(raw.get("llm_ca_file"), "llm_ca_file"),
        llm_timeout_s=_number(raw, "llm_timeout_s", 0.1),
        llm_seed=_integer(raw, "llm_seed", 0),
        max_concurrency=_integer(raw, "max_concurrency", 1),
        max_text_bytes=_integer(raw, "max_text_bytes", 1),
        diagnostic_mode=_boolean(raw, "diagnostic_mode"),
        consumer_tokens=tokens,
        llm_api_key=environment.get("PRIVACYGUARD_LLM_API_KEY"),
    )


def _string(data: dict[str, Any], name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError("config_" + name + "_invalid")
    return value


def _optional_string(value: Any, name: str) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError("config_" + name + "_invalid")
    return value


def _integer(data: dict[str, Any], name: str, minimum: int, maximum: int | None = None) -> int:
    value = data.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError("config_" + name + "_invalid")
    if maximum is not None and value > maximum:
        raise ValueError("config_" + name + "_invalid")
    return value


def _number(data: dict[str, Any], name: str, minimum: float) -> float:
    value = data.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < minimum:
        raise ValueError("config_" + name + "_invalid")
    return float(value)


def _boolean(data: dict[str, Any], name: str) -> bool:
    value = data.get(name)
    if not isinstance(value, bool):
        raise ValueError("config_" + name + "_invalid")
    return value
