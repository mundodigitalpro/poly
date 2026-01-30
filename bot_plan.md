# Plan: Bot Autónomo de Trading - Polymarket

## 🎯 Objetivo
Bot que opera de forma autónoma en un VPS, buscando oportunidades, comprando, y gestionando posiciones con take profit/stop loss dinámico.

## 📊 Parámetros de Operación

| Parámetro | Valor | Notas |
|-----------|-------|-------|
| Capital total | $18 | Verificar vía API cada loop |
| Máximo por trade | $0.25 → $1 | Empezar bajo, escalar gradualmente |
| Posiciones simultáneas | 3-5 máx | Evitar sobreexposición |
| Reserva de seguridad | $5 (no operar) | Buffer para emergencias |
| Capital operativo | $13 | Balance real - reserva - posiciones abiertas |
| Loop interval | 120-300s | Prevenir rate limits |

## 🔍 Criterios de Selección de Mercados

### Filtros de entrada (TODOS deben cumplirse):
1. **Odds**: Entre 0.30 y 0.70 (mercados inciertos = más oportunidad)
2. **Liquidez**: Spread < 5% entre BID y ASK (crítico para trades pequeños)
   - En trade de $1, spread 10% = $0.10 pérdida inmediata
   - Con spread 5%, necesitas solo +5% para empatar
3. **Volumen**: Orderbook con al menos $100 en ambos lados
   - Garantiza que puedas salir cuando necesites
4. **Timeframe**: Resolución esperada < 30 días
   - Evita capital atrapado en mercados de largo plazo
5. **Fees considerados**: TP debe cubrir fees + spread + margen deseado

### Ranking de "Mejor Candidato" (score ponderado):
```python
score = (
    (1 - spread_percent) * 40 +      # Menor spread = mejor
    (volume_total / 1000) * 30 +     # Mayor volumen = mejor
    abs(odds - 0.50) * 20 +          # Más alejado de 0.50 = mejor
    (30 - days_to_resolve) * 10      # Más cercano a resolver = mejor
)
```
Seleccionar mercado con mayor score que no esté en blacklist.

### Take Profit / Stop Loss Dinámico:

| Odds de Compra | Take Profit | Stop Loss | Fees Estimados |
|----------------|-------------|-----------|----------------|
| 0.30 - 0.40    | +25%        | -15%      | ~2-3%          |
| 0.40 - 0.50    | +20%        | -12%      | ~2-3%          |
| 0.50 - 0.60    | +15%        | -10%      | ~2-3%          |
| 0.60 - 0.70    | +12%        | -8%       | ~2-3%          |

*Mercados más inciertos (cerca de 0.50) → targets más conservadores*

**Nota crítica**: TP real = TP% - spread% - fees%. Con spread 5% + fees 2-3%, necesitas al menos +8% para ser rentable.

## 🏗️ Arquitectura

```
poly/
├── bot/
│   ├── __init__.py
│   ├── config.py          # Configuración del bot
│   ├── market_scanner.py  # Busca mercados que cumplan criterios
│   ├── position_manager.py # Gestiona posiciones abiertas + persistencia
│   ├── trader.py          # Ejecuta compras/ventas + maneja fills parciales
│   ├── strategy.py        # Calcula TP/SL dinámico + score de mercados
│   └── logger.py          # Logging a archivo
├── data/
│   ├── positions.json     # Posiciones abiertas (persistencia)
│   ├── blacklist.json     # Mercados bloqueados temporalmente
│   └── stats.json         # Estadísticas y balance histórico
├── logs/
│   └── bot_YYYY-MM-DD.log # Logs diarios
├── main_bot.py            # Entry point
├── config.json            # Parámetros configurables
└── docker-compose.yml     # Para VPS
```

### Estructura de `positions.json`:
```json
{
  "TOKEN_ID_123": {
    "entry_price": 0.45,
    "size": 2,
    "filled_size": 2,
    "entry_time": "2026-01-28T10:00:15Z",
    "tp": 0.54,
    "sl": 0.40,
    "fees_paid": 0.02,
    "order_id": "order_abc123"
  }
}
```

### Estructura de `blacklist.json`:
```json
{
  "TOKEN_ID_456": {
    "reason": "stop_loss",
    "blocked_until": "2026-02-01T00:00:00Z",
    "attempts": 1,
    "max_attempts": 2
  }
}
```

## 🔄 Flujo del Bot (Loop Principal)

```
┌──────────────────────────────────────────────────────┐
│              INICIALIZACIÓN (una vez)                 │
├──────────────────────────────────────────────────────┤
│  - Cargar positions.json (recuperar posiciones)      │
│  - Cargar blacklist.json                             │
│  - Verificar balance real (API)                      │
│  - Reconciliar posiciones (detectar cierres externos)│
│  - Inicializar logger                                │
└──────────────────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────────────────────┐
│                  LOOP INFINITO                        │
├──────────────────────────────────────────────────────┤
│                                                       │
│  1. ACTUALIZAR ESTADO                                │
│     ├─ Verificar balance real vía API               │
│     ├─ Limpiar blacklist (eliminar expirados)       │
│     └─ Log: estado actual del bot                   │
│                                                       │
│  2. GESTIONAR POSICIONES ABIERTAS                    │
│     ├─ Para cada posición en positions.json:        │
│     │  ├─ Obtener precio actual (BID)               │
│     │  ├─ Verificar liquidez de salida              │
│     │  ├─ ¿Alcanzó TP? → Intentar VENDER            │
│     │  ├─ ¿Alcanzó SL? → Intentar VENDER            │
│     │  └─ Si venta exitosa:                         │
│     │     ├─ Actualizar balance                     │
│     │     ├─ Registrar en stats.json                │
│     │     ├─ Si fue SL → agregar a blacklist       │
│     │     └─ Eliminar de positions.json             │
│     └─ Guardar cambios a disco                      │
│                                                       │
│  3. VERIFICAR SI PUEDO OPERAR                        │
│     ├─ ¿Balance real >= $5? (mínimo seguridad)     │
│     ├─ ¿Posiciones abiertas < 5?                    │
│     ├─ ¿Pasó cooldown desde última compra?          │
│     ├─ ¿Daily loss < $3?                            │
│     └─ Si NO → Skip a paso 5                        │
│                                                       │
│  4. BUSCAR Y EJECUTAR NUEVA OPERACIÓN               │
│     ├─ Escanear mercados disponibles                │
│     ├─ Filtrar por:                                 │
│     │  ├─ Odds: 0.30 - 0.70                        │
│     │  ├─ Spread < 5%                               │
│     │  ├─ Volumen > $100 ambos lados               │
│     │  ├─ Resolución < 30 días                     │
│     │  └─ No en blacklist ni en posiciones         │
│     ├─ Rankear por score ponderado                  │
│     ├─ Seleccionar mejor candidato                  │
│     └─ Si hay candidato válido:                     │
│        ├─ Calcular TP/SL dinámico según odds       │
│        ├─ Crear y ejecutar orden                    │
│        ├─ Esperar confirmación (timeout 30s)        │
│        ├─ Verificar fill (puede ser parcial)        │
│        ├─ Guardar posición real en positions.json  │
│        ├─ Actualizar balance                        │
│        └─ Registrar timestamp última compra         │
│                                                       │
│  5. ESPERAR (120-300 segundos)                      │
│                                                       │
│  6. REPETIR                                          │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### Manejo de Órdenes Parcialmente Ejecutadas
```python
# Después de crear orden
order_result = client.create_and_post_order(...)
time.sleep(30)  # Esperar ejecución

# Verificar ejecución real
filled = client.get_order(order_id)
if filled.size < order_args.size:
    # Fill parcial - registrar solo lo ejecutado
    actual_size = filled.size
    actual_cost = filled.size * filled.price
else:
    # Fill completo
    actual_size = order_args.size
    actual_cost = order_args.size * order_args.price
```

## 🛡️ Protecciones de Seguridad

1. **Capital mínimo**: No operar si balance real < $5
   - Verificar balance vía API cada loop, no confiar solo en cálculos

2. **Máximo posiciones**: No más de 5 simultáneas
   - Evita sobreexposición y fragmentación de capital

3. **Cooldown**: Mínimo 5 minutos entre compras
   - Previene trading emocional/errático
   - Permite que el mercado se estabilice

4. **Blacklist temporal** (no permanente):
   ```python
   # Mercado va a blacklist por 3 días después de SL
   # O después de 2 intentos fallidos
   blacklist_duration = 3 * 24 * 3600  # 3 días
   max_attempts = 2
   ```
   - Mercados pueden recuperarse, no bloquear para siempre

5. **Daily loss limit**: Si pierdo más de $3 en un día → pausar 24h
   - Trackear en `stats.json` con reset a medianoche
   - Previene caída en espiral

6. **Precio mínimo de venta**: Nunca vender por debajo del 50% del precio de compra
   - Protección contra crashes temporales
   - Preferible esperar que cristalizar pérdida extrema

7. **Verificación de liquidez de salida**:
   - Antes de comprar, verificar que haya volumen suficiente en BID
   - No entrar en mercados donde no puedas salir

8. **Rate limiting**:
   - Máximo 20 API calls por minuto
   - Implementar exponential backoff en errores 429

9. **Error handling robusto**:
   - Network timeouts → reintentar con backoff
   - API errors → loguear y continuar (no crashear)
   - Invalid data → skip y alertar

10. **Dry run mode**:
    - Variable `DRY_RUN = True` que simula pero no ejecuta trades
    - CRÍTICO para testing inicial

## 📝 Logging

Archivo `logs/bot_YYYY-MM-DD.log`:
```
[2026-01-28 10:00:00] INFO  - ========== BOT INICIADO ==========
[2026-01-28 10:00:00] INFO  - Balance inicial: $18.00 | Posiciones cargadas: 0
[2026-01-28 10:00:00] INFO  - Config: Max trade=$1, Max positions=5, Cooldown=300s
[2026-01-28 10:00:05] INFO  - Loop #1: Balance=$18.00, Posiciones=0, Daily loss=$0.00
[2026-01-28 10:00:10] INFO  - Escaneando 150 mercados...
[2026-01-28 10:00:15] INFO  - Filtrados: 12 mercados cumplen criterios
[2026-01-28 10:00:16] INFO  - Mejor candidato: "Hungary PM - Magyar?" (score: 85.3)
[2026-01-28 10:00:16] INFO  -   Odds: 0.45, Spread: 3.2%, Volume: $450, Days: 15
[2026-01-28 10:00:20] INFO  - COMPRA EJECUTADA: TOKEN_123
[2026-01-28 10:00:20] INFO  -   Size: 2/2 shares @ $0.45 = $0.90
[2026-01-28 10:00:20] INFO  -   Fees: $0.02 | TP: $0.54 (+20%) | SL: $0.40 (-11%)
[2026-01-28 10:00:20] INFO  -   Order ID: order_abc123
[2026-01-28 10:00:20] INFO  - Balance actualizado: $17.08 (incluyendo fees)
[2026-01-28 10:05:25] INFO  - Loop #2: Balance=$17.08, Posiciones=1, Daily loss=$0.00
[2026-01-28 10:05:30] INFO  - Posición TOKEN_123: Precio=$0.47 (+4.4%) | Estado: HOLDING
[2026-01-28 10:05:35] INFO  - Cooldown activo (2m restantes), skip búsqueda
[2026-01-28 12:30:00] INFO  - Loop #25: Balance=$17.08, Posiciones=1, Daily loss=$0.00
[2026-01-28 12:30:05] INFO  - Posición TOKEN_123: Precio=$0.55 (+22.2%) | TAKE PROFIT!
[2026-01-28 12:30:10] INFO  - VENTA EJECUTADA: TOKEN_123
[2026-01-28 12:30:10] INFO  -   Size: 2 shares @ $0.55 = $1.10
[2026-01-28 12:30:10] INFO  -   Fees: $0.02 | Ganancia neta: +$0.16 (+17.8%)
[2026-01-28 12:30:10] INFO  - Balance actualizado: $18.24
[2026-01-28 12:30:10] INFO  - Posición cerrada y removida de positions.json
[2026-01-28 15:45:00] ERROR - Posición TOKEN_456: Precio=$0.38 (-15.6%) | STOP LOSS!
[2026-01-28 15:45:05] WARN  - Liquidez baja en BID, ajustando precio de venta...
[2026-01-28 15:45:10] INFO  - VENTA EJECUTADA: TOKEN_456 @ $0.37 (parcial 1.5/2 shares)
[2026-01-28 15:45:10] INFO  -   Pérdida: -$0.22 | Balance: $18.02
[2026-01-28 15:45:10] INFO  - TOKEN_456 agregado a blacklist por 3 días
[2026-01-28 18:00:00] INFO  - Stats del día: Trades=4, Wins=3, Losses=1, P&L=+$0.12 (+0.67%)
```

### Niveles de log:
- **INFO**: Operaciones normales
- **WARN**: Situaciones anormales pero manejables
- **ERROR**: Errores que requieren atención
- **DEBUG**: Información detallada (solo en modo debug)

## 📊 Stats y Monitoring

### Estructura de `stats.json`:
```json
{
  "lifetime": {
    "total_trades": 45,
    "wins": 28,
    "losses": 17,
    "win_rate": 0.622,
    "total_pnl": 2.34,
    "roi": 0.13,
    "total_fees": 1.12,
    "avg_hold_time_hours": 8.5
  },
  "daily": {
    "2026-01-28": {
      "trades": 4,
      "wins": 3,
      "losses": 1,
      "pnl": 0.12,
      "fees": 0.08,
      "starting_balance": 18.00,
      "ending_balance": 18.04
    }
  },
  "by_odds_range": {
    "0.30-0.40": {"trades": 10, "wins": 7, "avg_pnl": 0.05},
    "0.40-0.50": {"trades": 15, "wins": 9, "avg_pnl": 0.03},
    "0.50-0.60": {"trades": 12, "wins": 8, "avg_pnl": 0.04},
    "0.60-0.70": {"trades": 8, "wins": 4, "avg_pnl": 0.02}
  }
}
```

### Métricas Clave a Monitorear:
1. **Win Rate**: % de trades ganadores (objetivo: >55%)
2. **Average P&L**: Ganancia promedio por trade
3. **Profit Factor**: (Total wins) / (Total losses) (objetivo: >1.5)
4. **Max Drawdown**: Pérdida máxima desde peak
5. **Sharpe Ratio**: ROI ajustado por volatilidad
6. **Hold Time**: Tiempo promedio en posición
7. **Fill Rate**: % de órdenes ejecutadas vs intentadas
8. **Fees/P&L Ratio**: Fees pagados como % de ganancias

### Dashboard Diario (consola o web):
```
╔══════════════════════════════════════════════════════════╗
║            POLYMARKET BOT - DAILY STATS                   ║
╠══════════════════════════════════════════════════════════╣
║ Balance: $18.24 (↑ $0.24 / +1.3%)                        ║
║ Posiciones: 2/5 abierta(s) | Capital libre: $7.80       ║
║ Daily P&L: +$0.16 | Daily Loss Limit: $2.84 restante   ║
╠══════════════════════════════════════════════════════════╣
║ Lifetime (45 trades):                                     ║
║   Win Rate: 62.2% (28W / 17L)                           ║
║   Total P&L: +$2.34 (↑ 13.0% ROI)                      ║
║   Avg Hold: 8.5 hours                                    ║
║   Fees Paid: $1.12 (47.9% of gross profit)              ║
╠══════════════════════════════════════════════════════════╣
║ Best Odds Range: 0.30-0.40 (70% WR, +$0.50)             ║
║ Worst Odds Range: 0.60-0.70 (50% WR, +$0.16)            ║
╠══════════════════════════════════════════════════════════╣
║ Blacklisted: 3 mercados (expires: 1d 5h)                ║
║ Last Trade: 2h ago (WIN @ +18%)                         ║
║ Next Cooldown: Ready                                     ║
╚══════════════════════════════════════════════════════════╝
```

## ⚙️ Configuración (`config.json`)

```json
{
  "capital": {
    "total": 18.0,
    "safety_reserve": 5.0,
    "max_trade_size": 1.0,
    "start_small": 0.25,
    "scale_after_trades": 30
  },
  "risk": {
    "max_positions": 5,
    "cooldown_seconds": 300,
    "daily_loss_limit": 3.0,
    "min_sell_price_ratio": 0.5
  },
  "market_filters": {
    "min_odds": 0.30,
    "max_odds": 0.70,
    "max_spread_percent": 5.0,
    "min_volume_usd": 100.0,
    "max_days_to_resolve": 30
  },
  "strategy": {
    "tp_sl_by_odds": {
      "0.30-0.40": {"tp_percent": 25, "sl_percent": 15},
      "0.40-0.50": {"tp_percent": 20, "sl_percent": 12},
      "0.50-0.60": {"tp_percent": 15, "sl_percent": 10},
      "0.60-0.70": {"tp_percent": 12, "sl_percent": 8}
    },
    "market_score_weights": {
      "spread": 40,
      "volume": 30,
      "odds_distance": 20,
      "time_to_resolve": 10
    }
  },
  "blacklist": {
    "duration_days": 3,
    "max_attempts": 2
  },
  "bot": {
    "loop_interval_seconds": 120,
    "order_timeout_seconds": 30,
    "dry_run": true,
    "log_level": "INFO"
  },
  "api": {
    "max_calls_per_minute": 20,
    "retry_attempts": 3,
    "retry_backoff_seconds": 5
  }
}
```

Todos estos parámetros deben ser fácilmente ajustables sin modificar código.

## ✅ Próximos Pasos - Roadmap de Implementación

### Fase 0: Preparación (1-2 días)
1. [x] Revisar y aprobar este plan actualizado
2. [x] Crear estructura de carpetas (`bot/`, `data/`, `logs/`)
3. [x] Implementar `config.json` con todos los parámetros
4. [x] Implementar `bot/logger.py` (primero, para debugging)

### Fase 1: Core Modules (3-4 días)
5. [x] Implementar `bot/config.py` (cargar configuración)
6. [x] Implementar `bot/position_manager.py`
   - [x] Cargar/guardar positions.json
   - [x] Cargar/guardar blacklist.json
   - [x] Reconciliar posiciones
7. [x] Implementar `bot/strategy.py`
   - [x] Calcular TP/SL dinámico
   - [x] Calcular score de mercados
8. [x] Implementar `bot/market_scanner.py`
   - [ ] Filtrar mercados por criterios
   - [ ] Rankear y seleccionar mejor candidato
9. [x] Implementar `bot/trader.py`
   - [ ] Ejecutar órdenes
   - [ ] Manejar fills parciales
   - [ ] Verificar liquidez

### Fase 2: Integración y Dry Run (2-3 días)
10. [x] Implementar `main_bot.py` con loop principal
11. [x] Implementar modo `DRY_RUN = True`
12. [x] Testing unitario de cada módulo
13. [ ] **CRÍTICO**: Correr 2-4 horas en modo dry run (~15-30 ciclos)
13. [ ] **CRÍTICO**: Correr 2-4 horas en modo dry run (~15-30 ciclos)
    - [ ] Verificar que loguea correctamente
    - [ ] Verificar que selecciona mercados apropiados
    - [ ] Verificar que cálculos de TP/SL son correctos
    - [ ] Analizar stats simulados

### Fase 3: Paper Trading (1 semana)
14. [ ] Revisar resultados de dry run
15. [ ] Ajustar parámetros si es necesario
16. [ ] Si dry run es positivo (>60% win rate), continuar
17. [ ] Si dry run es negativo, revisar estrategia

### Fase 4: Micro Trading (1-2 semanas)
18. [ ] **DRY_RUN = False** por primera vez
19. [ ] Empezar con `max_trade = $0.25` (no $1)
20. [ ] Ejecutar 20-30 trades reales
21. [ ] Monitorear CONSTANTEMENTE los primeros 3 días
22. [ ] Analizar resultados reales vs simulados
23. [ ] Si resultados son positivos (>50% win rate, +EV), continuar

### Fase 5: Normal Trading (ongoing)
24. [ ] Escalar gradualmente: $0.25 → $0.50 → $0.75 → $1.00
25. [ ] Optimizar parámetros basándose en datos reales
26. [ ] Implementar alertas (Telegram/Email) para eventos críticos

### Fase 6: VPS Deployment (cuando todo funcione)
27. [ ] Configurar Docker para producción
28. [ ] Desplegar en VPS
29. [ ] Configurar auto-restart en crashes
30. [ ] Implementar monitoring y alertas remotas

### Criterios de Avance entre Fases:
- **Fase 2 → 3**: Dry run loguea correctamente y no crashea
- **Fase 3 → 4**: Win rate simulado >60% y EV positivo
- **Fase 4 → 5**: 20+ trades reales con win rate >50% y +EV
- **Fase 5 → 6**: Bot estable por 2+ semanas sin intervención

**NUNCA** saltar fases. Cada fase valida que la anterior funciona correctamente.

## ⚠️ Riesgos y Consideraciones

### Riesgos Técnicos
1. **Bugs en el código**: Un error puede ejecutar trades no deseados o perder dinero
   - Mitigación: Dry run extensivo, testing, code review

2. **API failures**: Polymarket API puede caer o tener latencia
   - Mitigación: Error handling robusto, timeouts, reintentos

3. **Network issues**: VPS puede perder conexión
   - Mitigación: Auto-restart, persistencia de datos, reconciliación

4. **Partial fills no manejados**: Órdenes pueden ejecutarse parcialmente
   - Mitigación: Verificar fills reales, ajustar tracking

### Riesgos de Mercado
5. **Pérdida de capital**: Con $18 podrías perder todo si el bot funciona mal
   - Mitigación: Empezar con $0.25/trade, escalar gradualmente, daily loss limit

6. **Mercados ilíquidos**: Spread alto causa pérdidas al entrar/salir
   - Mitigación: Filtro estricto de spread <5%, verificar volumen

7. **Mercados sin compradores**: Puedes quedar atrapado en posición
   - Mitigación: Verificar liquidez de salida antes de entrar

8. **Eventos inesperados**: Noticias pueden mover mercados dramáticamente
   - Mitigación: Stop loss estricto, no operar durante eventos mayores

9. **Fees acumulados**: Fees de 2-3% en cada trade se acumulan
   - Mitigación: Calcular fees en TP/SL, mantener win rate alto

### Riesgos Estratégicos
10. **Overtrading**: Bot puede operar demasiado frecuentemente
    - Mitigación: Cooldown de 5 minutos, límite de posiciones

11. **Mercados de largo plazo**: Capital atrapado por meses
    - Mitigación: Filtrar por resolución <30 días

12. **Blacklist permanente**: Perder oportunidades en mercados buenos
    - Mitigación: Blacklist temporal (3 días), max 2 intentos

### Expectativas Realistas
- **Win rate objetivo**: 55-65% (no 100%)
- **ROI esperado**: 5-15% mensual (si todo va bien)
- **Probabilidad de pérdida**: ALTA en los primeros 30 días
- **Tiempo hasta breakeven**: 2-3 meses probablemente

**Recomendación crítica**:
1. Comenzar con modo "dry run" por 2-4 horas mínimo (~15-30 ciclos)
2. Micro trading ($0.25) por 20-30 trades antes de escalar
3. Solo operar capital que puedas perder 100%
4. Monitorear diariamente los primeros 2 meses

**Este es un experimento, no una máquina de dinero garantizada.**
