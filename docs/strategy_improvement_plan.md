# Plan de Implementación - Mejoras de Estrategia

**Fecha:** 2026-02-02  
**Versión:** 1.1 (Updated 2026-02-03)  
**Prioridad:** ALTA  
**Status:** Phase 1 COMPLETADO ✅

---

## 🎯 Objetivo

Corregir debilidades críticas en la estrategia de trading actual para alcanzar rentabilidad sostenible antes del despliegue con capital real.

---

## 📋 Resumen de Tareas

| ID | Tarea | Prioridad | Estimación | Asignado |
|----|-------|-----------|------------|----------|
| IMP-001 | Corregir inconsistencia rango de odds | 🔴 ALTA | 2h | ✅ DONE |
| IMP-002 | Rediseñar TP/SL con ratio 2:1 | 🔴 ALTA | 3h | ✅ DONE |
| IMP-003 | Aumentar tamaño de posición | 🟡 MEDIA | 30min | ✅ DONE |
| IMP-004 | Implementar Trailing Stop | 🟡 MEDIA | 4h | PENDIENTE |
| IMP-005 | Sizing dinámico Kelly Criterion | 🟢 BAJA | 6h | PENDIENTE |
| IMP-006 | Integrar análisis de slippage | 🟢 BAJA | 3h | PENDIENTE |
| IMP-007 | Testing y validación | 🔴 ALTA | 8h | ⏳ IN PROGRESS |

**Total estimado:** 26.5 horas (Phase 1: ~5.5h completadas)

---

## 🔴 PRIORIDAD ALTA

### IMP-001: Corregir Inconsistencia Rango de Odds

**Problema:** El bot opera en 0.60-0.80 pero define TP/SL para rangos 0.30-0.50 que nunca se usan.

**Solución propuesta:**

**Opción A - Ampliar rango (Recomendada):**
```json
{
  "market_filters": {
    "min_odds": 0.30,
    "max_odds": 0.80
  }
}
```

**Opción B - Ajustar TP/SL (Conservadora):**
```json
{
  "strategy": {
    "tp_sl_by_odds": {
      "0.60-0.70": { "tp_percent": 15, "sl_percent": 10 },
      "0.70-0.80": { "tp_percent": 12, "sl_percent": 8 }
    }
  }
}
```

**Archivos a modificar:**
- `config.json` - Actualizar parámetros
- `bot/strategy.py` - Añadir rangos 0.70-0.80 si se elige Opción B

**Criterios de aceptación:**
- [ ] Todos los rangos definidos en TP/SL son alcanzables por el bot
- [ ] Documentación actualizada refleja el rango operativo real

---

### IMP-002: Rediseñar TP/SL con Ratio 2:1

**Problema:** Ratio actual 1.20:1 requiere 48% win rate para breakeven (muy alto para predicción binaria).

**Solución propuesta:**

```json
{
  "strategy": {
    "tp_sl_by_odds": {
      "0.30-0.40": { "tp_percent": 30, "sl_percent": 15 },
      "0.40-0.50": { "tp_percent": 24, "sl_percent": 12 },
      "0.50-0.60": { "tp_percent": 20, "sl_percent": 10 },
      "0.60-0.70": { "tp_percent": 16, "sl_percent": 8 },
      "0.70-0.80": { "tp_percent": 14, "sl_percent": 7 }
    }
  }
}
```

**Win rate objetivo por rango:**
| Rango | TP | SL | Breakeven | Target WR |
|-------|-----|-----|-----------|-----------|
| 0.30-0.40 | 30% | 15% | 33.3% | 40%+ |
| 0.40-0.50 | 24% | 12% | 33.3% | 40%+ |
| 0.50-0.60 | 20% | 10% | 33.3% | 40%+ |
| 0.60-0.70 | 16% | 8% | 33.3% | 40%+ |
| 0.70-0.80 | 14% | 7% | 33.3% | 40%+ |

**Archivos a modificar:**
- `config.json` - Nueva configuración TP/SL
- `bot/strategy.py` - Añadir rango 0.70-0.80

**Criterios de aceptación:**
- [ ] Ratio TP:SL mínimo 2:1 en todos los rangos
- [ ] Win rate breakeven < 35% considerando comisiones
- [ ] Tests unitarios actualizados

---

### IMP-007: Testing y Validación

**Objetivo:** Validar todas las mejoras antes de despliegue.

**Fase 1: Tests Unitarios**
```bash
cd apps/poly
python -m pytest tests/ -v
python bot/strategy.py  # Test manual de cálculos
```

**Fase 2: Backtesting Simulado**
- Ejecutar bot en modo dry_run por 7 días
- Registrar todas las señales de entrada/salida
- Calcular métricas: Win Rate, P&L, Drawdown

**Fase 3: Paper Trading**
- 14 días operando sin dinero real
- Comparar contra baseline (estrategia anterior)

**Métricas objetivo:**
| Métrica | Mínimo Aceptable | Objetivo |
|---------|------------------|----------|
| Win Rate | 38% | 45%+ |
| Profit Factor | 1.3 | 1.5+ |
| Max Drawdown | <20% | <15% |
| Sharpe Ratio | >0.5 | >1.0 |

**Criterios de aceptación:**
- [ ] 7 días de dry_run sin errores
- [ ] Métricas cumplen mínimos aceptables
- [ ] Código revisado por 2 desarrolladores

---

## 🟡 PRIORIDAD MEDIA

### IMP-003: Aumentar Tamaño de Posición

**Problema:** Capital subutilizado (27% del total, 38% del disponible).

**Solución propuesta:**

```json
{
  "capital": {
    "max_trade_size": 1.0,
    "scale_to": 5.0,
    "scale_after_trades": 20
  },
  "risk": {
    "max_positions": 10
  }
}
```

**Nueva utilización:**
- 10 posiciones × $1.00 = $10 (55% del capital total)
- Reserva de $5 + $3 ocioso = flexibilidad para operar

**Archivos a modificar:**
- `config.json`

**Criterios de aceptación:**
- [ ] Tamaño ajustado según capital disponible
- [ ] Máximo drawdown por posición < 5% del capital

---

### IMP-004: Implementar Trailing Stop

**Problema:** No hay protección de ganancias parciales ni captura de tendencias.

**Solución propuesta:**

Añadir a `bot/position_manager.py`:

```python
def calculate_trailing_stop(
    self, 
    entry_price: float, 
    current_price: float, 
    initial_sl: float,
    activation_threshold: float = 0.5,  # 50% hacia TP
    trailing_distance: float = 0.05     # 5% debajo del máximo
) -> float:
    """
    Activa trailing stop cuando el precio alcanza 
    el % definido hacia el TP.
    """
    tp_price = self.get_tp_price(entry_price)
    sl_price = initial_sl
    
    # Distancia recorrida hacia TP (0.0 a 1.0)
    progress = (current_price - entry_price) / (tp_price - entry_price)
    
    if progress >= activation_threshold:
        # Trailing activado: SL sigue al precio
        max_price = max(current_price, self.get_position_high())
        new_sl = max_price * (1 - trailing_distance)
        return max(new_sl, sl_price)  # Nunca bajar el SL
    
    return sl_price
```

**Configuración:**
```json
{
  "strategy": {
    "trailing_stop": {
      "enabled": true,
      "activation_percent": 50,
      "trailing_distance_percent": 5
    }
  }
}
```

**Archivos a modificar:**
- `bot/position_manager.py` - Lógica de trailing
- `bot/trader.py` - Evaluación en cada iteración
- `config.json` - Parámetros configurables

**Criterios de aceptación:**
- [ ] Trailing stop calcula correctamente
- [ ] Nunca baja el SL por debajo del inicial
- [ ] Se activa solo después del umbral definido
- [ ] Tests unitarios pasan

---

## 🟢 PRIORIDAD BAJA

### IMP-005: Sizing Dinámico Kelly Criterion

**Problema:** Tamaño fijo sin considerar el edge de cada oportunidad.

**Solución propuesta:**

```python
def calculate_kelly_size(
    self,
    estimated_prob: float,    # Probabilidad estimada (ej: modelo propio)
    market_odds: float,       # Odds del mercado
    bankroll: float,          # Capital disponible
    kelly_fraction: float = 0.25  # Kelly fraccional (conservador)
) -> float:
    """
    f* = (p(b+1) - 1) / b
    Donde:
    - p = probabilidad de ganar
    - b = odds recibidos (decimal)
    """
    b = market_odds / (1 - market_odds)  # Convertir a odds decimal
    p = estimated_prob
    
    if p <= 1/(b+1):
        return 0  # No hay edge, no operar
    
    kelly = (p * (b + 1) - 1) / b
    bet_size = bankroll * kelly * kelly_fraction
    
    # Limitar a configuración máxima
    return min(bet_size, self.config.max_trade_size)
```

**Archivos a modificar:**
- `bot/strategy.py` - Método de sizing
- `config.json` - Parámetros Kelly

**Criterios de aceptación:**
- [ ] Calcula edge correctamente
- [ ] No opera cuando edge <= 0
- [ ] Respeta límites máximos de configuración

---

### IMP-006: Integrar Análisis de Slippage

**Problema:** El bot no considera cuánto empeorará el precio al ejecutar.

**Solución propuesta:**

Usar `walk_the_book` ya implementado en `market_scanner.py`:

```python
def validate_slippage(
    self, 
    token_id: str, 
    intended_size: float, 
    side: str
) -> Tuple[bool, float]:
    """
    Valida si el slippage es aceptable para operar.
    Returns: (should_trade, expected_price)
    """
    vwap, filled, slippage = self.walk_the_book(token_id, intended_size, side)
    
    max_slippage = self.config.get("max_slippage_percent", 2.0)
    
    if slippage > max_slippage:
        self.logger.warning(f"Slippage {slippage:.2f}% > {max_slippage}%")
        return False, vwap
    
    if filled < intended_size * 0.9:  # No se llena 90%
        self.logger.warning(f"Low liquidity: filled {filled}/{intended_size}")
        return False, vwap
    
    return True, vwap
```

**Configuración:**
```json
{
  "trading": {
    "max_slippage_percent": 2.0,
    "min_fill_ratio": 0.9
  }
}
```

**Archivos a modificar:**
- `bot/trader.py` - Validación antes de ejecutar
- `config.json` - Parámetros de slippage

**Criterios de aceptación:**
- [ ] Calcula VWAP correctamente
- [ ] Rechaza operaciones con slippage excesivo
- [ ] Ajusta tamaño si no hay suficiente liquidez

---

## 🚀 Plan de Rollout

### Fase 1: Correcciones Críticas (Semana 1)
- [x] IMP-001: Corregir rango de odds ✅ (2026-02-03)
- [x] IMP-002: Rediseñar TP/SL ✅ (2026-02-03)
- [x] IMP-003: Ajustar tamaño de posición ✅ (2026-02-03)
- [x] Code review y merge ✅

### Fase 2: Validación (Semana 2)
- [/] IMP-007: 7 días de dry_run (STARTED 2026-02-03)
- [ ] Análisis de métricas
- [ ] Ajustes si es necesario

### Fase 3: Paper Trading (Semanas 3-4)
- [ ] Ejecución con señales reales, sin capital
- [ ] Comparativa contra baseline
- [ ] Documentar resultados

### Fase 4: Features Adicionales (Semanas 5-6)
- [ ] IMP-004: Trailing Stop
- [ ] Testing de nueva funcionalidad
- [ ] Documentación de usuario

### Fase 5: Optimización (Semanas 7-8)
- [ ] IMP-005: Kelly Sizing (opcional)
- [ ] IMP-006: Slippage Analysis (opcional)
- [ ] Preparación para capital real

---

## 📊 KPIs de Seguimiento

| KPI | Valor Actual | Objetivo | Métrica |
|-----|--------------|----------|---------|
| Win Rate | ?% (pendiente baseline) | 40%+ | % operaciones ganadoras |
| Profit Factor | ? | 1.5+ | (Ganancias/Pérdidas) |
| Max Drawdown | ?% | <15% | Caída máxima del equity |
| Capital Utilizado | 27% | 50-70% | % del capital en posiciones |
| Operaciones/Día | ? | 2-5 | Frecuencia de trading |

---

## 📝 Notas para el Equipo

1. **Mantener modo dry_run** hasta completar Fase 3
2. **Documentar todos los cambios** en CHANGELOG.md
3. **Tests obligatorios** para cualquier modificación de strategy.py
4. **Revisar weekly** métricas y ajustar parámetros si es necesario
5. **No optimizar en exceso** (overfitting) - usar walk-forward testing

---

## 🔗 Recursos

- Análisis detallado: `docs/strategy_analysis_2026.md`
- Configuración actual: `config.json`
- Código estrategia: `bot/strategy.py`
- Plan copy trading: `docs/WHALE_COPY_TRADING_DESIGN.md`

---

**Próxima reunión:** Revisión de asignaciones y kickoff
**Contacto:** [Equipo de desarrollo]

---

*Documento vivo - actualizar según avance del proyecto*
