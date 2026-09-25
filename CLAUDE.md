# ATX PrivacyGuard — Convenciones del proyecto

Servicio HTTP interno de ATEXIS que **recibe el texto completo de un CV y lo
devuelve con los datos personales sustituidos por marcas neutras**, más la
lista de hallazgos. El Servicio **no estructura el CV** (no extrae
experiencia, formación, etc.): devuelve texto plano minimizado y AICrew se
ocupa de estructurarlo y evaluarlo. Sustituye a las capas E2 (regex) y E3
(LLM) de AICrew.

Documentos de referencia:
- Requisitos: `docs/ATX_PrivacyGuard_Requisitos_v1.0.md` (RF-*, RNF-*, RS-*,
  RC-*, RH-*, RM-*, §15 criterios, §21 decisiones D-*). La v1.1 se redacta en P0.
- Plan de trabajo: `PLAN.md`.
- Plan técnico del detector (taxonomía, métricas, red-team; las partes de
  entrenamiento NER quedan superadas por el uso de LLM):
  `C:\AI\AICrew\docs\CV-Privacy-Detector_Plan-Desarrollo_v1.md`.
- Consumidor de referencia: repositorio AICrew en `C:\AI\AICrew`
  (`CLAUDE.md`, `PLAN.md`, `app/core/pipeline.py`).

## Restricciones innegociables

1. **Stdlib de Python únicamente.** Sin dependencias externas: nada de
   FastAPI, Flask, requests, httpx, pydantic, torch, onnxruntime.
   Servidor: `http.server.ThreadingHTTPServer` + `ssl`. HTTP saliente:
   `urllib.request`. Config: `tomllib`. Código compatible con Python 3.11+
   (entorno local: 3.11.4; despliegue previsto: runtime 3.12 de AICrew): no
   usar sintaxis exclusiva de 3.12. NO añadir dependencias sin aprobación de JJO.
2. **Función pura, sin estado** (§2.3): `(texto, política) → (texto
   minimizado, hallazgos)`. Nada se persiste: ni texto, ni hallazgos, ni
   peticiones, ni cachés de texto, ni colas, ni endpoints de lote. Ninguna
   excepción "para depurar".
3. **Nunca devolver ni registrar el valor literal** de un dato detectado
   (RF-12): ni en respuestas, ni en logs, ni en cuerpos de error, ni en trazas
   de excepción. Sin mapa inverso marca → valor. Logs = solo contadores y
   metadatos (RC-2). El modo diagnóstico está deshabilitado por defecto (RC-4).
4. **Orden del pipeline:** normalización → **reglas deterministas primero** →
   LLM solo sobre el texto con los identificadores estructurados ya
   sustituidos → fusión → política → render. El LLM **nunca reescribe el
   texto**: solo devuelve una lista de entidades (texto literal + etiqueta);
   los offsets y la sustitución los calcula el Servicio de forma determinista.
5. **Única conexión saliente permitida:** el endpoint LLM interno configurado
   (OpenAI-compatible, `https://172.21.28.81/v1`, modelo `qwen3.6-27b`).
   Nada de internet, telemetría ni descargas. Verificación TLS **siempre
   activa** (con CA interna configurable si hace falta, nunca
   `CERT_NONE`). API key en variable de entorno o fichero de config fuera del
   repositorio, nunca en código ni en logs.
6. **Determinismo:** temperature=0, seed fijo, `response_format` json_schema,
   thinking desactivado; reglas y fusión con desempates estables; sin
   dependencia de `hash()`, orden de dicts no controlado, reloj, locale ni
   rutas. Cada respuesta declara todas las versiones (RF-11).
7. **Fail-closed:** ante fallo del LLM, respuesta inválida del LLM o cualquier
   error interno, el Servicio responde error (`503`/`500`); **nunca** devuelve
   texto minimizado solo con reglas como si estuviera completo.
8. **Vocabulario** (§1.2, RC-6): en nombre, endpoints, respuestas, logs y
   documentación del Servicio se dice "minimización" / "seudonimización";
   nunca "anonimización" (excepto al citar nombres de AICrew como
   `anon_layer1.py` o `anonymization_log`).
9. **Seguridad de red** (§9): modo local solo en `127.0.0.1`; fuera de
   loopback, TLS obligatorio. Token por Consumidor en cabecera, validado
   **antes de leer el cuerpo**. Sin CORS, sin interfaz web.
10. **Conformidad con la capa 1 de AICrew** (criterio 0): el motor de reglas
    cubre al menos lo que cubre `reference/aicrew/anon_layer1.py`. Esa copia
    no se edita (ver `reference/aicrew/README.md`).

## Arquitectura prevista

```
privacyguard/
  server.py          # ThreadingHTTPServer, auth por token, límites, rutas /v1
  config.py          # Carga TOML + variables de entorno, validación al arrancar
  pipeline.py        # Orquestación normalize → rules → llm → merge → policy → render
  normalize.py       # Normalización con mapa de offsets al texto original (RF-2)
  rules.py           # Detectores deterministas (RF-3)
  merge.py           # Fusión y deduplicación con precedencia documentada (RF-5)
  policy.py          # Motor de política puro: etiqueta → acción (RF-6)
  placeholders.py    # Catálogo de marcas + índice estable por entidad (RF-7, §8)
  generalize.py      # Tablas versionadas (municipio → provincia) (RF-8)
  render.py          # Aplica acciones sobre el texto original
  schemas.py         # Validación de petición/respuesta y de la salida del LLM
  logs.py            # Logs de contadores JSON por línea (RO-1)
  llm/
    client.py        # Cliente OpenAI-compatible (urllib), reintentos, timeout
    detect.py        # Detección contextual: prompt → JSON → localización de spans
    prompts/v1/      # Prompts versionados; cambiar un prompt = nueva versión
data/
  policies/<id>/<ver>.json
  placeholders/<ver>.json
  generalization/<tabla>/<ver>.json
config/
  privacyguard.example.toml   # Plantilla; la real (privacyguard.toml) no se versiona
reference/aicrew/    # Copia de la capa 1 de AICrew (solo tests)
tests/               # unittest (stdlib)
  conformance/       # Criterio 0: batería de la capa 1 de AICrew
benchmarks/          # Medición §15 (corpus fuera del repo)
docs/
run.py               # Arranque único
```

Nombre del paquete `privacyguard` provisional hasta D-13.

## Reglas de trabajo

- Offsets de `detections` y `review_items` siempre referidos al **texto
  original recibido**; `sanitized_text` se construye sobre el original.
- Políticas, catálogo de marcas, tablas de generalización y prompts son
  **ficheros de datos versionados**: un cambio = nueva versión, nunca edición
  en sitio de una versión publicada.
- Tests con `unittest`: `python -m unittest discover -s tests -t .`
  `policy.py`, `merge.py`, `normalize.py` y `rules.py` se desarrollan con TDD.
  El cliente LLM se prueba con dobles; nunca con CVs reales.
- Ningún CV real en el repositorio, en tests ni en fixtures: solo texto
  sintético.
- No inventar requisitos: ante ambigüedad, preguntar a JJO. Los supuestos se
  registran en `docs/P<n>_supuestos_pendientes_revision.md`.
- Flujo con puertas de aprobación: al final de cada fase de `PLAN.md`, parar
  y pedir revisión antes de continuar.
- No hay remoto git todavía: commits solo en local y solo cuando se pidan.
