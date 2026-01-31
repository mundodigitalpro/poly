# Fix: Filtro de Mercados Resueltos

**Fecha**: 2026-01-31
**Problema**: El bot estaba abriendo posiciones en mercados que se resolvían poco después, causando pérdidas masivas (95-99%)
**Estado**: ✅ IMPLEMENTADO

---

## 🚨 Problema Identificado

### Síntomas

De 4 posiciones simuladas en `data/simulation_results.json`:
- **1 Take Profit**: +72% ganancia ✅
- **3 Stop Losses**: Pérdidas de -95%, -97%, -99% ❌

### Causa Raíz

Los mercados se **resolvieron** (cerraron) después de que el bot abriera posición, enviando el precio a 0 o 1:

```json
{
  "entry_price": 0.64,
  "exit_price": 0.031,  // ❌ -95% loss
  "pnl_pct": -95.15625
}
```

**Análisis**:
- `exit_price: 0.031` indica que el mercado se resolvió contra la posición
- El bot no detectó que estos mercados estaban muy cerca de resolverse
- El filtro `max_days_to_resolve: 30` no era suficientemente conservador

---

## ✅ Solución Implementada

### 1. Nuevo Filtro: `min_days_to_resolve`

**Archivo**: `config.json`

```json
{
  "market_filters": {
    "min_days_to_resolve": 2,     // ✨ NUEVO
    "max_days_to_resolve": 30
  }
}
```

**Efecto**: El bot ahora **rechaza mercados que resuelven en menos de 2 días**.

**Razón**: Evita mercados que están a punto de cerrarse (resolución inminente).

---

### 2. Verificación Mejorada de Mercados Cerrados

**Archivo**: `bot/market_scanner.py:668-711`

**Cambios**:

#### a) Detectar mercados pasados de fecha de resolución

```python
# CRITICAL: Check if market is past its resolution date
days_to_resolve = self._days_to_resolve(market)
if days_to_resolve < 0:  # Negative = past resolution date
    self.logger.info(
        f"Rejected market: past resolution date (days={days_to_resolve})"
    )
    return True, "closed_status"
```

**Efecto**: Si un mercado ya pasó su `end_date_iso`, se rechaza automáticamente.

#### b) Ampliar detección de status cerrados

```python
if status in ("closed", "resolved", "settled", "finalized"):
    return True, "closed_status"
```

**Efecto**: Detecta más variantes de estados "cerrado".

---

### 3. Filtro Aplicado en Análisis de Mercados

**Archivo**: `bot/market_scanner.py:272-321`

```python
# CRITICAL: Reject markets resolving too soon
if days_to_resolve < min_days:
    self.logger.info(
        f"Rejected {token_id[:8]}: resolves too soon "
        f"(days={days_to_resolve} < {min_days})"
    )
    return False
```

**Efecto**: El filtro se aplica **antes** de llamar al API de orderbooks (ahorro de llamadas).

---

### 4. Logging Mejorado

**Archivo**: `bot/market_scanner.py:259-270`

Ahora cuando se **acepta** un mercado, se registra:

```python
self.logger.info(
    f"✓ Candidate: {question[:60]}... | "
    f"token={token_id[:8]}... | odds={odds:.2f} | "
    f"spread={spread_percent:.1f}% | days={days_to_resolve} | "
    f"score={score:.1f}"
)
```

**Efecto**: Puedes ver en los logs **exactamente** qué mercados se aceptan y sus características.

---

## 🧪 Herramienta de Diagnóstico

**Nueva herramienta**: `tools/diagnose_market_filters.py`

### Qué hace

1. Analiza 50 mercados reales
2. Muestra **por qué** cada mercado fue rechazado
3. Lista mercados aceptados con sus métricas
4. Exporta resultados a CSV (opcional)

### Cómo usar

```bash
# Diagnóstico básico
python tools/diagnose_market_filters.py

# Ver todos los mercados (no solo rechazados)
python tools/diagnose_market_filters.py --show-all

# Exportar a CSV
python tools/diagnose_market_filters.py --csv
```

### Salida esperada

```
[1/50] Analyzing market...
  Question: Will Trump win the 2024 election?
  Status: active | Active: True | Closed: False
  Token: 21742633...
  Volume: $1,250.50 | Liquidity: $5,200.00
  Days to resolve: 15
  Bid: 0.52 | Ask: 0.54 | Odds: 0.53
  Spread: 3.77%
  ✅ ACCEPTED: score=78.5

[2/50] Analyzing market...
  Question: Will it rain tomorrow in NYC?
  Status: active | Active: True | Closed: False
  Days to resolve: 1
  ❌ REJECTED: days_too_soon (1 < 2)

SUMMARY
========================================
Total markets analyzed: 50
✅ Accepted: 12
❌ Rejected: 38

Rejection reasons:
  • days_too_soon (1 < 2): 15
  • spread_too_wide: 8
  • odds_out_of_range: 7
  • closed_status: 5
  • no_orderbook: 3
```

---

## 📊 Impacto Esperado

### Antes del Fix

| Métrica | Valor |
|---------|-------|
| Mercados resueltos en posiciones | 3/4 (75%) |
| Pérdida promedio de SL | -69% |
| Posiciones "tóxicas" | Alta |

### Después del Fix

| Métrica | Valor Esperado |
|---------|----------------|
| Mercados resueltos en posiciones | <5% |
| Pérdida promedio de SL | -10 a -15% |
| Posiciones "tóxicas" | Baja |

### Por qué mejora

1. **`min_days_to_resolve: 2`**: Evita mercados que resuelven hoy/mañana
2. **Detección de fecha pasada**: Rechaza mercados ya resueltos
3. **Logging mejorado**: Visibilidad de qué se acepta/rechaza

---

## ✅ Validación

### Paso 1: Limpiar Posiciones Viejas

```bash
# Respaldar posiciones actuales
cp data/positions.json data/positions.json.old

# Revisar y eliminar posiciones de mercados resueltos
cat data/positions.json | python -m json.tool

# Si todas las posiciones son de mercados resueltos, limpia
echo "[]" > data/positions.json
```

### Paso 2: Ejecutar Diagnóstico

```bash
# Ver qué mercados se están aceptando ahora
python tools/diagnose_market_filters.py
```

**Verifica**:
- ✅ Ningún mercado con `days < 2` es aceptado
- ✅ Mercados con `status=closed` son rechazados
- ✅ Al menos 5-10 mercados son aceptados

### Paso 3: Dry Run 24 Horas

```bash
# Asegurar que dry_run=true
# config.json: "dry_run": true

# Ejecutar bot
python main_bot.py
```

**Monitorear logs**:
```
[INFO] ✓ Candidate: Will Bitcoin hit $100k... | days=7 | score=82.3
[INFO] Rejected 12345678: resolves too soon (days=1 < 2)
```

**Verifica**:
- ✅ Logs muestran `days` para mercados aceptados
- ✅ Mercados con `days < 2` son rechazados
- ✅ No aparecen mensajes de mercados resueltos

### Paso 4: Revisar Simulation

Después de 24 horas, ejecuta:

```bash
python tools/simulate_fills.py
```

**Verifica**:
- ✅ No hay posiciones con `exit_price < 0.10` (mercados resueltos)
- ✅ Posiciones tienen `days_to_resolve >= 2` al momento de entrada

---

## 🔧 Configuración Recomendada

### Conservador (Recomendado)

```json
{
  "market_filters": {
    "min_days_to_resolve": 2,
    "max_days_to_resolve": 14
  }
}
```

**Para**: Usuarios que quieren evitar mercados resueltos completamente.

### Moderado

```json
{
  "market_filters": {
    "min_days_to_resolve": 1,
    "max_days_to_resolve": 21
  }
}
```

**Para**: Usuarios que aceptan algo de riesgo de resolución rápida.

### Agresivo (NO recomendado)

```json
{
  "market_filters": {
    "min_days_to_resolve": 0,
    "max_days_to_resolve": 30
  }
}
```

**Riesgo**: Puede abrir posiciones en mercados que resuelven muy pronto.

---

## 🎯 Casos de Uso

### Caso 1: Mercado que resuelve mañana

```json
{
  "question": "Will it rain tomorrow?",
  "end_date_iso": "2026-02-01T12:00:00Z",
  "active": true,
  "closed": false
}
```

**Antes del fix**: ✅ Aceptado (si cumple otros filtros)
**Después del fix**: ❌ Rechazado (`days=1 < min_days=2`)

---

### Caso 2: Mercado ya resuelto pero no marcado

```json
{
  "question": "Did Bitcoin hit $50k in 2024?",
  "end_date_iso": "2024-12-31T23:59:59Z",
  "active": true,
  "closed": false
}
```

**Antes del fix**: ✅ Aceptado (active=true)
**Después del fix**: ❌ Rechazado (`days=-30 < 0`)

---

### Caso 3: Mercado resuelve en 1 semana

```json
{
  "question": "Will Trump announce VP pick?",
  "end_date_iso": "2026-02-07T12:00:00Z",
  "active": true,
  "closed": false
}
```

**Antes del fix**: ✅ Aceptado
**Después del fix**: ✅ Aceptado (`days=7 >= min_days=2`)

---

## 🐛 Troubleshooting

### Problema: Ningún mercado es aceptado

**Síntoma**:
```
Scan summary: candidates=0 days_too_soon=50
```

**Causa**: `min_days_to_resolve` configurado muy alto.

**Solución**:
```json
{
  "min_days_to_resolve": 1  // Reducir a 1 día
}
```

---

### Problema: Todavía aparecen mercados resueltos

**Síntoma**:
Posiciones con `exit_price < 0.10` después del fix.

**Causa posible**:
1. El mercado se resolvió **después** de abrir posición (normal, no evitable)
2. La fecha de resolución no está en `end_date_iso`

**Solución**:
```bash
# Ejecutar diagnóstico para ver qué se acepta
python tools/diagnose_market_filters.py

# Si aparecen mercados con days < 2, reportar bug
```

---

### Problema: Logs no muestran `days`

**Síntoma**:
```
[INFO] ✓ Candidate: Market question... | score=80
```

Sin información de `days`.

**Causa**: Versión vieja de market_scanner.py.

**Solución**:
```bash
# Verificar que tienes los cambios más recientes
git status
git pull origin claude/investigate-article-implementation-CG7Bb
```

---

## 📈 Métricas de Éxito

Después de implementar el fix y correr 48 horas en dry-run:

| Métrica | Target | Cómo Medir |
|---------|--------|------------|
| Mercados resueltos en posiciones | <5% | `python tools/simulate_fills.py` |
| Posiciones con `days >= 2` | >95% | Revisar `data/positions.json` |
| SL por resolución | <10% de SLs | Comparar `exit_price` con `sl` |
| Logging claro | 100% | Ver `days` en logs de candidatos |

---

## 📝 Archivos Modificados

| Archivo | Cambio | Líneas |
|---------|--------|--------|
| `config.json` | Añadido `min_days_to_resolve: 2` | +1 |
| `bot/market_scanner.py` | Filtro min_days, detección mejorada, logging | +35 |
| `tools/diagnose_market_filters.py` | **NUEVO** - herramienta diagnóstico | +400 |
| `docs/FIX_RESOLVED_MARKETS.md` | **NUEVO** - documentación | +450 |

**Total**: ~886 líneas de código + documentación

---

## 🚀 Próximos Pasos

1. **Validar fix** (1-2 horas):
   ```bash
   python tools/diagnose_market_filters.py
   ```

2. **Dry run 24-48 horas**:
   - Monitorear logs
   - Verificar que `days >= 2` en mercados aceptados
   - Confirmar que no aparecen mercados resueltos

3. **Revisar simulation**:
   ```bash
   python tools/simulate_fills.py
   ```
   - Verificar que no hay `exit_price < 0.10`

4. **Micro-trading** (después de validación):
   ```json
   {
     "dry_run": false,
     "max_trade_size": 0.10,
     "max_positions": 2
   }
   ```

---

## 🎓 Lecciones Aprendidas

1. **Mercados activos ≠ mercados seguros**: Un mercado puede estar `active=true` pero resolver en 1 día.

2. **`max_days` no es suficiente**: Necesitas también `min_days` para evitar resoluciones inmediatas.

3. **Logging es crítico**: Sin logs detallados, es difícil diagnosticar por qué se aceptan/rechazan mercados.

4. **Validación continua**: Herramientas como `diagnose_market_filters.py` son esenciales para debugging.

---

## ❓ FAQ

**P: ¿Por qué `min_days=2` y no `min_days=1`?**

R: Dos días da un margen de seguridad para:
- Zonas horarias diferentes
- Mercados que resuelven "fin de semana"
- Errores en metadata de `end_date_iso`

**P: ¿Puedo poner `min_days=0` para máxima liquidez?**

R: Puedes, pero arriesgas mercados que resuelven hoy/mañana. Solo recomendado si monitoreas activamente.

**P: ¿El fix previene 100% de mercados resueltos?**

R: No. Un mercado puede resolverse **después** de que abras posición. El fix reduce la probabilidad, no la elimina.

**P: ¿Qué pasa si `end_date_iso` está mal en la API?**

R: El filtro no funcionará para ese mercado. Es un edge case raro. Monitorea logs para detectarlo.

---

**Status**: ✅ Implementado y listo para validación
**Autor**: Claude (AI Assistant)
**Revisión**: Pendiente test en dry-run 24h
