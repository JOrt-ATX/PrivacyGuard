# Referencia: capa 1 de AICrew

Copia literal de la capa 1 de anonimización de AICrew, usada como
**especificación ejecutable del mínimo contractual** del motor de reglas
(requisitos §5 RF-3, §15 criterio 0, riesgo R15).

| Fichero aquí | Origen | SHA-256 del origen (25/09/2026) |
|---|---|---|
| `anon_layer1.py` | `C:\AI\AICrew\app\core\anon_layer1.py` | `ca1ff6b360c3faed9bd4cd06c3a974cf3c3b4b107a270513992fcba4236b62f3` |
| `tests/conformance/test_aicrew_layer1_reference.py` | `C:\AI\AICrew\tests\test_anon_layer1.py` | `9c8ea31de46f6eae802236b719b11ea4b29c6a59bbf9d0c2f550a5e30dffc89f` |

Reglas:

- `anon_layer1.py` **no se edita**. Si AICrew cambia su capa 1, se vuelve a
  copiar, se actualiza el hash de esta tabla y se revisa la conformidad.
- El test copiado solo cambia la línea de import.
- El Servicio **no importa** este módulo en producción: su motor de reglas es
  propio (`privacyguard/rules.py`). La referencia solo se usa en tests.
