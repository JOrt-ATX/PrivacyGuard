# Verificación del LLM interno

Esta verificación de P0 comprueba, usando únicamente texto sintético:

- conectividad TLS y validación del certificado;
- presencia de `qwen3.6-27b` en `/v1/models`;
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
`PRIVACYGUARD_LLM_MODEL` y `PRIVACYGUARD_LLM_CA_FILE`. La verificación TLS no
se puede desactivar. Para pruebas locales se admite HTTP únicamente en
`localhost`, `127.0.0.1` o `::1`.

## Resultado pendiente

Debe ejecutarse contra el servidor interno y completar esta tabla sin copiar
respuestas del modelo:

| Comprobación | Resultado | Fecha | Responsable |
|---|---|---|---|
| TLS / CA | Pendiente | — | — |
| Modelo listado | Pendiente | — | — |
| Parámetros de generación | Pendiente | — | — |
| *Thinking* desactivado | Pendiente | — | — |
| Latencia (~6.000 caracteres) | Pendiente | — | — |
| Repetibilidad (10 llamadas) | Pendiente | — | — |

