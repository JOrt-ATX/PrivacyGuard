# Supuestos pendientes de revisión de P1

| Id | Supuesto o punto abierto | Responsable | Estado |
|---|---|---|---|
| P1-1 | La implementación P1 no ejecuta detección contextual; `llm_model` permanece `null` y la integración LLM queda para P3. | JJO | Aplicado |
| P1-2 | La excepción D-15 para normas `ISO`, `UNE`, `EN` e `IEC` permanece desactivada por defecto hasta aprobación. | JJO/DPO | Pendiente |
| P1-3 | La política `cv_scoring@1.0` conserva organización, formación y rangos de fechas según D-5 provisional. | DPO | Pendiente |
| P1-4 | La tabla municipio → provincia es solo esquema hasta confirmar fuente, licencia y datos publicables del INE. | JJO/Sistemas | Pendiente |
| P1-5 | El arranque requiere una configuración local fuera del repositorio; `config/privacyguard.example.toml` no es una configuración operativa porque no contiene secretos. | Sistemas | Aplicado |

La suite de conformidad utiliza únicamente texto sintético y reejecuta la
capa de referencia sobre el texto minimizado para comprobar que no quedan
identificadores estructurados.
