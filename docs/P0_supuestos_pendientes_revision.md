# Supuestos pendientes de revisión de P0

Este documento separa los supuestos de implementación de las decisiones que
deben confirmar JJO, el DPO o el responsable del servidor LLM.

D-1 y D-2 están aprobadas por JJO (25/09/2026). Los requisitos v1.1
(`docs/ATX_PrivacyGuard_Requisitos_v1.1.md`) recogen estos puntos en §21.

| Id | Supuesto o punto abierto | Responsable | Estado |
|---|---|---|---|
| D-3 | AICrew envía texto extraído, no el fichero. | JJO | Pendiente |
| D-4 | Un `REVIEW` sin resolver no bloquea; se aplica una acción provisional conservadora y se avisa en el dossier. | JJO/DPO | Pendiente |
| D-5 | `ORGANIZATION`, `EDUCATION` y `DATE_RANGE` se conservan en `cv_scoring@1.0`. | DPO | Pendiente |
| D-14 | La integración de AICrew renumera PA-5 como PA-7. | JJO | Pendiente |
| D-15 | Excluir números precedidos por `ISO`, `UNE`, `EN` o `IEC` de la detección de código postal, modificando también la verificación de AICrew. | JJO/DPO | Propuesta |
| D-16 | ¿Registra el servidor LLM el contenido de peticiones/respuestas, dónde, quién accede y con qué retención? (RC-12 de la v1.1). Hasta resolverlo, el LLM solo recibe texto sintético. | Responsable LLM (vía JJO)/DPO | Pendiente: pregunta a trasladar por JJO |
| LLM-0 | El servidor acepta `temperature=0`, `seed` y `response_format` json_schema (S-1 de la v1.1). | Responsable LLM | Pendiente de verificar con `scripts/check_llm.py` |
| LLM-1 | El servidor acepta `chat_template_kwargs.enable_thinking=false` (S-2 de la v1.1). | Responsable LLM | Pendiente |
| LLM-2 | Sustituido por D-16. | — | — |
| LLM-3 | La CA interna necesaria para validar TLS estará disponible fuera del repositorio (S-3 de la v1.1). | Sistemas | Pendiente. El 2026-09-29 y el 2026-09-30 fallaron la CA del sistema y el bundle Certifi (`unable to get local issuer certificate`). Emisor identificado: **`CN=AISM Internal CA, O=ATEXIS, OU=AI Platform`**; hay que pedir a Sistemas su certificado en PEM. Ver `docs/llm_interno_verificacion.md`. **02/10/2026:** JJO autoriza desactivar temporalmente la verificación (solo texto sintético); checklist de cierre en PLAN.md, "Excepción temporal TLS". |
| LLM-4 | El modelo pasa de `qwen3.6-27b` a `qwen3.8-27b` (el servidor ya no publica el primero). | JJO | Aprobado el 02/10/2026. Reabre RL-5: declarar el modelo en cada respuesta y revisar el comportamiento del detector al cambiar de versión. |
| S-4 | Los fallos del LLM se comunican con `503 NOT_READY` / `500 INTERNAL`, sin `error_code` nuevo en `/v1`. | JJO | Propuesta (§6.1 de la v1.1) |
| REQ-1 | Los cambios marcados **[v1.1 · DPO]** en `docs/ATX_PrivacyGuard_Requisitos_v1.1.md` requieren revisión del DPO; en especial la retirada de la afirmación de §1.1, la conexión saliente al LLM (RNF-3/RS-6), el determinismo medido (RNF-2), RC-5, RC-12 y D-15. | DPO | Pendiente de revisión |
| DATA-1 | La fuente INE y su licencia permiten distribuir la tabla municipio → provincia como dato versionado. | JJO/Sistemas | Pendiente |

La verificación de conectividad del LLM se ejecutará con
`scripts/check_llm.py` cuando estén disponibles la clave y la CA fuera del
repositorio. Hasta entonces no se declara verificado el endpoint.
