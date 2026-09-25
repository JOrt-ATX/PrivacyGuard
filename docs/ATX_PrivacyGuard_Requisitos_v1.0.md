# ATX PrivacyGuard — Requisitos para proyecto nuevo v1.0

**Versión:** 1.0 (sustituye a `docs/ATX_PrivacyGuard_Requisitos_v0.1.md`)
**Fecha:** 23 de septiembre de 2026
**Naturaleza:** documento fundacional de un **proyecto nuevo e independiente**,
separado del repositorio de AICrew (CV Scoring MVP).
**Estado:** no aprobado. Requiere decisión de JJO (§21, D-1 a D-14), validación
del DPO y de Asesoría Jurídica.

**Qué cambia respecto a la v0.1, en una frase:** la v0.1 describía un Servicio
intercalado *entre* las dos capas de anonimización de AICrew ("capa 1.5"). Esta
versión describe un Servicio que **sustituye a ambas**: recibe el CV completo
—sin anonimizar— y devuelve el texto ya minimizado, listo para evaluar.

**Documentos relacionados:**
`docs/CV-Privacy-Detector_Plan-Desarrollo_v1.md` (plan técnico del detector:
taxonomía, datasets, entrenamiento, métricas — sigue vigente y **no se duplica
aquí**); `docs/ATX_PrivacyGuard_Requisitos_v0.1.md` (versión anterior,
superada); `docs/PA-5_minimizacion_datos_llm_capa2.md` (punto abierto que
origina la propuesta, pendiente de renumerar a PA-7, D-14); `CLAUDE.md` y
`PLAN.md` de AICrew.

---

# 0. Qué cambia respecto a la v0.1

La v0.1 es correcta en su arquitectura de fondo (servicio separado, sin estado,
función pura, política versionada). Lo que cambia es **dónde se corta el
pipeline de AICrew**, y ese corte arrastra consecuencias en el contrato, en la
trazabilidad, en la caché, en el modelo de datos y en el reparto de
responsabilidades.

| # | Punto de la v0.1 | Corrección en esta versión |
|---|---|---|
| **C-1** | §3.2: "la capa 1 de AICrew se conserva y se ejecuta antes de la llamada". El Servicio era capa 1.5. | §3: el Servicio es la **única etapa de minimización**. Sustituye a E2 (`anon_layer1.py`) y a E3 (`anon_layer2.py`) en el flujo de la UI. AICrew envía el texto extraído **sin anonimizar**. |
| **C-2** | RF-3: el motor de reglas del Servicio era "duplicación deliberada, defensa en profundidad". | §5, RF-3: el motor de reglas pasa a ser **mínimo contractual**. Si el Servicio no cubre todo lo que hoy cubre `anon_layer1.py`, la sustitución es una **regresión de privacidad respecto a producción**. La batería de tests de capa 1 de AICrew se convierte en suite de conformidad del Servicio (§15, criterio 0). |
| **C-3** | RF-14: la verificación independiente esperaba "cero eliminaciones porque la capa 1 ya se aplicó antes". Era una comprobación tautológica. | §3.4: con la capa 1 fuera del camino, re-ejecutar `anonymize_layer1()` sobre el texto devuelto es una **verificación real**: cualquier hallazgo significa que el Servicio ha dejado escapar un identificador estructurado. Mismo código, cero dependencias nuevas, valor de detección muy superior. |
| **C-4** | §1.2: "reduce el volumen de PII que cruza la frontera de proceso". | §3.5 y §9: ese argumento **desaparece**. Ahora cruza la frontera el CV íntegro, con email, DNI, IBAN y datos del art. 9. Se compensa con controles explícitos (TLS obligatorio también en modo local si no es `127.0.0.1`, token por Consumidor, higiene de memoria, cuerpo de error sin fragmentos). No se disimula: es el precio de la sustitución. |
| **C-5** | No contemplaba el **proceso de reclutamiento** (F4_e) como unidad de trabajo. | §4: el proceso pasa a ser el contexto de referencia. Un proceso fija plantilla@versión **y ahora también política@versión de minimización**. Sin ese anclaje, dos CVs del mismo ranking pueden haberse minimizado con criterios distintos y **dejan de ser comparables**. |
| **C-6** | No definía el comportamiento ante **lotes** de CVs. | §7.6 y RNF-8/RNF-13: el Servicio sigue siendo por documento y sin estado (nada de colas ni endpoints de lote, que romperían la frontera de §2.3); la concurrencia y el fallo parcial se gestionan **en el Consumidor**, con presupuesto de tiempo de lote medible. |
| **C-7** | El formato de marcas neutras se daba por resuelto (`[TIPO_n]`). | §8: **catálogo de marcas versionado** y endpoint propio. Hoy conviven dos formatos incompatibles en AICrew: capa 1 emite `[EMAIL_1]` (indexado) y capa 2 emite `[NOMBRE_PROPIO]` (sin índice, ver `llm/prompts/v1/anonymization_system.md:48`). Unificarlos cambia lo que ve E4 → **exige nueva versión de prompts de juicio** e invalida la caché de evaluaciones. |
| **C-8** | CA-10: la caché de capa 2 se ampliaba con las versiones del Servicio. | §17, CA-7: `layer2_cache` no se toca (insert-only, filas históricas válidas). Se crea `minimization_cache` con clave propia. La minimización **no depende del JD**, así que se reutiliza entre procesos —pero solo si coinciden las versiones fijadas por cada proceso. |
| **C-9** | No trataba el **cambio de versión del modelo a mitad de proceso**. | §4.3: el Servicio sirve **una sola versión de modelo activa** (RNF-6 no admite dos artefactos en memoria). Si cambia con un proceso abierto, AICrew bloquea CVs nuevos en ese proceso y ofrece reevaluar o cerrar; la excepción la autoriza un administrador y queda en `config_history`. |
| **C-10** | Daba por hecho que "el Servicio no persiste nada" resolvía la retención. | §10, RC-11: cierto para el Servicio, falso para el conjunto. El **texto minimizado que AICrew guarda** es dato personal seudonimizado y hoy `db/retention.py` no lo purga (solo vacía `documents.file_bytes`). Entra en el alcance de PA-1 (D-11). |
| **C-11** | RH-3: un `review_item` sin resolver bloqueaba el documento. | §12: se propone invertir el default a **acción provisional conservadora + aviso visible en el dossier**, y se explica por qué (la cola bloqueante expone texto sin minimizar a quien después decide, y eso contamina la decisión además de crear una superficie de PII). Es un cambio de criterio, no un descuido: D-4. |
| **C-12** | §11 asignaba la revisión a "un rol autorizado de AICrew". | §12.3: se añade la **separación de funciones**. Quien resuelve la revisión no debería ser quien evalúa o decide sobre ese candidato. |
| **C-13** | Asumía que "solo el responsable ve el CV completo" ya estaba implementado. | §13.2: hoy el desenmascaramiento está restringido **por rol** (`responsable_reclutamiento`, `server.py:844`), no **por responsable asignado al proceso**. El caso de uso descrito es más estricto que lo implementado: es un cambio en AICrew (CA-13, D-10). |
| **C-14** | RC-6 prohibía la palabra "anonimización" sin resolver el conflicto con AICrew, que la usa en código, esquema y UI. | §1.2: la regla se aplica a las superficies del Servicio y a los **textos de usuario** de AICrew; los nombres internos (`anon_layer1.py`, `anonymization_log`) **no se renombran**: son auditoría insert-only y renombrarlos rompe la trazabilidad sin ganar nada. |

Se mantienen sin cambios sustantivos de la v0.1: la justificación de servicio
separado (§1.1), la frontera sin estado (§2.3), el determinismo (RNF-2), la
regla de licencias, los requisitos de equidad (§11) y el análisis de naturaleza
dual bajo el AI Act (§14.2).

---

# 1. Propósito y vocabulario

## 1.1. Propósito

Proveer a las aplicaciones internas de ATEXIS un **servicio local de detección
y minimización de datos personales en texto**, que devuelva:

1. el texto con los datos personales sustituidos por marcas neutras, y
2. la lista de hallazgos no concluyentes marcados para interpretación humana.

En el caso de AICrew, el Servicio es **la etapa de minimización completa**: el
CV se extrae, se envía íntegro al Servicio, y lo que vuelve es lo único que
entra en el pipeline de evaluación. Ningún dato personal sin neutralizar llega
a un modelo generativo, porque la llamada LLM que hoy los recibe
(`core/anon_layer2.py`) desaparece del flujo.

En el resto del documento: **el Servicio** = ATX PrivacyGuard; **el Consumidor**
= cualquier aplicación interna que lo invoque; **AICrew** = el Consumidor de
referencia.

## 1.2. Nota sobre el nombre y el vocabulario

El Servicio **no se llamará "anonimizador"** ni contendrá la palabra
"anonimización" en su nombre, endpoints, interfaz ni documentación. Lo que
produce es **seudonimización**: un CV que conserva titulación, empresas, rangos
de fechas, idiomas y provincia sigue siendo un conjunto de cuasi-identificadores
y sigue siendo dato personal bajo el RGPD. Un nombre que afirme lo contrario
crea una expectativa jurídica errónea que después se usa para justificar
tratamientos indebidos ("ya está anonimizado, se puede enviar a X").

Nombre de trabajo: **ATX PrivacyGuard**. Nombre definitivo: D-13.

**Conflicto con el vocabulario existente de AICrew, y su resolución.** AICrew
usa "anonimización" en todas partes: `CLAUDE.md` restricción 5, `anon_layer1.py`,
`anon_layer2.py`, la tabla `anonymization_log`, los textos de la UI. La regla se
aplica así:

| Superficie | Regla |
|---|---|
| Nombre, endpoints, respuestas y documentación del Servicio | Nunca "anonimización". Solo "minimización" / "seudonimización". |
| Textos de usuario de AICrew (UI, mensajes de error, informes) | Se corrigen en F5 junto con el documento de información a candidatos. Es un cambio de literales, contenido y barato. |
| Nombres de módulos, tablas y columnas de AICrew | **No se renombran.** `anonymization_log` es insert-only y su historial es auditoría; renombrar rompe la trazabilidad a cambio de nada. |

---

# 2. Alcance

## 2.1. Dentro de alcance

- Detección de datos personales y sensibles en **texto plano en español**
  (inglés en v2).
- Aplicación de una **política de minimización versionada** que decide, por
  hallazgo, entre conservar, generalizar, redactar o marcar para revisión.
- Devolución del texto minimizado y del listado de hallazgos.
- Marcado de resultados no concluyentes para interpretación humana (**HIL**).
- Ejecución 100 % local, sin ninguna salida a internet.

## 2.2. Fuera de alcance

- **Extracción de documentos** (PDF, DOCX, OCR). El Consumidor envía texto ya
  extraído (D-3). AICrew ya tiene `core/extract.py` con `pypdf` autorizado y
  error explícito ante texto vacío; duplicarlo sería un error y trasladaría al
  Servicio el problema del PDF escaneado.
- **Persistencia de nada.** Ni CV, ni texto, ni resultados, ni colas, ni lotes.
- **Interfaz de usuario.**
- **Gestión de identidades, roles o sesiones.**
- **Mapa inverso marca → valor.** El Servicio no lo produce, no lo devuelve y no
  lo conserva. El desenmascaramiento se resuelve en AICrew con el fichero
  original (§13.2), no con información del Servicio.
- **La cola de revisión humana.** El Servicio **marca**; el Consumidor
  **almacena, presenta, controla el acceso y audita**.
- **Decisiones de negocio.** El Servicio no puntúa, no compara, no clasifica
  candidatos y no conoce el concepto "candidato" ni el de "proceso".

## 2.3. La frontera que no debe cruzarse

> El Servicio es una función pura: `(texto, política) → (texto minimizado,
> hallazgos)`. Todo lo que tenga estado, identidad, auditoría persistente,
> agrupación por lote o interfaz humana vive en el Consumidor.

Cada excepción que se le conceda —una caché de texto, un histórico "para
depurar", una cola de lote, una pantalla de revisión propia— lo convierte en un
segundo sistema de tratamiento de datos personales con sus propias obligaciones
de acceso, retención y auditoría. **Se rechaza por diseño.**

---

# 3. El cambio de arquitectura: de capa 1.5 a etapa única

## 3.1. Antes y después

```
HOY (producción, core/pipeline.py:69-84)

  E1 extract.py  →  E2 anon_layer1 (regex)  →  E3 anon_layer2 (LLM)  →  E4 judge (LLM)  →  E5 compute
                         determinista            ← PII sale aquí          texto ya anonimizado


OBJETIVO (con el Servicio)

  E1 extract.py  →  ┌──────────────────────────┐  →  VERIFICACIÓN  →  E4 judge  →  E5 compute
                    │  POST /v1/minimize       │     independiente
                    │  ATX PrivacyGuard        │     (anon_layer1
                    │  reglas + NER + política │      sobre la salida
                    └──────────────────────────┘      ⇒ debe dar 0)
```

`anon_layer1.py` y `anon_layer2.py` **no se borran del repositorio de AICrew**,
cambian de función:

| Módulo | Función hoy | Función objetivo |
|---|---|---|
| `core/anon_layer1.py` | Etapa E2 del pipeline | **Verificador independiente** de la salida del Servicio (RF-14). Mismo código, cero dependencias nuevas. |
| `core/anon_layer2.py` + prompts de anonimización | Etapa E3 del pipeline | **Solo línea base de medición** en `benchmarks/`: sin medir al incumbente sobre el mismo conjunto ciego, los criterios de §15 no son criterios, son opiniones. Fuera del flujo de la UI. |

## 3.2. La transición es un interruptor, no un salto

Retirar la capa 2 el primer día dejaría a AICrew sin detección de nombres hasta
que el Servicio tenga modelo. Se define una clave de configuración
`anon_mode`, auditada en `config_history` como el resto:

| Valor | Pipeline | Cuándo |
|---|---|---|
| `legacy` | E2 capa 1 → E3 capa 2 LLM | Estado actual. **Default hasta superar §15.** |
| `serie` | E2 capa 1 → Servicio → E3 capa 2 LLM | Integración temprana (P2) y piloto. El Servicio no puede empeorar nada porque la capa 2 sigue detrás. La verificación RF-14 es aquí tautológica y solo prueba que el Servicio no reintroduce texto. |
| `privacyguard` | Servicio → verificación con `anon_layer1` | Objetivo. Requiere §15 superado y decisión explícita de JJO. |

Un solo interruptor, tres estados, y la arquitectura objetivo escrita desde el
primer día. El cambio de valor es una decisión registrada, no un despliegue
silencioso.

## 3.3. Qué se envía: texto extraído, no el fichero

**Recomendación (D-3): AICrew envía el texto extraído por `core/extract.py`.**

| | Enviar texto extraído (recomendado) | Enviar el fichero binario |
|---|---|---|
| Errores de extracción | Se detectan en AICrew, con el mensaje claro que ya existe, **antes** de que nada cruce la frontera | El Servicio hereda el problema del PDF escaneado y necesita OCR, fuera de alcance |
| Dependencias | Ninguna nueva en ninguno de los dos lados | El Servicio duplica `pypdf` y la extracción DOCX |
| Offsets | Un solo origen de coordenadas | Dos: las del fichero y las del texto |
| Superficie de ataque | Texto plano | Parseo de formatos binarios de origen externo, que es históricamente donde aparecen las vulnerabilidades |

Se reserva la posibilidad de un `POST /v1/minimize-document` en v2 para
Consumidores sin extracción propia. No entra en v1.

## 3.4. La verificación independiente pasa a ser real (RF-14)

Con la capa 1 fuera del camino de ida, AICrew re-ejecuta
`anonymize_layer1()` sobre el `sanitized_text` devuelto. El resultado esperado
sigue siendo **cero eliminaciones**, pero ahora por un motivo distinto y mucho
más valioso: significa que el Servicio ha cubierto todo lo que la capa 1
cubría.

Cualquier hallazgo ⇒ **fail-closed**: la evaluación se detiene, se registra el
incidente y el usuario ve un mensaje claro. Es una comprobación barata
(determinista, local, sin red, con tests ya escritos) que detecta la clase de
fallo más peligrosa: la que no produce error.

## 3.5. Lo que empeora con este cambio, dicho sin rodeos

La v0.1 podía argumentar que cruzaba la frontera de proceso un texto ya
despojado de email, teléfono, DNI e IBAN. **Eso ya no es cierto.** Ahora cruza
el CV íntegro. Consecuencias que deben tratarse como requisitos, no como notas:

1. El canal entre AICrew y el Servicio transporta datos personales en claro
   salvo que se cifre ⇒ RS-2 pasa a **obligatorio siempre que no sea
   `127.0.0.1`**, sin excepción de "red interna de confianza".
2. El Servicio pasa a ser un objetivo de mayor valor ⇒ RS-3, RS-4 y RS-8 dejan
   de ser higiene y pasan a ser controles de acceso a PII.
3. Un volcado de memoria o un log mal configurado del Servicio contiene CVs
   completos ⇒ RC-2 (logs sin texto) y RC-4 (modo diagnóstico deshabilitado en
   producción) pasan a ser **auditables en la puerta de despliegue**.
4. El flujo debe constar en el registro de actividades (art. 30) y en la DPIA
   describiendo lo que realmente viaja: "CV completo, sin minimizar, de AICrew
   al Servicio por la red interna" (RC-5).

---

# 4. Contexto de integración: el proceso de reclutamiento

## 4.1. El caso de uso, paso a paso

| # | Paso del caso de uso | Quién | Implementación |
|---|---|---|---|
| 1 | Se crea un proceso de selección | AICrew (reclutador/admin) | `processes` (F4_e). Fija plantilla@versión **y ahora también política@versión de minimización** (§4.2) |
| 2 | El reclutador añade los CVs recibidos | AICrew (reclutador) | Subida por CV; `candidate_id` = SHA-256 del fichero; `documents` guarda el original |
| 3 | AICrew envía cada CV al Servicio | AICrew | E1 `extract.py` → `POST /v1/minimize` con `document_ref = candidate_id` |
| 4 | El Servicio minimiza y devuelve el texto | Servicio | Normalización → reglas + NER → fusión → política. Sin estado |
| 5 | AICrew vincula el texto al CV y lo evalúa | AICrew | Verificación RF-14 → `minimization_cache` por `candidate_id` → E4 `judge.py` → E5 `compute.py` → E6 persistencia con `process_id` |
| 6 | AICrew devuelve el listado; solo el responsable ve el CV completo | AICrew | Listado del proceso; original bajo `unmask_events` (§13.2, D-10) |

El Servicio participa **solo en el paso 4** y no sabe nada de los otros cinco.
Esa ignorancia es la propiedad que hay que proteger.

## 4.2. El proceso fija también las versiones de minimización

Regla derivada directamente de CLAUDE.md ("un proceso agrupa evaluaciones
contra UNA plantilla y versión fijadas al crear el proceso" y "las comparaciones
entre versiones de plantilla distintas están bloqueadas con aviso"):

> Si dos CVs del mismo proceso se minimizan con políticas o modelos distintos,
> uno puede haber conservado evidencia que al otro se le ha redactado. El
> ranking resultante compara cosas distintas. La comparabilidad dentro del
> proceso exige fijar las versiones de minimización igual que se fija la
> plantilla.

Por tanto: `processes` guarda `privacy_policy_id` y `privacy_policy_version` al
crearse, y registra `privacy_model_version` + `privacy_model_sha256` con el
primer CV minimizado del proceso (CA-9).

## 4.3. Deriva de versiones con un proceso abierto

El Servicio sirve **una sola versión de modelo activa** (RNF-6 no admite dos
artefactos cargados). Si el modelo o la política cambian con procesos abiertos:

| Situación | Comportamiento exigido |
|---|---|
| Cambia `policy_version` y el proceso fijó otra | El Servicio **sirve la versión fijada** si está disponible (las políticas son datos versionados, no pesos: mantener N-1 es barato). Si no está, responde `409 POLICY_VERSION_UNAVAILABLE` y AICrew bloquea CVs nuevos en ese proceso con mensaje claro |
| Cambia la versión del modelo y el proceso fijó otra | AICrew detecta la discrepancia al recibir `versions` y **bloquea CVs nuevos en ese proceso**, ofreciendo: reevaluar el proceso completo con la versión nueva, o cerrarlo y abrir uno nuevo |
| Un administrador decide continuar igualmente | Excepción explícita, registrada en `config_history`, y el proceso queda marcado como **heterogéneo**: sus informes y comparaciones muestran el aviso, igual que hoy se avisa al comparar versiones de plantilla distintas |

Lo que no se admite es continuar en silencio. Un ranking con minimizaciones
mezcladas y sin aviso es exactamente el tipo de fallo que la trazabilidad de
CLAUDE.md existe para impedir.

## 4.4. Otros Consumidores

El contrato se diseña genérico desde el día uno, con `policy_id` por caso de
uso: evaluación de propuestas y licitaciones, publicaciones técnicas, cualquier
flujo interno que preceda a una llamada LLM. **Nota regulatoria:** cada
Consumidor hereda su propia clasificación AI Act; el Servicio no la transmite
(§14.2).

---

# 5. Requisitos funcionales

| Id | Requisito | Prioridad |
|---|---|---|
| **RF-1** | Recibir texto plano UTF-8 y un identificador de política, y devolver el texto minimizado. | Must |
| **RF-2** | Normalizar el texto de entrada **preservando un mapa de offsets** carácter a carácter contra el original, con test de ida y vuelta. | Must |
| **RF-3** | Detectar identificadores estructurados mediante reglas deterministas. **Mínimo contractual:** todo lo que hoy cubre `app/core/anon_layer1.py` —email (incluido el partido por el maquetado del PDF), teléfono español en cualquier agrupación, DNI/NIE con y sin guion, IBAN, URL, código postal etiquetado y suelto con validación de rango de provincia, y fecha completa día-mes-año— **respetando el supuesto documentado en `anon_layer1.py:16-22`**: los rangos mes/año de experiencia laboral NO son fechas absolutas y se conservan. Ampliaciones: pasaporte, NIF de persona jurídica (para **distinguirlo** del DNI), IBAN no español, perfiles sociales sin esquema, nº de la Seguridad Social. | Must |
| **RF-4** | Detectar entidades contextuales mediante modelo de clasificación de tokens. **Mínimo contractual:** todo lo que hoy cubre la capa 2 LLM según `llm/prompts/v1/anonymization_system.md` —nombre propio y sus variantes cortas o iniciales, marcador de género, categorías del art. 9 RGPD y referencias a terceros con sus datos de contacto—, más organización, localización, formación y fechas para poder aplicarles política. | Must |
| **RF-5** | Fusionar y deduplicar hallazgos de ambas fuentes con precedencia **determinista y documentada**: span más largo; a igual longitud, regla sobre modelo; a igual origen, etiqueta de mayor riesgo; a igual riesgo, orden alfabético de etiqueta. | Must |
| **RF-6** | Aplicar la política versionada y asignar a cada hallazgo una de cuatro acciones: `KEEP`, `GENERALIZE`, `REDACT`, `REVIEW`. | Must |
| **RF-7** | Sustituir cada `REDACT` por una marca del **catálogo versionado** (§8), con índice estable: la misma entidad recibe el mismo índice en todas sus apariciones del documento. | Must |
| **RF-8** | Aplicar `GENERALIZE` mediante tablas versionadas (p. ej. municipio → provincia), sin llamar a ningún modelo generativo. | Must |
| **RF-9** | Marcar como `REVIEW` los hallazgos no concluyentes y devolverlos en `review_items` con offset, etiqueta candidata, confianza, motivo, acción provisional y opciones de resolución. | Must |
| **RF-10** | Fijar `status = REVIEW_REQUIRED` cuando exista al menos un `review_item`, de forma que el Consumidor pueda decidir sin inspeccionar la lista. | Must |
| **RF-11** | Devolver todas las versiones vigentes (servicio, modelo + hash del artefacto, reglas, política, preprocesamiento, catálogo de marcas) en cada respuesta. | Must |
| **RF-12** | **No devolver el valor literal** de los spans detectados, ni ningún mapa inverso marca → valor, en ningún modo de funcionamiento salvo el diagnóstico (§10, RC-4). La trazabilidad se obtiene con offsets, etiqueta y marca. | Must |
| **RF-13** | Honrar la `policy_version` solicitada si está disponible; si no, responder `409 POLICY_VERSION_UNAVAILABLE` sin procesar (§4.3). | Must |
| **RF-14** | *(En el Consumidor)* Verificación independiente del texto devuelto con `anonymize_layer1()` (§3.4). Cualquier hallazgo ⇒ fail-closed. | Must |
| **RF-15** | Exponer el catálogo de políticas disponibles, su versión y su matriz `etiqueta → acción`. | Must |
| **RF-16** | Exponer el **catálogo de marcas neutras** vigente y su versión (§8), para que el Consumidor pueda validar compatibilidad antes de procesar. | Must |
| **RF-17** | Soportar `mode: "dry_run"`, que devuelve hallazgos y estadísticas sin texto minimizado, para evaluación y calibración. | Should |
| **RF-18** | Soportar `language_hint` y detectar el idioma cuando no se indique. | Should |
| **RF-19** | Admitir un `policy_override` acotado (p. ej. forzar `REDACT` en una etiqueta concreta) que el Consumidor pueda usar sin desplegar una política nueva. Todo override se refleja en la respuesta. | Could |
| **RF-20** | No exponer ningún endpoint de lote ni acumular estado entre peticiones. Cada petición es independiente y su resultado no depende de ninguna anterior. | Must |

---

# 6. Contrato de API

Todos los endpoints bajo `/v1/`. El versionado es explícito en la ruta: un
cambio incompatible es `/v2/`, nunca una modificación silenciosa.

## 6.1. `POST /v1/minimize`

**Petición:**

```json
{
  "request_id": "5f3a...-uuid",
  "document_ref": "a1b2c3...",
  "text": "Juan Pérez\njuan.perez@correo.es · 655 12 34 56\nIngeniero aeronáutico\nAirbus, Sevilla\n03/2018 - 07/2024",
  "language_hint": "es",
  "policy_id": "cv_scoring",
  "policy_version": "1.0",
  "mode": "enforce"
}
```

- `request_id`: correlación e idempotencia. **No debe contener PII.**
- `document_ref`: identificador opaco del documento en el Consumidor. En AICrew
  es el `candidate_id` (SHA-256 del fichero, ya derivado por `compute.py`). Se
  usa para correlacionar logs. **Nunca un nombre ni un DNI.**
- `policy_version`: la que fijó el proceso (§4.2). Omitirla hace la llamada no
  reproducible; el Servicio usaría la vigente y la declararía en la respuesta.
- `mode`: `enforce` (por defecto) o `dry_run`.

Obsérvese que el `text` de ejemplo ya no está pre-anonimizado: esa es la
diferencia con la v0.1.

**Respuesta `200 OK`:**

```json
{
  "request_id": "5f3a...-uuid",
  "status": "OK",
  "sanitized_text": "[PERSONA_1]\n[EMAIL_1] · [TELEFONO_1]\nIngeniero aeronáutico\nAirbus, Andalucía\n03/2018 - 07/2024",
  "detections": [
    { "index": 0, "label": "PERSON_NAME", "start": 0,  "end": 10, "action": "REDACT",     "placeholder": "[PERSONA_1]",  "confidence": 0.994, "risk": "HIGH",   "source": "MODEL", "reason": "CONTEXTUAL_ENTITY" },
    { "index": 1, "label": "EMAIL",       "start": 11, "end": 32, "action": "REDACT",     "placeholder": "[EMAIL_1]",    "confidence": 1.0,   "risk": "HIGH",   "source": "RULE",  "reason": "STRUCTURED_IDENTIFIER" },
    { "index": 2, "label": "ORGANIZATION","start": 70, "end": 76, "action": "KEEP",       "confidence": 0.981, "risk": "LOW",    "source": "MODEL", "reason": "POLICY_PROFESSIONAL_CONTENT" },
    { "index": 3, "label": "LOCATION_CITY","start": 78,"end": 85, "action": "GENERALIZE", "replacement": "Andalucía",    "confidence": 0.972, "risk": "MEDIUM", "source": "MODEL", "reason": "POLICY_GENERALIZE_CITY" }
  ],
  "review_items": [],
  "stats": {
    "detections_total": 12,
    "by_action": { "KEEP": 6, "GENERALIZE": 2, "REDACT": 4, "REVIEW": 0 },
    "by_category_rgpd": { "dato_contacto": 2, "identificador_oficial": 1 }
  },
  "versions": {
    "service": "1.0.0",
    "model": "privacyguard-es-1.0",
    "model_sha256": "9f2b...",
    "rules": "1.0",
    "policy": "cv_scoring@1.0",
    "preprocessing": "1.0",
    "placeholders": "1.0"
  },
  "timing_ms": 412
}
```

Puntos de diseño relevantes:

- **`by_category_rgpd` usa las categorías que AICrew ya registra** en
  `anonymization_log` (`dato_contacto`, `identificador_oficial`,
  `dato_financiero`, `identificador_web`, `dato_localizacion`, `dato_fecha`, y
  las de capa 2: `nombre_propio`, `marcador_genero`, `dato_articulo9_rgpd`,
  `referencia_tercero`). Así el Consumidor inserta sus contadores sin traducir
  nada. Categorías nuevas se añaden, nunca se renombran.
- **`review_items` no incluye el texto del span.** Solo offsets. El Consumidor
  tiene el texto original y lo muestra al revisor bajo su propio control de
  acceso.
- **`provisional_action` es conservadora.** Un `REVIEW` sin resolver jamás
  degrada a `KEEP`.
- **`sanitized_text` ya incluye la acción provisional aplicada**, de modo que el
  Consumidor puede continuar sin reconstruir el texto (§12.2).

**Códigos de error** (todos con cuerpo `{error_code, message, request_id}`):

| Código | `error_code` | Situación | Acción del Consumidor |
|---|---|---|---|
| `400` | `INVALID_REQUEST` | Esquema de petición inválido | Fail-closed, error de programación |
| `409` | `POLICY_VERSION_UNAVAILABLE` | La versión de política fijada por el proceso no está disponible | Fail-closed, bloquear CVs nuevos en el proceso, avisar al administrador |
| `413` | `TEXT_TOO_LARGE` | Texto por encima del límite (RNF-9) | Fail-closed, mensaje al usuario |
| `422` | `UNPROCESSABLE_TEXT` | Texto vacío, binario o codificación inválida | Fail-closed, mensaje explícito |
| `429` | `BUSY` | Límite de concurrencia | Reintento con backoff, máx. 2 |
| `503` | `NOT_READY` | Modelo no cargado o servicio arrancando | Reintento con backoff, máx. 2; después fail-closed |
| `500` | `INTERNAL` | Fallo interno | Fail-closed, registrar incidente |

El cuerpo de error **nunca** incluye fragmentos del texto recibido. Con el CV
íntegro cruzando la frontera (§3.5), un mensaje de error que "ayude a depurar"
citando el texto es una fuga.

## 6.2. `GET /v1/health`

Estado (`ok` / `degraded` / `loading`), modelo cargado, versiones, uptime. Sin
autenticación en modo local; autenticado en modo servidor.

## 6.3. `GET /v1/version`

Todas las versiones y el hash del artefacto del modelo. Es lo que AICrew
persiste por evaluación y por proceso para que ambos sean reproducibles.

## 6.4. `GET /v1/policies` y `GET /v1/policies/{id}`

Catálogo de políticas, versiones disponibles y detalle de la matriz
`etiqueta → acción` vigente. Permite que el Consumidor muestre al usuario, y al
auditor, qué política se aplicó sin leer el código del Servicio.

## 6.5. `GET /v1/placeholders`

Catálogo de marcas neutras vigente y su versión (§8). AICrew lo consulta al
arrancar para comprobar que la versión del catálogo coincide con la que esperan
sus prompts de juicio; si no coincide, lo advierte en administración en lugar de
descubrirlo por una caída de puntuación.

---

# 7. Requisitos no funcionales

| Id | Requisito | Criterio de aceptación |
|---|---|---|
| **RNF-1 — Sin estado** | No se persiste texto, hallazgos, peticiones ni respuestas. Ni en disco, ni en BD, ni en caché, ni entre peticiones del mismo lote. | Auditoría de código + test que ejecuta N peticiones y comprueba que no se escribe ningún fichero fuera de los logs de contadores. |
| **RNF-2 — Determinismo** | Misma entrada + mismas versiones ⇒ salida **byte a byte idéntica**. | 20 ejecuciones del mismo documento en 2 máquinas del parque objetivo, con igualdad exacta de la respuesta serializada (excluyendo `timing_ms` y `request_id`). |
| **RNF-3 — Sin salida a internet** | Cero conexiones salientes en ejecución. Sin telemetría, sin autoactualización, sin descarga de modelos en caliente. | **Test con la red cortada.** |
| **RNF-4 — CPU** | Inferencia 100 % CPU en producción. | Benchmark en el hardware objetivo real. |
| **RNF-5 — Latencia por CV** | p95 ≤ 3 s para un CV de 2 páginas (≈6.000 caracteres). | Benchmark documentado. Valor a confirmar tras la primera medición (D-7). |
| **RNF-6 — Memoria** | ≤ 2 GB de RSS con el modelo cargado. Una sola versión de modelo activa. | Medición en el hardware objetivo. |
| **RNF-7 — Arranque** | ≤ 60 s hasta `health = ok`. Durante el arranque responde `503`, nunca procesa con el modelo a medio cargar. | Test de arranque. |
| **RNF-8 — Concurrencia** | Al menos 4 peticiones simultáneas sin degradación superior al 50 % de la latencia p95. Por encima del límite, `429` limpio, nunca degradación silenciosa ni cola ilimitada. | Test de carga. |
| **RNF-9 — Límites** | Texto ≤ 200 KB; cuerpo de petición ≤ 1 MB. Por encima, `413`. | Test de límites. |
| **RNF-10 — Portabilidad** | Windows 11 x86-64 sin permisos de administrador ni instalación en el sistema, y Linux para el modo servidor. | Instalación en un equipo limpio del parque. |
| **RNF-11 — Trazabilidad** | Toda respuesta declara las versiones que la produjeron, incluido el hash del artefacto. | Validación de esquema de respuesta. |
| **RNF-12 — Fail-safe de arranque** | Si el hash del artefacto no coincide con el declarado en configuración, el Servicio **no arranca**. | Test con artefacto alterado. |
| **RNF-13 — Presupuesto de lote** | Un lote de 20 CVs de 2 páginas se minimiza completo en ≤ 2 minutos de reloj con 4 peticiones concurrentes. | Benchmark de lote en hardware objetivo. |
| **RNF-14 — Higiene de memoria** | El texto de una petición no sobrevive a su respuesta en estructuras de proceso reutilizables (buffers, cachés de tokenizador, trazas de excepción). Las trazas de error no incluyen el texto. | Revisión de código + test que provoca una excepción y comprueba que el texto no aparece en la traza ni en el log. |

## 7.1. Sobre RNF-2 (determinismo)

No es una aspiración: AICrew cachea de forma determinista (F4_b) y su auditoría
es insert-only. Un Servicio no determinista invalida la caché y hace
irreproducible la evaluación, y CLAUDE.md es explícito: *sin trazabilidad, la
evaluación no es válida*.

Implicaciones técnicas: número de hilos de inferencia fijado, reducciones
deterministas, desempates estables en la fusión de spans, sin dependencia del
orden de iteración de diccionarios, ni de `hash()` aleatorizado, ni de reloj,
locale o rutas absolutas.

## 7.2. Sobre RNF-13 (lote) y por qué no hay endpoint de lote

El reclutador no sube un CV: sube los que ha recibido. Si minimizar 20 CVs
tarda diez minutos, el sistema se percibe como lento y se buscan atajos, que es
como mueren los controles de privacidad.

Aun así, **no se añade un endpoint de lote**: implicaría estado de lote, cola,
resultados parciales y reintentos en el Servicio, es decir, cruzar la frontera
de §2.3 y heredar obligaciones de retención. El lote se gestiona en AICrew con
un pool de concurrencia acotado y configurable (`privacy_max_concurrency`, por
defecto 3), tratando cada CV como independiente: **el fallo de un CV no aborta
el lote**, se marca ese CV y el resto continúa (CA-10).

---

# 8. Catálogo de marcas neutras

Hoy AICrew emite dos formatos incompatibles: la capa 1 produce `[EMAIL_1]`,
`[TELEFONO_1]`, `[DNI_NIE_1]`, `[IBAN_1]`, `[URL_1]`, `[CODIGO_POSTAL_1]`,
`[FECHA_ABSOLUTA_1]` (indexados, `anon_layer1.py:177`), y la capa 2 produce
`[NOMBRE_PROPIO]`, `[REFERENCIA_TERCERO]` (sin índice,
`prompts/v1/anonymization_system.md:48`). El Servicio unifica ambos.

| Id | Requisito |
|---|---|
| **RM-1** | Existe un **catálogo de marcas versionado** (`placeholders@X.Y`), fichero de datos, no código disperso: etiqueta → prefijo de marca. |
| **RM-2** | Toda marca tiene la forma `[TIPO_n]` con índice, incluidas las de entidades contextuales. El índice es estable por entidad dentro del documento: sin correferencia, "trabajó en [ORGANIZACION] y volvió a [ORGANIZACION]" pierde sentido y la evaluación se degrada. |
| **RM-3** | El catálogo **conserva los prefijos ya en producción** de la capa 1 (`EMAIL`, `TELEFONO`, `DNI_NIE`, `IBAN`, `URL`, `CODIGO_POSTAL`, `FECHA_ABSOLUTA`). Cambiarlos rompería la comparabilidad con las evaluaciones históricas sin ganar nada. |
| **RM-4** | Las marcas **no filtran información por su forma**: ni longitud proporcional al dato original, ni índices que permitan contar apariciones de un apellido concreto en un informe. |
| **RM-5** | Un cambio en el catálogo es un cambio de versión y **obliga a una nueva versión de los prompts de juicio** de AICrew (CLAUDE.md: cambiar un prompt = nueva versión) y a invalidar la caché de evaluaciones. Se mide su efecto sobre la puntuación antes de desplegarlo (§15, criterio 4). |

**Por qué RM-5 importa más de lo que parece:** el texto minimizado es la entrada
de E4. Cambiar `[NOMBRE_PROPIO]` por `[PERSONA_1]` cambia lo que lee el modelo
que emite los juicios 0 / 0,5 / 1. Es un cambio de entrada del sistema de
evaluación disfrazado de detalle de formato, y se trata como tal.

---

# 9. Seguridad y red

| Id | Requisito |
|---|---|
| **RS-1** | Modo local: escucha **solo** en `127.0.0.1`. Modo servidor: solo en la interfaz interna, nunca en `0.0.0.0` sin cortafuegos delante. |
| **RS-2** | **TLS obligatorio siempre que el destino no sea `127.0.0.1`**, vía módulo `ssl` o proxy corporativo (coherente con la restricción 9 de CLAUDE.md). Sin excepción por "red interna de confianza": por ese canal viaja el CV íntegro (§3.5). |
| **RS-3** | Autenticación servicio a servicio mediante token en cabecera, rotable, almacenado como el resto de secretos de la organización. mTLS si Sistemas lo prefiere. |
| **RS-4** | Lista de Consumidores autorizados por token; cada token identifica al Consumidor en los logs de contadores. |
| **RS-5** | **El Servicio no se publica fuera de la red interna bajo ninguna circunstancia.** Ni con VPN, ni con "acceso temporal para pruebas". |
| **RS-6** | Sin conexiones salientes (RNF-3), verificado con el test de red cortada. |
| **RS-7** | Cabeceras de respuesta restrictivas; sin CORS permisivo; sin interfaz web. |
| **RS-8** | El proceso corre con usuario sin privilegios y sin escritura fuera de su directorio de logs. Volcados de memoria (`core dumps`) deshabilitados: contendrían CVs completos. |
| **RS-9** | El Servicio rechaza peticiones sin token válido antes de leer el cuerpo, para no cargar en memoria texto de un origen no autorizado. |

---

# 10. Requisitos de cumplimiento RGPD

| Id | Requisito |
|---|---|
| **RC-1** | El Servicio **no persiste datos personales** (RNF-1). Es la garantía principal y debe poder demostrarse por auditoría de código. |
| **RC-2** | Los logs registran **contadores y metadatos**, nunca texto ni valores detectados: `request_id`, `document_ref`, marca de tiempo, versiones, hallazgos por etiqueta, acciones aplicadas, latencia, código de resultado. |
| **RC-3** | Los rangos de confianza se registran agregados cuando un valor individual pudiera permitir inferir el dato. |
| **RC-4** | El modo diagnóstico (que sí expone valores) requiere activación explícita, queda deshabilitado en producción por configuración, y su activación se registra. |
| **RC-5** | El flujo **"CV completo, sin minimizar, de AICrew al Servicio por la red interna"** se incorpora al registro de actividades (art. 30) y a la DPIA de AICrew antes de producción. Descrito así, no como "texto de CV". |
| **RC-6** | La documentación y la interfaz emplean "minimización" y "seudonimización"; nunca "anonimización" (§1.2). |
| **RC-7** | Si se usan CV reales para entrenar o evaluar, aplica íntegramente §11.2 del plan de desarrollo: base jurídica, compatibilidad de fines (art. 6.4), información a los interesados, régimen del art. 9 para los anotadores, y resolución del conflicto con la purga de PA-1. |
| **RC-8** | Test de memorización obligatorio antes de aprobar cualquier versión entrenada con datos reales. |
| **RC-9** | El plazo de conservación de los logs del Servicio es el de PA-4, no uno propio. |
| **RC-10** | Derechos del interesado: como el Servicio no persiste nada, acceso, rectificación y supresión se atienden **íntegramente en el Consumidor**. Debe constar así, para que nadie los busque en el sitio equivocado. |
| **RC-11** | *(En el Consumidor)* El **texto minimizado que AICrew almacena es dato personal seudonimizado** y entra en el alcance de la retención PA-1. Hoy `db/retention.py` solo vacía `documents.file_bytes`, `original_filename` y `content_type`: la tabla de caché de minimización sobreviviría a la purga y seguiría siendo dato personal. D-11. |

---

# 11. Requisitos de equidad y calidad del modelo

Requisitos con rango propio, no métricas informativas. Justificación completa en
§14.4 del plan de desarrollo.

| Id | Requisito |
|---|---|
| **RE-1** | Las métricas de detección se miden **estratificadas por origen del nombre** (al menos: español, latinoamericano, magrebí, subsahariano, europeo del este, asiático, europeo occidental). |
| **RE-2** | Ninguna métrica de un estrato puede quedar más de un margen aprobado por debajo de la mejor. El margen lo fija JJO con el DPO (D-8). |
| **RE-3** | Se mide la **utilidad conservada**: proporción de entidades profesionales correctamente mantenidas y correlación de la puntuación final de AICrew entre el texto minimizado por el Servicio y el del sistema actual. |
| **RE-4** | Se mide la **tasa de `REVIEW` por estrato**. Con el criterio de §12.2 (acción conservadora automática), se mide además la **tasa de sobre-redacción por estrato**: si los CV con nombres extranjeros pierden más evidencia, el sesgo se traslada a la puntuación sin pasar por ninguna cola visible. |
| **RE-5** | El corpus sintético incluye nombres no españoles con la misma densidad que los españoles. Sin esto, RE-1 no es medible. |

**Por qué esto es un requisito y no una buena práctica:** un modelo que reconoce
peor los nombres extranjeros redacta peor (fuga de PII) o redacta de más
(pérdida de evidencia → peor puntuación). Lo segundo es impacto discriminatorio
por origen, exactamente lo que el Anexo III 4(a) del AI Act pretende vigilar. Un
modelo sin estratificar no se aprueba.

---

# 12. Human-in-the-loop

## 12.1. División de responsabilidades

| | Servicio | Consumidor (AICrew) |
|---|---|---|
| Detectar la incertidumbre | ✔ | |
| Marcar `REVIEW` y proponer acción provisional conservadora | ✔ | |
| **Almacenar** la cola de revisión | | ✔ |
| **Mostrar** el fragmento original al revisor | | ✔ |
| Controlar **quién** puede revisar | | ✔ |
| **Auditar** la resolución (insert-only) | | ✔ |
| Aplicar la resolución al texto | | ✔ |
| Aprender del caso (active learning) | ✔ (con el caso exportado y aprobado) | |

**Motivo del reparto:** la cola de revisión expone texto **sin minimizar**. Es
una superficie de acceso a datos personales y debe heredar el régimen que
AICrew ya tiene —rol autorizado, motivo, registro insert-only, como
`unmask_events`— en vez de crear un canal paralelo sin control.

## 12.2. Cambio de criterio: no bloquear por defecto (D-4)

La v0.1 (RH-3) bloqueaba el documento hasta que un humano resolviera cada
`review_item`. Para el flujo descrito —un reclutador sube veinte CVs a un
proceso— eso significa que dos o tres CVs se quedan parados esperando a alguien
que debe leer texto sin minimizar. Se propone invertir el default:

| | Bloquear (v0.1, RH-3) | **Conservador automático (propuesto)** |
|---|---|---|
| Qué pasa con el CV | No avanza hasta que un humano resuelve | Avanza con la acción provisional **más protectora** ya aplicada |
| Riesgo de fuga | Nulo | **Nulo**: la acción provisional nunca degrada a `KEEP` (RH-2) |
| Coste | El lote se detiene; alguien debe leer PII de varios CV | Posible **sobre-redacción**: ese CV puede perder evidencia y puntuar por debajo de lo que merece |
| Visibilidad del coste | Alta (hay una cola) | Requiere aviso explícito en el dossier, si no es invisible |

Requisitos que hacen aceptable el default propuesto:

| Id | Requisito |
|---|---|
| **RH-1** | `review_items` contiene offsets, etiquetas candidatas, confianza, motivo, acción provisional y opciones de resolución. **Nunca el valor del span.** |
| **RH-2** | La acción provisional es siempre la más protectora entre las plausibles. Un `REVIEW` sin resolver nunca degrada a `KEEP`. |
| **RH-3** | *(Consumidor)* Un CV con `REVIEW_REQUIRED` avanza con la acción provisional aplicada **y el dossier lo declara de forma visible**: "este CV se evaluó con N fragmentos redactados por precaución; su puntuación puede estar infravalorada". El humano que decide ve el aviso junto a la puntuación, que es donde sirve de algo. |
| **RH-4** | *(Consumidor)* El responsable del proceso puede resolver los casos marcados y **solicitar la reevaluación** de ese CV. La resolución registra quién, cuándo, hallazgo, acción elegida y versiones del Servicio. Insert-only. |
| **RH-5** | *(Consumidor)* El fail-closed se mantiene **intacto** para todo lo demás: servicio caído, timeout, esquema inválido, `409`/`500`, o verificación RF-14 con hallazgos. Ahí no se avanza nunca. |
| **RH-6** | **Presupuesto de revisión:** ≤ 3 `review_items` por documento en el percentil 95, y ≤ 10 % de documentos con al menos uno. Superarlo es un fallo de calibración del Servicio, no un problema del revisor. |
| **RH-7** | El Consumidor puede exportar las resoluciones, previa aprobación, como casos de entrenamiento. La exportación es un tratamiento con su propia base jurídica (RC-7). |

**Sobre RH-6:** es el requisito que más fácilmente se incumple y el que más daño
hace. Con el default propuesto, incumplirlo ya no produce una cola que nadie
mira, sino algo peor: muchos CV evaluados con evidencia recortada y un aviso que
se vuelve rutina. `GENERALIZE` existe precisamente para mantener el presupuesto
sin rebajar la protección.

## 12.3. Separación de funciones (D-9)

Quien resuelve una revisión lee el fragmento original de un candidato al que
después se va a puntuar. Dos exigencias:

1. **No debe ser quien decide sobre ese candidato**, o la evaluación deja de ser
   ciega para ese CV. Si por tamaño de equipo no es posible separarlo, debe
   constar en la DPIA como riesgo aceptado, no ignorarse.
2. **Se muestra el fragmento marcado con una ventana de contexto acotada**
   (p. ej. ±200 caracteres), nunca el CV completo. Cada visualización se registra
   en `access_log`.

---

# 13. Requisitos del lado de AICrew relativos al caso de uso

## 13.1. Vinculación texto minimizado ↔ CV original (paso 5)

| Id | Requisito |
|---|---|
| **RV-1** | La vinculación es el `candidate_id` (SHA-256 del fichero) que ya existe. No se crea ningún identificador nuevo ni ningún mapa adicional. |
| **RV-2** | El texto minimizado se guarda en `minimization_cache`, con clave `(candidate_id, service_version, model_sha256, rules_version, policy_id, policy_version, placeholders_version)`. Como la minimización **no depende del JD**, el mismo CV en otro proceso reutiliza el texto **si y solo si** las versiones fijadas por ese proceso coinciden. |
| **RV-3** | Un cambio de cualquiera de esas versiones produce una entrada nueva, nunca sobrescribe. Si la caché no incluye las versiones del Servicio, un cambio de modelo devolvería resultados antiguos y **la trazabilidad mentiría**. |
| **RV-4** | El texto minimizado está sujeto al mismo control de acceso por rol que el dossier y al régimen de retención de PA-1 (RC-11, D-11). |

## 13.2. Quién ve el CV completo (paso 6)

El caso de uso dice "solo el responsable elegido puede ver el CV completo de
cada candidato". **Eso hoy no está implementado tal cual.**

| | Hoy (`server.py:844`, `auth/provider.py:28`) | Lo que describe el caso de uso |
|---|---|---|
| Quién desenmascara | Cualquier usuario con rol `responsable_reclutamiento` | El responsable **asignado a ese proceso** |
| Alcance | Cualquier candidato con al menos una evaluación | Los candidatos **de su proceso** |
| Registro | `unmask_events` + `access_log`, con motivo obligatorio | Igual |

Cerrar esa diferencia es un cambio en AICrew, no en el Servicio: añadir un
responsable asignado a `processes` y restringir el desenmascaramiento a los
candidatos de sus procesos (CA-13). Es **decisión de JJO** (D-10): el modelo
actual es más simple y puede ser el deseado; el descrito es más estricto y
encaja mejor con el principio de necesidad de conocer.

En ninguno de los dos modelos el Servicio participa: **no devuelve mapa inverso
ni conserva nada** (RF-12). El único camino a la identidad sigue siendo el
fichero original de `documents`, bajo rol y auditoría.

---

# 14. Requisitos del AI Act

## 14.1. El Servicio como componente

Integrado en AICrew, el Servicio es **componente de un sistema de alto riesgo**
del Anexo III 4(a). Entra en su documentación técnica (art. 11), su sistema de
gestión de la calidad (art. 17) y su gestión de riesgos (art. 9). Separar
repositorios no crea una frontera regulatoria: ATEXIS es proveedor de ambos.

| Id | Requisito |
|---|---|
| **RA-1** | El Servicio mantiene su propia ficha técnica (arquitectura, datos de entrenamiento, métricas, limitaciones conocidas, versiones), incorporable a la documentación técnica de cada Consumidor de alto riesgo. |
| **RA-2** | Registro de eventos (art. 12) versionado por modelo, reglas y política, insert-only en el lado del Consumidor. |
| **RA-3** | Explicabilidad (art. 13): cada decisión identificable por offset, etiqueta, confianza, origen (regla o modelo), regla de política aplicada y versión. |
| **RA-4** | Supervisión humana efectiva (art. 14): §12, con presupuesto de revisión real **y** con el aviso de RH-3 visible junto a la puntuación. Con el default de §12.2, la supervisión que cuenta es la del humano que decide sobre el candidato, no la de una cola intermedia. |
| **RA-5** | Exactitud y robustez (art. 15): métricas, red-team adversarial, regresión obligatoria, determinismo y benchmark en hardware objetivo. |
| **RA-6** | Gobernanza de datos y examen de sesgo (art. 10): §11 y §7.8 del plan de desarrollo. |
| **RA-7** | Ninguna versión se despliega sin superar la batería de regresión completa, incluidos los tests de equidad, determinismo, memorización y **conformidad con la capa 1** (§15, criterio 0). |

## 14.2. Naturaleza dual

Usado de forma autónoma —minimizar texto antes de una llamada LLM en un flujo
que no evalúa personas—, el Servicio **no es un uso del Anexo III** y no arrastra
obligaciones de alto riesgo a ese Consumidor. La clasificación la determina el
uso del Consumidor, no la existencia del Servicio. Esto permite desplegarlo para
el resto de ATEXIS sin contaminar cada uso con el régimen de alto riesgo,
siempre que cada Consumidor documente su clasificación.

**A confirmar por Asesoría Jurídica (D-6).** No dar por buena esta lectura sin
dictamen.

---

# 15. Criterios de aceptación del producto

El Servicio puede pasar a `anon_mode = privacyguard` —es decir, **sustituir a
las dos capas actuales**— si y solo si, sobre el conjunto ciego y con la política
congelada, cumple **todos** los criterios siguientes. Se fijan **antes** de
medir y requieren firma de JJO y del DPO.

| # | Criterio | Umbral |
|---|---|---|
| **0** | **Conformidad con la capa 1.** La batería de tests de `anon_layer1.py` se ejecuta contra el Servicio como suite de conformidad: mismos casos positivos, negativos parecidos, formatos alternativos y solapamientos. | **100 %.** Cualquier fallo es una regresión respecto a lo que hoy hay en producción |
| 1 | Recall de identificadores directos | ≥ el de capa 1 + capa 2 y ≥ **0,99** |
| 2 | Recall de categorías del art. 9 | ≥ el de capa 1 + capa 2 y ≥ **0,98** |
| 3 | Document Privacy Failure Rate | ≤ el de capa 1 + capa 2 |
| 4 | Utilidad profesional conservada, y correlación de la puntuación final de `compute.py` | ≥ **0,95** |
| 5 | Paridad entre estratos (RE-2) | dentro del margen aprobado |
| 6 | Determinismo (RNF-2) | exacto |
| 7 | Presupuesto de revisión (RH-6) | cumplido |
| 8 | Latencia p95 por CV (RNF-5) y presupuesto de lote (RNF-13) | cumplidos en hardware objetivo |
| 9 | Test de red cortada (RNF-3) | superado |
| 10 | Verificación independiente (RF-14) sobre el conjunto ciego | cero hallazgos residuales |
| 11 | Compatibilidad del catálogo de marcas (RM-5): el cambio de formato no degrada la puntuación | medido y aprobado |

**Si cumple 0-3 pero no 4-11:** se despliega en `anon_mode = serie`, no en
sustitución.
**Si no cumple 0-3:** no se despliega.

El criterio 0 es nuevo respecto a la v0.1 y es el más barato de todos: son tests
que ya existen. También es el más importante, porque la sustitución solo es
segura si el Servicio cubre primero el suelo que hoy ya está cubierto.

Medir el sistema actual (capa 1 + capa 2 LLM) sobre el mismo conjunto ciego
forma parte del trabajo: sin línea base no hay criterio, solo opinión. Por eso
`anon_layer2.py` se conserva en `benchmarks/`.

---

# 16. Despliegue

## 16.1. Modo local (PC/portátil)

- Servicio en `127.0.0.1:PUERTO`, mismo equipo que AICrew. TLS innecesario solo
  en este caso (RS-2).
- LLM de juicio: el de la oficina, por red interna.
- Requisitos: 4 núcleos, 8 GB de RAM, 1–2 GB de disco.
- Arranque por el mismo `start.bat` que ya lanza AICrew, sin permisos de
  administrador ni instalación en el sistema.
- **Modelo de amenaza:** el CV original, el texto minimizado y los fragmentos de
  revisión residen en un equipo que puede perderse. Exige cifrado de disco
  corporativo y purga por retención igual que en servidor.
- **Uso recomendado:** desarrollo, pruebas y piloto.

## 16.2. Modo servidor (oficina)

- Servicio en la red interna **con TLS obligatorio** (RS-2), una sola copia del
  modelo en memoria, multiusuario.
- Depende de PA-3 (servidor definitivo).
- **Uso recomendado: producción.**

## 16.3. Común a ambos

El artefacto del modelo se descarga **una vez**, se verifica por hash, se
registra su licencia y se distribuye internamente. En ejecución no hay descarga,
telemetría ni actualización automática, y eso se verifica con el test de red
cortada (RNF-3). Esa prueba —"funciona con el cable desenchufado"— convierte
"sin salida fuera de la red" en un hecho comprobable.

---

# 17. Cambios requeridos en AICrew

El otro lado del contrato. Sin esto, el Servicio no sirve para nada. Las
migraciones siguen la numeración existente (0001-0005 aplicadas): la siguiente
es `0006`. Ningún fichero de migración aplicado se modifica.

| Id | Cambio | Módulo |
|---|---|---|
| **CA-1** | Cliente HTTP del Servicio con `urllib.request`: timeout, validación de esquema de respuesta, reintento solo ante `429`/`503` (máx. 2), fail-closed en todo lo demás. Mismo patrón que `llm/client.py`. | `app/privacy/client.py` (nuevo) |
| **CA-2** | Configuración en `config` con historial en `config_history`: `privacy_service_url`, `privacy_service_token`, `privacy_timeout_s`, `privacy_max_concurrency`, `privacy_policy_id`, **`anon_mode`** (§3.2). | `app/db/`, `app/static/administracion.html` |
| **CA-3** | Etapa de minimización en el pipeline según `anon_mode`. En `privacyguard`, sustituye a E2 y E3. `run_pipeline` recibe el cliente del Servicio junto al `LLMClient`, con la misma separación core/db que ya tiene (la caché vive en los callers). | `app/core/pipeline.py` |
| **CA-4** | **Verificación independiente** (RF-14): re-ejecutar `anonymize_layer1()` sobre el texto devuelto; cualquier hallazgo ⇒ fail-closed e incidente registrado. | `app/core/pipeline.py` |
| **CA-5** | Migración 0006: `anonymization_log` admite la capa del Servicio (`CHECK (layer IN (1, 2, 3))`, 3 = minimización por el Servicio). Solo añade; las filas históricas de capas 1 y 2 siguen siendo válidas (restricción 6). | `app/db/migrations/0006_*.sql` |
| **CA-6** | Migración 0006: `evaluations` + `privacy_service_version`, `privacy_model_version`, `privacy_model_sha256`, `privacy_policy_id`, `privacy_policy_version`, `privacy_rules_version`, `privacy_placeholders_version`. Sin ellas la evaluación no es reproducible y, por CLAUDE.md, **no es válida**. | `app/db/migrations/0006_*.sql` |
| **CA-7** | Migración 0006: tabla `minimization_cache` con la clave de RV-2. `layer2_cache` **no se toca**: sus filas son historia válida del modo `legacy`. | `app/db/migrations/0006_*.sql` |
| **CA-8** | Migración 0006: tabla `privacy_calls`, insert-only con sus dos triggers, análoga a `llm_calls`. Las llamadas al Servicio **no van a `llm_calls`**: no es un LLM, y el `CHECK (step IN ('anon_layer2','judge'))` no debe estirarse para que quepa algo que no lo es. Campos: `evaluation_id` (nullable), `candidate_id`, `process_id`, `attempt_number`, `success`, `status`, `latency_ms`, versiones, `error_summary`. Nunca texto. | `app/db/migrations/0006_*.sql` |
| **CA-9** | Migración 0006: `processes` + `privacy_policy_id`, `privacy_policy_version` (fijadas al crear) y `privacy_model_version`, `privacy_model_sha256` (registradas con el primer CV). Control de deriva de §4.3. | `app/db/migrations/0006_*.sql`, `app/server.py` |
| **CA-10** | Estado por CV en la vista de proceso: *pendiente / minimizado / evaluado / con aviso de precaución / error*, con reintento por CV. Un CV que falla **no aborta el lote**. Mensajes en español de España, no técnicos (CLAUDE.md, restricción 2), para todos los modos de fallo del Servicio: caído, timeout, `409`, `413`, `422`, verificación fallida. | `app/static/`, `app/server.py` |
| **CA-11** | Nueva versión de los prompts de juicio compatible con el catálogo de marcas unificado (RM-5), y actualización de la clave de caché de evaluaciones. Los prompts son ficheros versionados: se añade `v3`, no se edita `v1`/`v2` (CLAUDE.md). | `app/llm/prompts/v3/` |
| **CA-12** | Aviso de precaución (RH-3) en el dossier, en el listado del proceso y en los informes: número de fragmentos redactados por precaución y advertencia de posible infravaloración. | `app/static/common/dossier-render.js`, `app/core/schemas.py` |
| **CA-13** | *(Si D-10 lo aprueba)* Responsable asignado en `processes` y desenmascaramiento restringido a los candidatos de sus procesos (§13.2). | `app/db/`, `app/server.py` |
| **CA-14** | Retención: incluir `minimization_cache` en el alcance de la purga de PA-1 según decida D-11, con el mismo registro en `config_history` que ya hace el job. | `app/db/retention.py` |
| **CA-15** | Bloquear con aviso las comparaciones e informes que mezclen CVs minimizados con versiones distintas, igual que ya se bloquean entre versiones de plantilla distintas. | `app/server.py`, `app/static/` |
| **CA-16** | `anon_layer2.py` y sus prompts salen del flujo de la UI y quedan disponibles solo para `cli.py` y `benchmarks/` (línea base de §15). No se borran. | `app/core/pipeline.py`, `benchmarks/` |
| **CA-17** | Benchmark del incumbente (capa 1 + capa 2) sobre el conjunto ciego, y benchmark de lote (RNF-13). | `benchmarks/` |

**CA-6 y CA-7 merecen atención:** si la caché no incluye las versiones del
Servicio, un cambio de modelo devolverá resultados antiguos y la trazabilidad
mentirá. Es el fallo silencioso más probable de toda la integración.

---

# 18. Fases del proyecto

Cada fase termina en **puerta de aprobación de JJO**, siguiendo el formato de
`PLAN.md`. No se inicia la siguiente sin revisión.

| Fase | Contenido | Estimación |
|---|---|---|
| **P0 — Decisiones y contrato** | Cerrar D-1 a D-14. Congelar el contrato de §6 y el catálogo de marcas de §8. Esqueleto del repositorio, `CLAUDE.md` propio, fichas de licencia. | 1 semana |
| **P1 — Servicio sin modelo** | Servidor HTTP, contrato completo, motor de reglas **con conformidad de capa 1 (criterio 0) ya superada**, motor de política puro con tests, normalización con offsets. Ya utilizable: equivale a la capa 1 actual expuesta como servicio. | 2 semanas |
| **P2 — Integración temprana con AICrew** | CA-1 a CA-10 y CA-17. AICrew llama al Servicio en `anon_mode = serie` y el pipeline funciona de punta a punta con la capa 2 todavía activa. **Valida el contrato, el fail-closed, la caché, el lote y la trazabilidad antes de invertir en el modelo.** | 1,5 semanas |
| **P3 — V0 con modelo preentrenado** | Modelo NER de licencia permisiva, sin entrenar. Medición completa con §15 y §11. | 1–2 semanas |
| **Puerta de decisión** | Si V0 cumple §15 → **el proyecto puede terminar aquí**. | — |
| **P4 — Corpus sintético y ajuste** | Solo si V0 no basta. Generación, entrenamiento, evaluación. | 3–4 semanas |
| **P5 — Calibración, marcas y HIL** | Umbrales por etiqueta, presupuesto de revisión, catálogo de marcas unificado, CA-11 a CA-13. | 2 semanas |
| **P6 — Optimización y validación** | CPU, determinismo, red cortada, lote, validación end-to-end, regresión completa. | 2 semanas |
| **P7 — Piloto y conmutación** | Piloto en `serie`, medición del incumbente, decisión de pasar a `privacyguard` (CA-16). | 2 semanas |
| **P8 — Corpus real y active learning** | Solo si el DPO resuelve favorablemente RC-7. | Indeterminado |

**Camino favorable (V0 suficiente): 6–8 semanas.**
**Camino completo sin corpus real: 14–18 semanas a dedicación parcial.**

**Sobre P1 y P2:** integrar contra un Servicio que aún no tiene modelo es
deliberado. Valida el contrato cuando corregirlo todavía es barato. El error
clásico es dedicar dos meses al modelo y descubrir al integrar que el contrato
no sirve. Y exigir el criterio 0 ya en P1 evita construir un modelo encima de un
motor de reglas que cubre menos que la producción actual.

---

# 19. Riesgos

| # | Riesgo | Mitigación |
|---|---|---|
| R1 | **Erosión de la frontera** (§2.3): al Servicio se le añaden estado, caché de texto, histórico "para depurar", endpoint de lote, UI de revisión. | RNF-1 y RF-20 como requisitos auditables; revisión explícita en cada puerta. |
| R2 | **Fallo silencioso**: el Servicio devuelve texto que parece minimizado y no lo está. | Verificación independiente RF-14 (ahora real, §3.4) + fail-closed. |
| **R3** | **Regresión respecto a producción**: el motor de reglas del Servicio cubre menos que `anon_layer1.py` y la sustitución empeora la protección actual. | **Criterio 0 de §15** como puerta, con los tests que ya existen. Riesgo nuevo, introducido por la sustitución. |
| **R4** | **El CV íntegro cruza la frontera de proceso** (§3.5). | RS-2 sin excepciones, RS-3/RS-4, RS-8 sin volcados, RNF-14 higiene de memoria, RC-2 y RC-4 auditables en la puerta. |
| R5 | **Sobre-redacción** que destruye la evidencia que puntúa AICrew. | Criterio 4 de §15 como puerta, acción `GENERALIZE`, aviso RH-3 visible. |
| R6 | **Sesgo por origen del nombre** → impacto discriminatorio. | RE-1 a RE-5 como requisitos, no métricas informativas; RE-4 amplía la medición a la sobre-redacción. |
| **R7** | **Deriva de versiones dentro de un proceso abierto**: dos CVs del mismo ranking minimizados con criterios distintos. | §4.2 (fijación en `processes`), §4.3 (bloqueo y marca de heterogeneidad), CA-9, CA-15. Riesgo nuevo. |
| **R8** | **Cambio del catálogo de marcas** que degrada silenciosamente las puntuaciones de E4. | RM-5, criterio 11 de §15, nueva versión de prompts (CA-11) e invalidación de caché. Riesgo nuevo. |
| **R9** | **Latencia de lote** que hace que el reclutador perciba el sistema como inservible y busque atajos. | RNF-13 como requisito con benchmark, concurrencia acotada en el Consumidor, estado por CV visible (CA-10). Riesgo nuevo. |
| **R10** | **Acumulación de texto minimizado en AICrew** fuera del alcance de la purga PA-1. | RC-11, CA-14, D-11. Riesgo nuevo. |
| R11 | **Aviso de precaución convertido en ruido** (RH-3 aparece en tantos CV que se ignora). | RH-6 como presupuesto medido, RO-4 con alerta, revisión en la puerta de piloto. |
| R12 | **Pérdida de determinismo** → caché y auditoría de AICrew dejan de ser válidas. | RNF-2 bloqueante; claves de caché versionadas (RV-2, RV-3). |
| R13 | **Base jurídica del corpus de entrenamiento** sin resolver. | RC-7; alternativa de corpus sintético siempre disponible. |
| R14 | **Licencias de datasets y modelos.** | Regla default-deny del plan de desarrollo; ficha obligatoria por dataset y por modelo. |
| R15 | **Doble mantenimiento** de las reglas (capa 1 de AICrew + motor del Servicio). | Con el criterio 0, `anon_layer1.py` deja de ser una copia y pasa a ser la **especificación ejecutable del mínimo** y el verificador. La duplicación tiene ahora una función. |
| R16 | **El Servicio nunca llega a sustituir a las dos capas** y solo añade complejidad. | §15 con decisión explícita; la puerta tras P3 permite cerrar el proyecto pronto; `anon_mode = serie` es un estado final aceptable si aporta defensa en profundidad. |
| R17 | **Un Consumidor publica el Servicio fuera de la red** para "una prueba rápida". | RS-5 no negociable; escucha ligada a interfaz interna por configuración, no por convención. |

---

# 20. Observabilidad

| Id | Requisito |
|---|---|
| **RO-1** | Logs de contadores conforme a RC-2, en JSON por línea. |
| **RO-2** | Métricas agregadas: peticiones, latencia p50/p95/p99, tasa de error por código, tasa de `REVIEW_REQUIRED`, hallazgos por etiqueta, CPU y memoria. |
| **RO-3** | Las métricas se exponen en un endpoint interno o se vuelcan a fichero. **No se envían a ningún servicio externo.** |
| **RO-4** | Alerta cuando la tasa de `REVIEW_REQUIRED` supere el presupuesto de RH-6: indica deriva del modelo o política mal calibrada. |
| **RO-5** | Alerta cuando la tasa de fallos de la verificación RF-14 sea distinta de cero: es fuga de PII, no una anomalía estadística. |
| **RO-6** | Los logs permiten reconstruir **qué versiones** procesaron un `document_ref`, sin contener ningún dato personal. |

---

# 21. Decisiones pendientes

Ninguna fase arranca sin D-1 y D-2. Las demás se cierran en P0.

| Id | Decisión | Responsable | Impacto si no se decide |
|---|---|---|---|
| **D-1** | ¿Se aprueba crear ATX PrivacyGuard como **proyecto y servicio independiente**, con sus propias dependencias, manteniendo intacta la restricción 1 de CLAUDE.md para AICrew? | JJO | Bloqueante total. |
| **D-2** | ¿Se aprueba el **alcance de sustitución**: el Servicio sustituye a E2 **y** E3, y AICrew le envía el CV sin anonimizar (§3)? La alternativa es la v0.1 (capa 1.5, capa 1 conservada antes de la llamada). | JJO + DPO | Determina el contrato, la seguridad del canal y el criterio 0. |
| **D-3** | ¿AICrew envía **texto extraído** (recomendado, §3.3) o el fichero binario? | JJO | Condiciona el alcance del Servicio y la gestión del PDF escaneado. |
| **D-4** | Ante un `REVIEW` sin resolver: ¿**bloquear** el CV (v0.1, RH-3) o **continuar con la acción conservadora y aviso visible** (recomendado, §12.2)? | JJO + Recruitment + DPO | Determina la experiencia del reclutador y dónde se ejerce la supervisión humana del art. 14. |
| **D-5** | ¿Se confirma **KEEP** para organización, formación y rangos de fechas, asumiendo el riesgo residual de reidentificación en la DPIA? | JJO + DPO | Sin ella, la política es incompatible con `core/compute.py`. |
| **D-6** | ¿Se confirma la lectura de **naturaleza dual** del §14.2 (el Servicio autónomo no es Anexo III)? | Asesoría Jurídica | Condiciona la reutilización en el resto de ATEXIS. |
| **D-7** | ¿Se aprueban los **umbrales de aceptación** de §15 y las cifras de RNF-5, RNF-6 y RNF-13? | JJO + DPO | Sin ellos, la decisión de conmutar a `privacyguard` será post hoc e indefendible. |
| **D-8** | **Margen de paridad** admisible entre estratos (RE-2). | JJO + DPO | Sin él, el examen de sesgo no tiene puerta. |
| **D-9** | ¿Quién resuelve las revisiones y cómo se aplica la **separación de funciones** de §12.3? | JJO + DPO | Riesgo de contaminar la evaluación y de crear un canal de acceso a PII sin control. |
| **D-10** | ¿El desenmascaramiento se restringe al **responsable asignado al proceso** (§13.2, CA-13) o se mantiene por rol como hoy? | JJO + DPO | Diferencia entre lo descrito en el caso de uso y lo implementado. |
| **D-11** | ¿Entra `minimization_cache` en el alcance de la **purga de PA-1** y con qué calendario (RC-11)? | DPO | El texto seudonimizado sobreviviría a la purga del original. |
| **D-12** | ¿Se autoriza el **corpus real interno** y bajo qué base jurídica (RC-7), y cómo encaja con la purga de PA-1? | DPO + Jurídica | Sin ella, se avanza solo con corpus sintético: viable, con techo más bajo. |
| **D-13** | **Nombre definitivo** del servicio (§1.2). | JJO | Riesgo de afirmación jurídica incorrecta consolidada en el producto. |
| **D-14** | **Renumeración de PA-5**: el identificador está ocupado por la excepción SMTP (`PLAN.md:657`, `PLAN.md:750`). `PA-7` es el siguiente libre (PA-6 se cerró en F4_h). | JJO | Dos puntos abiertos distintos con el mismo número en el mismo repositorio. |

---

# 22. Glosario

| Término | Significado en este documento |
|---|---|
| **Minimización** | Reducir los datos personales presentes en un texto al mínimo necesario para la finalidad. |
| **Seudonimización** | Sustituir identificadores de forma que el dato ya no se atribuya a una persona sin información adicional. **Lo que hace el Servicio.** |
| **Anonimización** | Tratamiento irreversible tras el cual el dato deja de ser personal. **Lo que el Servicio NO hace.** |
| **Hallazgo / detección** | Span de texto identificado como entidad, con etiqueta, offsets y confianza. |
| **Acción** | `KEEP`, `GENERALIZE`, `REDACT` o `REVIEW`. |
| **Política** | Matriz versionada `etiqueta → acción`, más reglas de generalización y umbrales por etiqueta. |
| **Catálogo de marcas** | Fichero versionado que asigna a cada etiqueta su marca neutra `[TIPO_n]` (§8). |
| **Fail-closed** | Ante cualquier fallo, detener el flujo en vez de continuar. |
| **Acción provisional conservadora** | La más protectora entre las plausibles, aplicada automáticamente a un hallazgo no concluyente (§12.2). |
| **HIL** | Human-in-the-loop: resolución humana de los casos no concluyentes. |
| **Consumidor** | Aplicación interna que invoca el Servicio. |
| **Proceso** | Agrupación de evaluaciones de una misma vacante en AICrew (F4_e), con plantilla y versiones de minimización fijadas. |

---

# 23. Nota de mantenimiento

Este documento es una **especificación de requisitos**, no una especificación
jurídica ni un criterio de cumplimiento por sí solo. Antes de la puesta en
producción deben actualizarse: estado y calendario del AI Act; directrices
vigentes de la EDPB sobre anonimización y seudonimización; licencias de datasets
y de modelos; políticas internas de tratamiento; resultados de validación;
umbrales y márgenes de aprobación; y la evaluación de riesgo de
reidentificación.

El plan técnico de desarrollo del detector (taxonomía, datasets, corpus,
entrenamiento, métricas, fases de modelado) vive en
`docs/CV-Privacy-Detector_Plan-Desarrollo_v1.md` y no se duplica aquí. Este
documento define **qué debe hacer el Servicio y bajo qué contrato**; aquel
define **cómo se construye el modelo que lo hace posible**. Las secciones del
plan que asumen la posición de "capa 1.5" (§2.2 y §13/Fase 5) quedan superadas
por §3 y §15 de este documento; el resto sigue vigente.

**Historial:**

- v0.1 — 22/09/2026 — borrador inicial: Servicio como capa 1.5, entre la capa 1
  y la capa 2 de AICrew.
- v1.0 — 23/09/2026 — el Servicio pasa a **sustituir a las dos capas de
  anonimización** de AICrew y se ancla al flujo de procesos de reclutamiento:
  contrato sobre CV sin anonimizar, mínimo contractual de reglas y criterio de
  conformidad con la capa 1, verificación independiente efectiva, catálogo de
  marcas versionado, fijación de versiones por proceso, caché de minimización,
  semántica de lote, revisión no bloqueante por defecto, responsable por proceso
  y riesgos del canal. Detalle en §0.
