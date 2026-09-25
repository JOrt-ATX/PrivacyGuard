"""Verificación P0 del endpoint LLM interno.

La herramienta no guarda peticiones ni respuestas y nunca imprime el contenido
de una respuesta. La clave se obtiene exclusivamente de una variable de
entorno. Está pensada para ejecutarse con texto sintético.
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from statistics import mean
from typing import Any


DEFAULT_BASE_URL = "https://172.21.28.81/v1"
DEFAULT_MODEL = "qwen3.6-27b"
API_KEY_ENV = "PRIVACYGUARD_LLM_API_KEY"
SYNTHETIC_TEXT = (
    "Perfil profesional sintético. Experiencia en gestión de proyectos, "
    "calidad, seguridad y mejora continua. "
)
RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "text": {"type": "string"},
                    "label": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["text", "label", "confidence"],
            },
        }
    },
    "required": ["entities"],
}


class VerificationError(Exception):
    """Error operativo que se puede mostrar sin revelar datos de la petición."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("PRIVACYGUARD_LLM_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--model", default=os.environ.get("PRIVACYGUARD_LLM_MODEL", DEFAULT_MODEL))
    parser.add_argument("--ca-file", default=os.environ.get("PRIVACYGUARD_LLM_CA_FILE"))
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--seed", type=int, default=20260925)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--text-chars", type=int, default=6000)
    return parser


def _validate_base_url(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url.rstrip("/"))
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise VerificationError("base_url_invalid")
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" and hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise VerificationError("tls_required")
    if parsed.path.rstrip("/").endswith("/v1"):
        return parsed.geturl().rstrip("/")
    return parsed.geturl().rstrip("/") + "/v1"


def _context(ca_file: str | None) -> ssl.SSLContext:
    try:
        return ssl.create_default_context(cafile=ca_file)
    except (OSError, ssl.SSLError) as exc:
        raise VerificationError("tls_context_invalid") from exc


def _request(
    base_url: str,
    path: str,
    api_key: str,
    timeout: float,
    context: ssl.SSLContext,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    body = None
    headers = {"Authorization": "Bearer " + api_key, "Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        base_url + path,
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            return json.load(response)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as exc:
        raise VerificationError("request_failed") from exc


def _synthetic_text(length: int) -> str:
    if length < 1:
        raise VerificationError("text_length_invalid")
    repeats = (length + len(SYNTHETIC_TEXT) - 1) // len(SYNTHETIC_TEXT)
    return (SYNTHETIC_TEXT * repeats)[:length]


def _completion_payload(model: str, text: str, seed: int) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Devuelve JSON siguiendo exactamente el esquema. "
                    "Detecta entidades solo en el texto recibido."
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0,
        "seed": seed,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "privacy_entities",
                "strict": True,
                "schema": RESPONSE_SCHEMA,
            },
        },
        "chat_template_kwargs": {"enable_thinking": False},
    }


def _check_completion_shape(response: Any) -> None:
    if not isinstance(response, dict):
        raise VerificationError("completion_shape_invalid")
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise VerificationError("completion_choices_missing")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise VerificationError("completion_content_invalid")
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError as exc:
        raise VerificationError("completion_json_invalid") from exc
    if not isinstance(decoded, dict) or not isinstance(decoded.get("entities"), list):
        raise VerificationError("completion_schema_invalid")


def run(args: argparse.Namespace) -> int:
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        raise VerificationError("api_key_missing")
    base_url = _validate_base_url(args.base_url)
    if args.iterations < 1 or args.iterations > 20:
        raise VerificationError("iterations_invalid")
    context = _context(args.ca_file)
    models = _request(base_url, "/models", api_key, args.timeout, context)
    model_ids = {
        item.get("id")
        for item in models.get("data", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    } if isinstance(models, dict) else set()
    if args.model not in model_ids:
        raise VerificationError("configured_model_not_listed")

    payload = _completion_payload(args.model, _synthetic_text(args.text_chars), args.seed)
    durations: list[float] = []
    responses: list[str] = []
    for _ in range(args.iterations):
        started = time.perf_counter()
        response = _request(
            base_url,
            "/chat/completions",
            api_key,
            args.timeout,
            context,
            method="POST",
            payload=payload,
        )
        durations.append(time.perf_counter() - started)
        _check_completion_shape(response)
        responses.append(json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    print("models_endpoint=ok")
    print("configured_model_listed=yes")
    print("chat_completion=ok")
    print("temperature_zero=sent")
    print("seed=sent")
    print("json_schema=accepted")
    print("thinking_disabled=sent")
    print("iterations=" + str(len(responses)))
    print("identical_responses=" + ("yes" if len(set(responses)) == 1 else "no"))
    print("latency_ms_min={:.1f}".format(min(durations) * 1000))
    print("latency_ms_mean={:.1f}".format(mean(durations) * 1000))
    print("latency_ms_max={:.1f}".format(max(durations) * 1000))
    return 0


def main() -> int:
    try:
        return run(_parser().parse_args())
    except VerificationError as exc:
        print("verification_failed=" + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
