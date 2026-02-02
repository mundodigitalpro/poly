# Análisis de Estrategia de Trading - Polymarket Bot

**Fecha:** 2026-02-02  
**Analista:** Claude (Kimi)  
**Versión:** 1.0

---

## 📋 Resumen Ejecutivo

Este documento presenta un análisis completo de la estrategia de trading implementada en el bot de Polymarket, identificando fortalezas, debilidades críticas y oportunidades de mejora.

**Veredicto:** Estrategia BETA con fundamentos sólidos pero requiere ajustes significativos antes de usar con capital real.

---

## 🎯 Configuración Actual

### Parámetros de Trading

| Parámetro | Valor | Observación |
|-----------|-------|-------------|
| **Capital Total** | $18.00 | Limitado para testing |
| **Safety Reserve** | $5.00 | Protección conservadora |
| **Máximo por Trade** | $0.25 | 1.4% del capital por operación |
| **Máx. Posiciones** | 20 | Diversificación excesiva para el capital |
| **Cooldown** | 60 segundos | Entre operaciones |
| **Límite Pérdida Diaria** | $3.00 | 16.6% del capital |

### Filtros de Mercado

```json
{
  "min_odds": 0.60,
  "max_odds": 0.80,
  "max_spread_percent": 5.0,
  "min_volume_usd": 100.0,
  "min_volume_24h": 500,
  "min_liquidity": 1000,
  "min_days_to_resolve": 2,
  "max_days_to_resolve": 30
}
```

### Take-Profit / Stop-Loss por Rango

| Rango Odds | TP % | SL % | Ratio R:R |
|------------|------|------|-----------|
| 0.30-0.40 | 25% | 18% | 1.39:1 |
| 0.40-0.50 | 20% | 15% | 1.33:1 |
| 0.50-0.60 | 15% | 12% | 1.25:1 |
| 0.60-0.70 | 12% | 10% | 1.20:1 |

### Ponderación del Market Score

| Factor | Peso | Descripción |
|--------|------|-------------|
| Spread | 40% | Diferencial bid-ask |
| Volumen | 30% | Volumen 24h USD |
| Distancia Odds | 20% | Qué tan lejos de 0.50 |
| Tiempo Resolución | 10% | Días hasta cierre |

---

## ✅ Fortalezas Identificadas

### 1. Sistema de Filtros Robusto
- **Volumen mínimo** ($500) evita mercados ilíquidos
- **Liquidez** ($1000) asegura capacidad de salida
- **Spread máximo** (5%) reduce costos de entrada/salida
- **Filtro de resolución** (>2 días) evita mercados ya decididos

### 2. Integración de Datos Gamma
- API de volumen y liquidez en tiempo real
- Cache de mercados para análisis eficiente
- Mejora significativa sobre solo usar CLOB API

### 3. Copy Trading de Ballenas
- Monitoreo de wallets exitosas
- Sistema de scoring de ballenas
- Modo "hybrid" combina estrategia propia + señales

### 4. Gestión de Riesgo Básica
- Cooldown entre operaciones (anti-sobretrading)
- Blacklist de mercados problemáticos
- Límite diario de pérdidas

### 5. Algoritmo de Scoring Ponderado
- Múltiples factores considerados
- Fácilmente configurable
- Permite ajustar según condiciones de mercado

---

## ⚠️ Debilidades Críticas

### 🔴 PROBLEMA 1: Inconsistencia en Rango de Odds

**Descripción:** El bot opera en rango 0.60-0.80 pero define TP/SL para rangos 0.30-0.50 que nunca se usarán.

**Impacto:** Configuración muerta, confusión en mantenimiento, posibles errores al modificar.

**Código afectado:**
```python
# strategy.py - líneas 38-48
if 0.30 <= entry_odds < 0.40:
    range_key = "0.30-0.40"  # NUNCA SE USA
elif 0.40 <= entry_odds < 0.50:
    range_key = "0.40-0.50"  # NUNCA SE USA
# ... solo 0.60-0.70 se usa realmente
```

**Severidad:** ALTA

---

### 🔴 PROBLEMA 2: Ratio Risk/Reward Desfavorable

**Análisis matemático:**

Para el rango 0.60-0.70 (donde opera el bot):
- TP: 12% | SL: 10%
- Ratio: 1.20:1

**Breakeven Analysis:**
```
Win Rate necesario = SL / (TP + SL) = 10 / (12 + 10) = 45.5%
Con comisiones Polymarket (~2% entrada/salida): ~48% necesario
```

**Realidad de mercados de predicción:**
- Eventos binarios tienen alta volatilidad de corto plazo
- "Ruido" del mercado activa SLs prematuros
- Difícil mantener 48%+ win rate consistentemente

**Severidad:** ALTA

---

### 🟡 PROBLEMA 3: Subutilización de Capital

**Cálculo:**
- Capital disponible: $18 - $5 (reserva) = $13
- Máx posiciones: 20 × $0.25 = $5
- Uso real: 38% del capital disponible, 27% del total

**Problema:** Capital ocioso que no genera rendimiento, especialmente en modo acumulación.

**Severidad:** MEDIA

---

### 🟡 PROBLEMA 4: Ausencia de Trailing Stop

**Descripción:** Una vez abierta posición, no hay mecanismo para:
- Proteger ganancias parciales
- Ajustar SL si el precio se mueve favorablemente
- Capturar tendencias alcistas más allá del TP fijo

**Ejemplo:**
- Entrada: 0.65, TP: 0.728, SL: 0.585
- Precio llega a 0.72 (cerca de TP), luego cae a 0.60
- Sin trailing stop: se pierde la ganancia parcial

**Severidad:** MEDIA

---

### 🟡 PROBLEMA 5: Contradicción en Scoring

**Descripción:** El factor "odds_distance" premia estar lejos de 0.50, pero el rango 0.60-0.80 es relativamente moderado.

**Peso:** 20% del score va a favorecer extremos que el bot ni siquiera opera.

**Severidad:** MEDIA

---

### 🟢 PROBLEMA 6: Tamaño de Posición Estático

**Descripción:** $0.25 fijos sin considerar:
- Confianza del scoring
- Kelly Criterion adaptado
- Tamaño del edge detectado

**Severidad:** BAJA

---

## 📊 Comparativa con Mejores Prácticas

| Aspecto | Actual | Recomendado | Diferencia |
|---------|--------|-------------|------------|
| Rango Odds | 0.60-0.80 | 0.35-0.75 | Limitado |
| Ratio TP:SL | 1.20:1 | 2:1 mínimo | Insuficiente |
| Posición/Capital | 1.4% | 5-10% | Muy conservador |
| Trailing Stop | No | Sí | Falta feature |
| Sizing Dinámico | No | Sí | Mejorable |

---

## 💡 Oportunidades de Mejora

### Mejora 1: Ampliar Rango de Operación
**Acción:** Permitir operar en 0.30-0.80 con ajustes dinámicos
**Beneficio:** Más oportunidades, mejor diversificación
**Complejidad:** Baja

### Mejora 2: Rediseñar TP/SL
**Acción:** Implementar ratio mínimo 2:1 (ej: TP 20%, SL 10%)
**Beneficio:** Win rate necesario baja de 48% a 33%
**Complejidad:** Baja

### Mejora 3: Trailing Stop
**Acción:** Activar trailing a 50% del camino al TP
**Beneficio:** Capturar tendencias, proteger ganancias
**Complejidad:** Media

### Mejora 4: Sizing Kelly
**Acción:** Ajustar tamaño según edge = (probabilidad estimada - odds) / (1 - odds)
**Beneficio:** Mayor retorno en edges fuertes, menos riesgo en edges débiles
**Complejidad:** Media

### Mejora 5: Análisis de Profundidad
**Acción:** Calcular slippage real antes de ejecutar
**Beneficio:** Evitar mercados donde el precio empeora al entrar
**Complejidad:** Media (ya existe walk_the_book, integrar)

---

## 🎯 Conclusión y Recomendación

### Veredicto Final
La estrategia tiene **buenos fundamentos** pero presenta **riesgos operativos significativos** que deben corregirse antes del despliegue con capital real.

### Recomendación Inmediata
**NO usar con dinero real** hasta implementar:
1. ✅ Corrección del rango de odds (o ajustar TP/SL)
2. ✅ Mejora del ratio TP:SL a 2:1 mínimo
3. ✅ Aumentar tamaño de posición a $0.50-1.00

### Fase de Testing Recomendada
1. **Semana 1-2:** Paper trading con parámetros actuales (baseline)
2. **Semana 3-4:** Paper trading con mejoras implementadas
3. **Semana 5-6:** Análisis comparativo y ajuste fino
4. **Semana 7+:** Capital real (10% del objetivo final)

---

## 📎 Referencias

- `bot/strategy.py` - Implementación actual
- `bot/market_scanner.py` - Lógica de filtrado
- `config.json` - Parámetros configurables
- `docs/WHALE_COPY_TRADING_DESIGN.md` - Documentación de copy trading

---

*Documento generado para revisión del equipo de desarrollo.*
