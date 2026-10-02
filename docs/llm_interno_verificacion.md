# Verificación del LLM interno

Esta verificación de P0 comprueba, usando únicamente texto sintético:

- conectividad TLS y validación del certificado;
- presencia de `qwen3.8-27b` en `/v1/models`;
- aceptación de `temperature=0`, `seed` y `response_format` con `json_schema`;
- desactivación del modo *thinking*;
- latencia de una petición de aproximadamente 6.000 caracteres;
- repetibilidad de diez peticiones idénticas.

La herramienta no persiste peticiones ni respuestas y no imprime el contenido
devuelto por el modelo. La clave se obtiene de
`PRIVACYGUARD_LLM_API_KEY`; no se debe escribir en el repositorio.

## Ejecución

Desde la raíz del repositorio:

```text
set PRIVACYGUARD_LLM_API_KEY=<clave proporcionada fuera del repositorio>
python scripts/check_llm.py --ca-file C:\ruta\ca-interna.pem
```

También se pueden configurar `PRIVACYGUARD_LLM_BASE_URL`,
`PRIVACYGUARD_LLM_MODEL` y `PRIVACYGUARD_LLM_CA_FILE`. La verificación TLS solo
se puede omitir con `--insecure-skip-tls-verify`, **excepción temporal** (solo
texto sintético) descrita en PLAN.md, "Excepción temporal TLS". Para pruebas locales se admite HTTP únicamente en
`localhost`, `127.0.0.1` o `::1`.

## Resultados

Tabla completada sin copiar respuestas del modelo. Ejecución del 2026-10-02 con
`--insecure-skip-tls-verify` (excepción temporal) y texto sintético, modelo
`qwen3.8-27b`:

| Comprobación | Resultado | Fecha | Responsable |
|---|---|---|---|
| TLS / CA | Sigue sin validar (falta la CA). Verificación omitida solo mediante la excepción temporal; **pendiente de cerrar**. Antes: bloqueado: ni las CA del sistema ni el bundle Certifi proporcionado validan el certificado del endpoint (`unable to get local issuer certificate`); falta la CA interna. No se desactivó la verificación. | 2026-09-29 | Sistemas |
| Modelo listado | OK, con cambio: `qwen3.6-27b` ya no se publica. `/v1/models` lista `qwen3.8-27b`, `qwen3.8-27b-int4`, `qwen3-reranker-0.6b`, `qwen3-embedding-0.6b` y dos ids genéricos. JJO aprueba pasar a `qwen3.8-27b`. | 2026-10-02 | JJO |
| Parámetros de generación | OK: se aceptan `temperature=0`, `seed` y `response_format` json_schema (strict). | 2026-10-02 | Servicio |
| *Thinking* desactivado | OK: `chat_template_kwargs: {"enable_thinking": false}` aceptado. | 2026-10-02 | Servicio |
| Latencia (~6.000 caracteres) | Media 434 ms (mín. 432, máx. 437), 10 llamadas. | 2026-10-02 | Servicio |
| Repetibilidad (10 llamadas) | Contenido idéntico en las 10 (solo cambia `id`). Medido con texto sintético que no produce entidades; falta repetir con texto con entidades (P3/P4). | 2026-10-02 | Servicio |

Tercer intento (2026-09-30): mismo error. Inspección del certificado público
del endpoint (sin enviar datos): sujeto `CN=ai-gateway.local, O=ATEXIS,
OU=AI Platform`; **emisor `CN=AISM Internal CA, O=ATEXIS, OU=AI Platform`**;
no es autofirmado; válido del 2026-05-21 al 2028-08-23; el SAN incluye
`IP:172.21.28.81`, por lo que la comprobación de nombre funcionará sobre la IP
en cuanto se disponga de la CA. **Petición a Sistemas:** certificado raíz (y,
si existen, intermedios) de "AISM Internal CA" en formato PEM.

Los intentos se detuvieron en la validación TLS, antes de consultar
`/v1/models` o enviar texto sintético al modelo. El segundo intento usó el
bundle Certifi instalado en el entorno local y falló porque no contiene el
emisor del certificado del endpoint. Reanudar cuando Sistemas proporcione la
CA interna en formato PEM, configurándola mediante `--ca-file` o
`PRIVACYGUARD_LLM_CA_FILE`. No usar `CERT_NONE` ni otro modo que omita la
verificación del certificado.

## Hallazgo: el servidor devuelve el prompt

Las respuestas de `/chat/completions` incluyen los campos `prompt_text` y
`prompt_token_ids` (eco del texto enviado), además de `kv_transfer_params`,
`prompt_logprobs` y `system_fingerprint`. Con texto real, el contenido
viajaría también en la respuesta. El cliente de P3 debe descartar esos campos
sin registrarlos y conviene preguntar al administrador si se pueden desactivar
(relacionado con D-16 / RC-12).
