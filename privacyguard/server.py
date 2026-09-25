"""Servidor HTTP v1 del Servicio ATX PrivacyGuard."""

from __future__ import annotations

import hashlib
import hmac
import json
import ssl
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import unquote, urlparse

from .config import Settings
from .logs import write_event
from .pipeline import Pipeline
from .schemas import SchemaError


MAX_BODY_BYTES = 1_048_576


class PrivacyGuardHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], handler_class: type[BaseHTTPRequestHandler],
                 *, settings: Settings, pipeline: Pipeline, log_stream=None) -> None:
        super().__init__(address, handler_class)
        self.settings = settings
        self.pipeline = pipeline
        self.log_stream = log_stream
        self.started_at = time.monotonic()
        self.ready = True
        self.request_slots = threading.BoundedSemaphore(settings.max_concurrency)


class PrivacyGuardHandler(BaseHTTPRequestHandler):
    server: PrivacyGuardHTTPServer
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/v1/health" and self._is_loopback():
            self._json_response(HTTPStatus.OK, self._health())
            return
        if not self._authorized():
            return
        if path == "/v1/health":
            self._json_response(HTTPStatus.OK, self._health())
        elif path == "/v1/version":
            self._json_response(HTTPStatus.OK, {"versions": self._versions()})
        elif path == "/v1/policies":
            self._json_response(
                HTTPStatus.OK,
                {
                    "version": self.server.pipeline.policy.version,
                    "policies": [self.server.pipeline.policy.policy_id],
                },
            )
        elif path == "/v1/policies/" + self.server.pipeline.policy.policy_id:
            policy = self.server.pipeline.policy
            self._json_response(
                HTTPStatus.OK,
                {
                    "policy_id": policy.policy_id,
                    "version": policy.version,
                    "default_action": policy.default_action,
                    "rules": dict(sorted(policy.rules.items())),
                },
            )
        elif path == "/v1/placeholders":
            self._json_response(
                HTTPStatus.OK,
                {
                    "version": self.server.pipeline.catalog.version,
                    "placeholders": dict(sorted(self.server.pipeline.catalog.prefixes.items())),
                },
            )
        else:
            self._error(HTTPStatus.NOT_FOUND, "INVALID_REQUEST")

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/v1/minimize":
            self._error(HTTPStatus.NOT_FOUND, "INVALID_REQUEST")
            return
        if not self._authorized():
            return
        if not self.server.ready:
            self._error(HTTPStatus.SERVICE_UNAVAILABLE, "NOT_READY")
            return
        if not self.server.request_slots.acquire(blocking=False):
            self._error(HTTPStatus.TOO_MANY_REQUESTS, "BUSY")
            return
        started = time.perf_counter()
        request_id = "-"
        consumer = self._consumer_name()
        status_code = HTTPStatus.OK
        event: dict[str, Any] = {"event": "minimize", "consumer": consumer}
        try:
            raw = self._read_body()
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                status_code = HTTPStatus.UNPROCESSABLE_ENTITY
                self._error(status_code, "UNPROCESSABLE_TEXT")
                return
            if isinstance(data, dict) and isinstance(data.get("request_id"), str):
                request_id = data["request_id"]
            event["request_id"] = request_id
            try:
                result = self.server.pipeline.minimize(
                    data,
                    max_text_bytes=self.server.settings.max_text_bytes,
                )
            except SchemaError as exc:
                status_code = HTTPStatus.REQUEST_ENTITY_TOO_LARGE if exc.code == "text_too_large" else HTTPStatus.BAD_REQUEST
                code = "TEXT_TOO_LARGE" if exc.code == "text_too_large" else "INVALID_REQUEST"
                self._error(status_code, code, request_id)
                return
            except ValueError as exc:
                status_code, code = self._pipeline_error(exc)
                self._error(status_code, code, request_id)
                return
            self._json_response(status_code, result)
            event["detections_total"] = result["stats"]["detections_total"]
            event["by_action"] = result["stats"]["by_action"]
        except BodyTooLarge:
            status_code = HTTPStatus.REQUEST_ENTITY_TOO_LARGE
            self._error(status_code, "TEXT_TOO_LARGE", request_id)
        except (ConnectionError, OSError):
            status_code = HTTPStatus.BAD_REQUEST
            self._error(status_code, "INVALID_REQUEST", request_id)
        except Exception:
            status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            self._error(status_code, "INTERNAL", request_id)
        finally:
            event["status_code"] = int(status_code)
            event["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
            write_event(event, stream=self.server.log_stream)
            self.server.request_slots.release()

    def _authorized(self) -> bool:
        if not self.server.settings.consumer_tokens:
            return True
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            self._error(HTTPStatus.UNAUTHORIZED, "AUTH_REQUIRED")
            return False
        token = header[7:]
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        for name, expected in self.server.settings.consumer_tokens.items():
            if hmac.compare_digest(digest, expected):
                self._request_consumer = name
                return True
        self._error(HTTPStatus.UNAUTHORIZED, "AUTH_REQUIRED")
        return False

    def _consumer_name(self) -> str:
        return getattr(self, "_request_consumer", "local")

    def _read_body(self) -> bytes:
        length_header = self.headers.get("Content-Length")
        if length_header is None:
            raise BodyTooLarge()
        try:
            length = int(length_header)
        except ValueError as exc:
            raise BodyTooLarge() from exc
        if length < 0 or length > MAX_BODY_BYTES:
            raise BodyTooLarge()
        body = self.rfile.read(length)
        if len(body) != length:
            raise ConnectionError("body_incomplete")
        return body

    def _health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.server.ready else "loading",
            "versions": self._versions(),
            "model_loaded": False,
            "uptime_s": round(time.monotonic() - self.server.started_at, 3),
        }

    def _versions(self) -> dict[str, Any]:
        versions = self.server.pipeline.versions
        return {
            "service": versions.service,
            "rules": versions.rules,
            "policy": self.server.pipeline.policy.policy_id + "@" + self.server.pipeline.policy.version,
            "preprocessing": versions.preprocessing,
            "placeholders": self.server.pipeline.catalog.version,
            "llm_model": versions.llm_model,
            "prompt_version": versions.prompt_version,
            "llm_endpoint_id": versions.llm_endpoint_id,
        }

    def _pipeline_error(self, error: ValueError) -> tuple[HTTPStatus, str]:
        code = str(error)
        if code == "policy_version_unavailable":
            return HTTPStatus.CONFLICT, "POLICY_VERSION_UNAVAILABLE"
        if code == "policy_id_unavailable":
            return HTTPStatus.BAD_REQUEST, "INVALID_REQUEST"
        return HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL"

    def _error(self, status: HTTPStatus, code: str, request_id: str = "-") -> None:
        self._json_response(
            status,
            {"error_code": code, "message": _error_message(code), "request_id": request_id},
        )

    def _json_response(self, status: HTTPStatus, value: dict[str, Any]) -> None:
        body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _is_loopback(self) -> bool:
        return self.server.server_address[0] in {"127.0.0.1", "localhost", "::1"}

    def log_message(self, format: str, *args: Any) -> None:
        return


class BodyTooLarge(Exception):
    pass


def _error_message(code: str) -> str:
    messages = {
        "AUTH_REQUIRED": "Autenticación requerida",
        "INVALID_REQUEST": "Petición inválida",
        "POLICY_VERSION_UNAVAILABLE": "Versión de política no disponible",
        "TEXT_TOO_LARGE": "Texto demasiado grande",
        "UNPROCESSABLE_TEXT": "Texto no procesable",
        "BUSY": "Servicio ocupado",
        "NOT_READY": "Servicio no preparado",
        "INTERNAL": "Error interno",
    }
    return messages.get(code, "Error de servicio")


def create_server(settings: Settings, pipeline: Pipeline, *, log_stream=None) -> PrivacyGuardHTTPServer:
    server = PrivacyGuardHTTPServer(
        (settings.host, settings.port),
        PrivacyGuardHandler,
        settings=settings,
        pipeline=pipeline,
        log_stream=log_stream,
    )
    if settings.host not in {"127.0.0.1", "localhost", "::1"}:
        if not settings.tls_cert or not settings.tls_key:
            server.server_close()
            raise ValueError("tls_required_for_non_loopback")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(settings.tls_cert, settings.tls_key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    return server
