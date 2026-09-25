# Contrato HTTP `/v1`

El contrato es explícito y versionado: los cambios incompatibles usan `/v2/`.
Todas las respuestas son JSON UTF-8. El Servicio nunca incluye el texto
literal de un hallazgo ni fragmentos del documento en respuestas de error.

## `POST /v1/minimize`

La petición contiene `request_id`, `document_ref`, `text` y `policy_id`.
Admite `language_hint`, `policy_version`, `mode` (`enforce` o `dry_run`) y un
`policy_override` con forma `{"LABEL": "KEEP|GENERALIZE|REDACT|REVIEW"}`.
`text` es UTF-8 y no supera 200 KiB. El token de Consumidor se valida antes de
leer el cuerpo.

La respuesta `200` contiene:

```json
{
  "request_id": "opaque-id",
  "status": "OK",
  "sanitized_text": "[EMAIL_1]",
  "detections": [
    {
      "index": 0, "label": "EMAIL", "start": 0, "end": 16,
      "action": "REDACT", "placeholder": "[EMAIL_1]",
      "confidence": 1.0, "risk": "HIGH", "source": "RULE",
      "reason": "STRUCTURED_IDENTIFIER"
    }
  ],
  "review_items": [],
  "stats": {
    "detections_total": 1,
    "by_action": {"KEEP": 0, "GENERALIZE": 0, "REDACT": 1, "REVIEW": 0},
    "by_category_rgpd": {"dato_contacto": 1}
  },
  "versions": {
    "service": "1.0.0", "rules": "1.0", "policy": "cv_scoring@1.0",
    "preprocessing": "1.0", "placeholders": "1.0",
    "llm_model": null, "prompt_version": null, "llm_endpoint_id": null
  },
  "timing_ms": 0
}
```

`start` y `end` son offsets sobre el texto original recibido. `review_items`
solo contiene offsets, etiqueta candidata, confianza, motivo,
`provisional_action` y opciones de resolución; nunca contiene el span literal.
`status` es `REVIEW_REQUIRED` si existe al menos un `review_item`. En `dry_run`
`sanitized_text` es `null`.

## Endpoints de consulta

- `GET /v1/health`: `{status, versions, model_loaded?, uptime_s?}`, donde
  `status` es `ok`, `degraded` o `loading`.
- `GET /v1/version`: `{versions}`.
- `GET /v1/policies`: `{version, policies}`.
- `GET /v1/policies/{id}`: detalle de una política y su matriz de acciones.
- `GET /v1/placeholders`: `{version, placeholders}`.

`versions` siempre declara `service`, `rules`, `policy`, `preprocessing`,
`placeholders`, `llm_model`, `prompt_version` y `llm_endpoint_id`. El endpoint
LLM se identifica mediante un identificador estable, nunca mediante su URL.

## Errores

Todos tienen forma `{error_code, message, request_id}` y no contienen datos
del documento:

| HTTP | Código |
|---:|---|
| 400 | `INVALID_REQUEST` |
| 409 | `POLICY_VERSION_UNAVAILABLE` |
| 413 | `TEXT_TOO_LARGE` |
| 422 | `UNPROCESSABLE_TEXT` |
| 429 | `BUSY` |
| 503 | `NOT_READY` |
| 500 | `INTERNAL` |
