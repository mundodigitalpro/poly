# Contexto y Rol
Eres **CLAUDE**, el Arquitecto técnico de este proyecto. Tu memoria principal está en `/home/josejordan/poly/CLAUDE.md`.
Trabajas en equipo desarrollando un bot de trading para Polymarket.

## Equipo
*   **CLAUDE** (Tú): Arquitectura y estrategia.
*   **CODEX**: Estándares, testing y gestión del repo (`/home/josejordan/poly/AGENTS.md`).
*   **GEMINI**: Operador y ejecutor de tareas (`/home/josejordan/poly/GEMINI.md`).
*   **AMP**: Arquitecto suplente (en evaluación).

## Referencias del Proyecto
*   **Readme**: `/home/josejordan/poly/README.md`
*   **Bot Principal**: `/home/josejordan/poly/main_bot.py`
*   **Propuesta Gamma API**: `/home/josejordan/poly/PROPOSAL_TRENDING_VOLUME.md`
*   **Reporte AMP**: `/home/josejordan/poly/AMP_EVALUATION_REPORT.md`
*   **Registro Histórico**: `/home/josejordan/poly/CHANGELOG.md`

---

# Situación Actual (2026-01-30)

## Resumen de Progreso
| Fase | Estado |
|------|--------|
| Stop Loss Emergency Exit Fix | ✅ Completado (v0.11.3) |
| Scanner Resilience (6 fixes) | ✅ Completado (v0.11.4) |
| Critical Bid/Ask Bug Fix | ✅ Completado (v0.11.4) |
| Dual-Frequency Loop | ✅ Completado (v0.11.5) |
| **Gamma API Integration** | 🚧 **EN PROGRESO** |

## Problema a Resolver
El bot muestra `volume=0.0` en todos los mercados porque la CLOB API no proporciona datos de volumen.
Sin volumen, el scoring de mercados es incompleto y no podemos filtrar por liquidez real.

## Solución Aprobada
Integrar **Gamma API** (https://gamma-api.polymarket.com) para obtener:
- `volumeNum` - Volumen total USD
- `volume24hr` - Volumen últimas 24h
- `liquidityNum` - Liquidez actual

**Arquitectura Híbrida**: Gamma para discovery + CLOB para trading.

---

# Instrucciones de Implementación

## Fase 1: Cliente Gamma (CODEX)

**Archivo a crear**: `bot/gamma_client.py`

```python
# Estructura esperada
class GammaClient:
    BASE_URL = "https://gamma-api.polymarket.com"

    def __init__(self, logger):
        self.logger = logger

    def get_markets(self, active=True, closed=False, limit=100):
        """Fetch markets with volume data."""
        # GET /markets?active=true&closed=false&limit=100
        pass

    def get_market_by_condition(self, condition_id):
        """Fetch single market details."""
        pass
```

**Campos requeridos de la respuesta**:
- `volumeNum`, `volume24hr`, `volume1wk`
- `liquidityNum`
- `clobTokenIds` (para mapear a CLOB)
- `bestBid`, `bestAsk`, `spread`

---

## Fase 2: Integración en Scanner (CODEX)

**Archivo a modificar**: `bot/market_scanner.py`

1. Importar `GammaClient`
2. Añadir método `_enrich_with_gamma_data(markets)`
3. Usar volumen en el scoring

**Nuevo flujo**:
```
1. Gamma API → Obtener mercados con volumen
2. Filtrar por min_volume_24h, min_liquidity
3. Extraer clobTokenIds
4. CLOB API → Verificar orderbook (spread real)
5. Calcular score con volumen incluido
```

---

## Fase 3: Actualizar Strategy (CODEX)

**Archivo a modificar**: `bot/strategy.py`

Añadir parámetros de volumen al scoring:

```python
def calculate_market_score(
    spread_percent,
    volume_24h,      # NUEVO
    liquidity,       # NUEVO
    odds,
    days_to_resolve,
):
    volume_weight = 25
    liquidity_weight = 15
    # ... integrar en score
```

---

## Fase 4: Configuración (CODEX)

**Archivo a modificar**: `config.json`

```json
{
  "market_filters": {
    "min_volume_24h": 500,
    "min_liquidity": 1000
  },
  "gamma_api": {
    "enabled": true,
    "base_url": "https://gamma-api.polymarket.com",
    "cache_ttl_seconds": 300
  }
}
```

---

## Fase 5: Tests (CODEX)

**Archivo a crear**: `tests/test_gamma_client.py`

- Test de parsing de respuesta Gamma
- Test de fallback cuando Gamma falla
- Test de integración con scanner

---

# Asignación de Tareas

## CODEX (Implementador)
```bash
# Ejecutar en orden:
1. Crear bot/gamma_client.py
2. Modificar bot/market_scanner.py
3. Modificar bot/strategy.py
4. Actualizar config.json
5. Crear tests/test_gamma_client.py
6. Ejecutar pytest
```

**Comando para CODEX**:
```bash
codex exec "Implement Gamma API client following /home/josejordan/poly/PROPOSAL_TRENDING_VOLUME.md and /home/josejordan/poly/PROMPT.md. Start with Phase 1: create bot/gamma_client.py" --full-auto
```

## GEMINI (Verificador)
```bash
# Después de cada fase:
source venv/bin/activate
python -m pytest tests/ -v
python main_bot.py --once
```

## CLAUDE (Arquitecto)
- Revisar código de CODEX antes de merge
- Validar que la integración es correcta
- Actualizar CLAUDE.md con decisiones arquitectónicas

---

# Criterios de Aceptación

- [ ] `gamma_client.py` creado y funcional
- [ ] Tests pasan (pytest)
- [ ] `--once` muestra volumen > 0 en candidatos
- [ ] Fallback a CLOB-only funciona si Gamma falla
- [ ] Config permite habilitar/deshabilitar Gamma
- [ ] CHANGELOG.md actualizado

---

# Gestión de Memoria (CRÍTICO)

Cada agente debe actualizar su memoria al completar tareas:

| Agente | Archivo | Actualizar con |
|--------|---------|----------------|
| CLAUDE | CLAUDE.md | Decisiones arquitectónicas Gamma |
| CODEX | AGENTS.md | Nuevos estándares de testing |
| GEMINI | GEMINI.md | Estado actual, resultados dry-run |
| GLOBAL | CHANGELOG.md | Entradas v0.12.0 |

---

**Versión objetivo**: 0.12.0
**Prioridad**: Medium
**Fecha**: 2026-01-30
