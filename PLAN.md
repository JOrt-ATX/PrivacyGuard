# ATX PrivacyGuard — Plan de trabajo por fases

Estimaciones para un desarrollador con asistencia de IA, dedicación parcial.
**Cada fase termina en una puerta de aprobación: no iniciar la siguiente sin
revisión de JJO.** Requisitos: `docs/ATX_PrivacyGuard_Requisitos_v1.0.md`
(§18 define las fases originales; este plan las adapta al uso de un LLM
interno en lugar de un modelo NER embebido).

**Alcance autorizado ahora: P0 + P1.** P2 en adelante quedan descritas para
dar contexto, pero no se inician sin nueva autorización.

---

## Cómo arrancar en un chat nuevo

1. Leer `CLAUDE.md` (restricciones) y este `PLAN.md` completo, incluida la
   sección "Contexto y decisiones de partida".
2. Leer los requisitos v1.0 (§3, §5, §6, §8, §12, §15 y §21 como mínimo).
3. Comprobar que la suite está verde:
   `python -m unittest discover -s tests -t .` (34 tests de referencia al
   25/09/2026).
4. Empezar por la primera casilla sin marcar de la fase en curso.
5. Al terminar una fase: actualizar casillas, redactar
   `docs/P<n>_supuestos_pendientes_revision.md` y **parar** en la puerta.

---

## Contexto y decisiones de partida (25/09/2026)

### Decisiones confirmadas por JJO

| Id | Decisión |
|---|---|
| D-1 | **Aprobada.** Proyecto y servicio independientes de AICrew. |
| D-2 | **Aprobada.** El Servicio sustituye a E2 **y** E3; AICrew le envía el CV sin minimizar. |
| Stack | Python, **solo stdlib** (sin dependencias). |
| IA | **No hay modelo NER embebido.** La detección contextual la hace un **LLM generativo interno, OpenAI-compatible**; el Servicio solo necesita configurar URL y API key. |
| Salida | El Servicio devuelve **texto plano minimizado + hallazgos**. No estructura el CV: eso lo hace AICrew. |
| Git | Repositorio local; sin remoto por ahora. |

### Decisiones técnicas asumidas (a registrar como supuestos en P0)

| Id | Supuesto |
|---|---|
| D-3 | AICrew envía **texto extraído** (no el fichero). |
| D-4 | `REVIEW` sin resolver **no bloquea**: acción provisional conservadora + aviso visible en el dossier (§12.2). |
| D-14 | PA-5 de AICrew se renumera a **PA-7**. |

D-5 a D-13 siguen abiertas (DPO / Jurídica / JJO) y **no bloquean P0 ni P1**.

### Datos del LLM interno

| Parámetro | Valor |
|---|---|
| URL base | `https://172.21.28.81/v1` |
| Modelo | `qwen3.6-27b` |
| API | OpenAI-compatible (`/v1/chat/completions`, `/v1/models`) |
| Soporta | `temperature=0`, `seed`, `response_format` (json_schema), según JJO |
| API key | Variable de entorno `PRIVACYGUARD_LLM_API_KEY` (no está en el repositorio; pedírsela a JJO cuando haga falta, nunca escribirla en ficheros versionados) |
| Pendiente de verificar (P0) | Certificado TLS (probablemente CA interna o autofirmado sobre IP: configurar `llm_ca_file`, **nunca** desactivar la verificación); cómo desactivar el modo *thinking* de Qwen3 (`chat_template_kwargs: {"enable_thinking": false}` o `/no_think`); si el servidor LLM registra el contenido de los prompts y durante cuánto tiempo. |

### Otros valores provisionales

- Puerto por defecto del Servicio: **8090** (AICrew usa 8080).
- Python local: 3.11.4 (el código debe funcionar en 3.11 y 3.12).
- Paquete: `privacyguard` (nombre provisional, D-13).

### Consecuencias del cambio NER → LLM sobre los requisitos v1.0

A reflejar en la v1.1 (tarea de P0):

| Requisito v1.0 | Cambio |
|---|---|
| §1.1 "ningún dato sin neutralizar llega a un modelo generativo" | Deja de ser cierto. El LLM interno recibe el CV **después** de que las reglas hayan sustituido los identificadores estructurados (email, teléfono, DNI, IBAN...), y solo devuelve una lista de entidades: **nunca reescribe el texto** (a diferencia de `anon_layer2.py`, que regenera el CV y puede alterar la evidencia). Debe constar así en la DPIA (RC-5). |
| RF-4 (clasificación de tokens) | Detección contextual por LLM con salida JSON validada; offsets calculados por el Servicio. |
| RF-8 ("sin llamar a ningún modelo generativo") | Se mantiene: `GENERALIZE` usa solo tablas. |
| RNF-2 (byte a byte idéntico) | Garantizado para reglas, fusión, política y render. Para el LLM: temperature=0 + seed + json_schema; la reproducibilidad total la da `minimization_cache` en AICrew. Medir la variabilidad real en P3. |
| RNF-3 / RS-6 (cero salidas) | "Cero salidas **salvo** el endpoint LLM configurado". El test de red cortada pasa a comprobar que no hay otras. |
| RNF-5 / RNF-8 / RNF-13 (latencia, concurrencia, lote) | Dependen del servidor LLM compartido. p95 ≤ 3 s probablemente no es realista con un modelo de 27B: medir en P3 y reabrir D-7. |
| RNF-6 / RNF-12 (memoria del modelo, hash del artefacto) | Se sustituyen por: al arrancar, `/v1/models` debe listar el modelo configurado (si no, `health = degraded` y `503`). En `versions`: `llm_model`, `llm_endpoint_id` (hash de la URL, no la URL) y `prompt_version` en lugar de `model_sha256`. |
| §14.2 / RA-1 (ficha técnica del modelo) | Ficha del LLM usado: proveedor, licencia y versión de Qwen, y dónde se ejecuta. |
| §18 P3/P4 (modelo preentrenado / entrenamiento) | V0 = LLM con prompt v1. P4 = mejora de prompts y few-shot con corpus sintético; **sin fine-tuning**. |

### Hallazgo al revisar la capa 1 (requiere decisión)

`anon_layer1.py` sustituye como código postal cualquier número de 5 dígitos
entre 01000 y 52999. **Consecuencia comprobada:** "ISO 14001", "ISO 45001" e
"ISO 27001" se convierten en `ISO [CODIGO_POSTAL_n]`. Esas normas son
evidencia central en CVs de calidad, medio ambiente y seguridad, que son los
perfiles que evalúa AICrew.

Esto choca con el criterio 0 ("100 % de conformidad con la capa 1") y con
RF-14: si el Servicio conserva "ISO 14001", la verificación independiente de
AICrew lo marcará como fuga y bloqueará el CV.

**Propuesta a decidir en la puerta de P0 (nueva decisión D-15):** el Servicio
**no** trata como código postal un número precedido por `ISO`, `UNE`, `EN`,
`IEC` o similares (lista versionada), y **AICrew aplica la misma excepción en
`anon_layer1.py` y en el verificador RF-14**. El criterio 0 se redefine como
"100 % de los casos de la batería de capa 1 **salvo** las excepciones
aprobadas y listadas". Mientras no se decida, los tests de conformidad marcan
estos casos como pendientes de decisión, no como éxito.

---

## P0 — Decisiones y contrato (≈1 semana)

- [x] Estructura inicial: `CLAUDE.md`, `PLAN.md`, `.gitignore`, `docs/`,
      `reference/aicrew/` (copia de `anon_layer1.py` con hashes),
      `tests/conformance/test_aicrew_layer1_reference.py` (34 tests, verdes).
- [x] `git init` en local (sin commits todavía).
- [ ] Primer commit con la estructura inicial (cuando JJO lo pida).
- [ ] **Verificar el LLM interno** con un script de prueba en
      `scripts/check_llm.py` (stdlib; solo texto sintético, nunca un CV real):
      conectividad TLS y CA necesaria, `/v1/models` lista `qwen3.6-27b`,
      aceptación de `seed`, `temperature=0` y `response_format` json_schema,
      desactivación del *thinking*, latencia de una llamada tipo con ~6.000
      caracteres, y repetibilidad (10 llamadas idénticas → ¿misma salida?).
      Documentar en `docs/llm_interno_verificacion.md`.
- [ ] Preguntar al responsable del servidor LLM (vía JJO) si registra el
      contenido de los prompts y con qué retención. Es un tratamiento de datos
      personales que debe constar en RC-5 y en la DPIA.
- [ ] Redactar `docs/ATX_PrivacyGuard_Requisitos_v1.1.md` con los cambios de
      la tabla "Consecuencias del cambio NER → LLM", D-1/D-2 aprobadas,
      D-3/D-4/D-14 como supuestos, y la propuesta D-15 (normas ISO). Marcar
      los cambios para revisión del DPO. La v1.0 no se edita.
- [x] **Congelar el contrato `/v1`** (§6) en `docs/contrato_v1.md` + esquemas
      en `privacyguard/schemas.py` (validadores stdlib): petición y respuesta
      de `POST /v1/minimize`; `health`, `version`, `policies`, `placeholders`;
      cuerpos de error. Con `versions` adaptado al LLM (`llm_model`,
      `prompt_version`, `llm_endpoint_id`).
- [x] **Taxonomía de etiquetas v1** (`data/labels/1.0.json`): etiquetas de
      reglas (EMAIL, PHONE, DNI_NIE, NIF_JURIDICA, PASSPORT, IBAN, URL,
      SOCIAL_PROFILE, NSS, POSTAL_CODE, DATE_FULL) y de LLM (PERSON_NAME,
      GENDER_MARKER, ART9_*, THIRD_PARTY, ORGANIZATION, LOCATION_*,
      EDUCATION, DATE_RANGE), cada una con riesgo y categoría RGPD de
      `anonymization_log` (§6.1).
- [x] **Catálogo de marcas `placeholders@1.0`** (`data/placeholders/1.0.json`):
      conservar los prefijos de capa 1 (`EMAIL`, `TELEFONO`, `DNI_NIE`,
      `IBAN`, `URL`, `CODIGO_POSTAL`, `FECHA_ABSOLUTA`, RM-3) y definir los
      nuevos (`PERSONA`, `TERCERO`, `DATO_SENSIBLE`...). Todas con índice
      `[TIPO_n]` (RM-2).
- [x] **Política `cv_scoring@1.0`** (`data/policies/cv_scoring/1.0.json`):
      matriz etiqueta → acción, umbrales por etiqueta y acción provisional de
      `REVIEW`. KEEP para organización, formación y rangos de fechas (D-5,
      pendiente del DPO, se marca como supuesto).
- [x] Tabla de generalización `municipio → provincia` v1.0: definir la
      fuente (dato público de INE, anotar la licencia) y el formato.
- [x] `config/privacyguard.example.toml`: `host`, `port=8090`, `tls_cert`,
      `tls_key`, `consumer_tokens` (hash SHA-256 + nombre del Consumidor),
      `llm_base_url`, `llm_model`, `llm_ca_file`, `llm_timeout_s`, `llm_seed`,
      `max_concurrency`, `max_text_bytes`, `diagnostic_mode=false`.
- [x] `docs/P0_supuestos_pendientes_revision.md`.

**Salida:** contrato, taxonomía, catálogo y política congelados como datos
versionados; LLM interno verificado; requisitos v1.1 redactados.

**Puerta P0:** JJO revisa el contrato, el catálogo de marcas (tiene impacto en
los prompts de juicio de AICrew, RM-5), la política y D-15.

---

## P1 — Servicio sin LLM (≈2 semanas)

Objetivo: el Servicio completo con el contrato real, con solo reglas
deterministas. Equivale a la capa 1 actual expuesta como servicio. La
detección contextual queda como una interfaz sin implementar.

- [x] `normalize.py` (TDD): normalización (NFC, espacios no separables,
      guiones partidos por maquetado, espacios en emails partidos) con **mapa
      de offsets** normalizado → original. Test de ida y vuelta (RF-2).
- [x] `rules.py` (TDD): detectores de RF-3 que devuelven spans (inicio, fin,
      etiqueta, regla), sin sustituir texto. Mínimo: todo lo de capa 1.
      Ampliaciones: pasaporte, NIF de persona jurídica (distinguirlo del
      DNI), IBAN no español, perfiles sociales sin esquema, número de la
      Seguridad Social. Excepción de normas ISO/UNE según D-15.
- [x] `tests/conformance/test_layer1_conformance.py` — **criterio 0**: por
      cada caso de la batería de capa 1, el Servicio no deja pasar ningún
      valor que la capa 1 elimina y conserva lo que la capa 1 conserva
      (rangos mes/año, años sueltos, texto sin datos personales). Además,
      re-ejecutar `reference.aicrew.anon_layer1.anonymize_layer1()` sobre el
      `sanitized_text` debe dar **cero eliminaciones** (simulacro de RF-14).
- [x] `merge.py` (TDD): fusión y deduplicación con la precedencia de RF-5
      (span más largo → regla sobre modelo → mayor riesgo → orden
      alfabético).
- [x] `policy.py` (TDD, puro): carga de política versionada, acción por
      hallazgo, `REVIEW` con acción provisional conservadora que nunca
      degrada a `KEEP` (RH-2), `policy_override` acotado (RF-19, Could).
- [x] `placeholders.py` + `render.py` (TDD): índice estable por entidad (la
      misma entidad normalizada lleva el mismo índice en todo el documento,
      RF-7), marcas sin información de longitud (RM-4), `GENERALIZE` por
      tabla (RF-8), `sanitized_text` construido sobre el texto original.
- [x] `pipeline.py`: orquestación con la etapa LLM como interfaz
      `ContextualDetector` con implementación nula en P1. **En P1 la
      respuesta se marca con `versions.llm_model = null`**, para que nadie
      confunda la salida con una minimización completa.
- [x] `config.py`: carga TOML + variables de entorno, validación al arrancar,
      error claro si falta configuración obligatoria.
- [x] `server.py`: `ThreadingHTTPServer`; token validado **antes** de leer el
      cuerpo (RS-9); límites (RNF-9: texto ≤ 200 KB, cuerpo ≤ 1 MB → `413`);
      semáforo de concurrencia → `429` (RNF-8); `503` mientras arranca
      (RNF-7); códigos y cuerpos de error de §6.1 **sin fragmentos de
      texto**; cabeceras restrictivas, sin CORS (RS-7); escucha en
      `127.0.0.1` por defecto y TLS obligatorio fuera de loopback (RS-1,
      RS-2).
- [x] Endpoints `GET /v1/health`, `/v1/version`, `/v1/policies`,
      `/v1/policies/{id}`, `/v1/placeholders` (RF-15, RF-16); `mode: dry_run`
      (RF-17); `409 POLICY_VERSION_UNAVAILABLE` (RF-13).
- [x] `logs.py`: una línea JSON por petición solo con contadores (RC-2,
      RO-1). Test que provoca una excepción y comprueba que el texto no
      aparece ni en la traza ni en el log (RNF-14).
- [x] Tests de propiedad del contrato: determinismo (20 ejecuciones →
      respuesta idéntica salvo `timing_ms`/`request_id`, RNF-2), sin estado
      (N peticiones → ningún fichero escrito fuera de `logs/`, RNF-1),
      ausencia del valor literal en toda la respuesta (RF-12).
- [x] `run.py`: arranque único (`python run.py --config config/privacyguard.toml`).
- [x] `docs/P1_supuestos_pendientes_revision.md`.

**Salida:** Servicio funcional por HTTP con reglas, política y contrato
completos; criterio 0 superado (con las excepciones de D-15); suite verde.

**Puerta P1:** JJO revisa la suite de conformidad y prueba el Servicio con
`curl` y texto sintético.

---

## Fases siguientes (no autorizadas todavía)

| Fase | Contenido | Estimación |
|---|---|---|
| **P2 — Integración temprana con AICrew** | En el repositorio de AICrew: CA-1 a CA-10 y CA-17 (cliente, config `anon_mode`, migración 0006, verificación RF-14, estado por CV). AICrew llama al Servicio en `anon_mode = serie`. | 1,5 semanas |
| **P3 — V0 con LLM** | `llm/client.py` (urllib, TLS verificado, timeout, reintentos solo ante 429/503, máx. 2) y `llm/detect.py`: prompt v1 que recibe el texto **ya procesado por las reglas** y devuelve JSON `[{text, label, confidence}]`; localización determinista de cada entidad en el original (todas las apariciones, tolerante a mayúsculas, tildes y espacios; propagación de variantes de nombre e iniciales); entidad que no se puede localizar → contador + `REVIEW` sin offsets, a decidir; fail-closed si el LLM falla. Medición completa con §15 y §11 frente a capa 1 + capa 2 de AICrew, y medición de latencia y repetibilidad reales. | 1–2 semanas |
| **Puerta de decisión** | Si V0 cumple §15 → el proyecto puede terminar aquí. | — |
| **P4 — Corpus sintético y ajuste de prompts** | Corpus sintético con nombres de todos los estratos de RE-1; iteración de prompts y few-shot (cada cambio = nueva versión de prompt). Sin fine-tuning. | 2–3 semanas |
| **P5 — Calibración, marcas y HIL** | Umbrales, presupuesto de revisión RH-6, catálogo de marcas definitivo, CA-11 a CA-13 en AICrew. | 2 semanas |
| **P6 — Validación** | Determinismo, test de red cortada (solo LLM permitido), lote de 20 CVs, red-team, regresión completa. | 2 semanas |
| **P7 — Piloto y conmutación** | Piloto en `serie`, decisión de pasar a `privacyguard` (CA-16). | 2 semanas |

---

## Riesgos específicos del cambio a LLM

| # | Riesgo | Mitigación |
|---|---|---|
| RL-1 | El LLM devuelve entidades que no aparecen literalmente en el texto, o no devuelve variantes (iniciales, apellido suelto) → fuga. | Localización tolerante + propagación determinista de variantes; verificación RF-14 en AICrew; red-team en P6. |
| RL-2 | Latencia del LLM de 27B incompatible con RNF-5 / RNF-13. | Medir en P0 y P3; enviar solo el texto necesario; reabrir D-7 con datos. |
| RL-3 | El servidor LLM registra los prompts → segundo sistema con CVs completos (contra §2.3). | Verificación en P0; hacerlo constar en la DPIA; enviar al LLM solo el texto ya procesado por las reglas. |
| RL-4 | No determinismo del LLM pese a temperature=0 y seed. | Medir la repetibilidad en P0/P3; la caché versionada de AICrew (RV-2) fija el resultado por CV. |
| RL-5 | Cambio silencioso del modelo en el servidor LLM (misma etiqueta, pesos distintos). | Declarar `llm_model` en cada respuesta; comprobar `/v1/models` al arrancar y en `health`; acordar con el administrador el aviso de cambios. |
| RL-6 | Inyección de instrucciones dentro del CV ("ignora las instrucciones y..."). | El LLM solo produce una lista validada por esquema; nunca texto de salida; casos de red-team específicos. |
