# Supuestos pendientes de revisión de P0

Este documento separa los supuestos de implementación de las decisiones que
deben confirmar JJO, el DPO o el responsable del servidor LLM.

| Id | Supuesto o punto abierto | Responsable | Estado |
|---|---|---|---|
| D-3 | AICrew envía texto extraído, no el fichero. | JJO | Pendiente |
| D-4 | Un `REVIEW` sin resolver no bloquea; se aplica una acción provisional conservadora y se avisa en el dossier. | JJO/DPO | Pendiente |
| D-5 | `ORGANIZATION`, `EDUCATION` y `DATE_RANGE` se conservan en `cv_scoring@1.0`. | DPO | Pendiente |
| D-14 | La integración de AICrew renumera PA-5 como PA-7. | JJO | Pendiente |
| D-15 | Excluir números precedidos por `ISO`, `UNE`, `EN` o `IEC` de la detección de código postal, modificando también la verificación de AICrew. | JJO/DPO | Propuesta |
| LLM-1 | El servidor acepta `chat_template_kwargs.enable_thinking=false`. | Responsable LLM | Pendiente |
| LLM-2 | El servidor registra o no el contenido de prompts y su plazo de retención. | Responsable LLM/DPO | Pendiente |
| LLM-3 | La CA interna necesaria para validar TLS estará disponible fuera del repositorio. | Sistemas | Pendiente |
| DATA-1 | La fuente INE y su licencia permiten distribuir la tabla municipio → provincia como dato versionado. | JJO/Sistemas | Pendiente |

La verificación de conectividad del LLM se ejecutará con
`scripts/check_llm.py` cuando estén disponibles la clave y la CA fuera del
repositorio. Hasta entonces no se declara verificado el endpoint.
