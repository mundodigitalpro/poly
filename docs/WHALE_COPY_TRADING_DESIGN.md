# Whale Copy Trading - Diseño de Arquitectura

## 🎯 Objetivo

Implementar sistema de auto-copy trading que sigue a los top traders de Polymarket en tiempo real.

---

## 🚧 Limitación Crítica: No Hay Datos de Win-Rate

### Datos Disponibles (Polymarket API)
```json
{
  "proxyWallet": "0xABC...",
  "side": "BUY",
  "size": 1000,
  "price": 0.55,
  "timestamp": "2026-02-01T12:00:00Z",
  "title": "Will Trump win?",
  "slug": "trump-win-2026",
  "transactionHash": "0xDEF..."
}
```

### Datos NO Disponibles
- ❌ P&L histórico del trader
- ❌ Win rate (% de trades ganadores)
- ❌ Sharpe ratio
- ❌ Drawdown máximo
- ❌ ROI del trader

### Implicación
No podemos calcular "win rate real", debemos usar **heurísticas proxy** para identificar buenos traders.

---

## 🧠 Estrategia de Selección de Whales (Sin Win-Rate)

### Método 1: Volume-Weighted Ranking ⭐ (Principal)
**Asunción:** Whales con mayor volumen sostenido probablemente son rentables (o ya habrían quebrado)

```python
def calculate_whale_score(trader_stats):
    """
    Score basado en:
    - Total volume (peso 40%)
    - Consistencia de trades (peso 30%)
    - Diversidad de markets (peso 20%)
    - Recencia de actividad (peso 10%)
    """
    volume_score = min(100, trader_stats["total_volume"] / 10000)  # Max at $10k
    consistency_score = min(100, trader_stats["trade_count"] * 2)  # Max at 50 trades
    diversity_score = min(100, trader_stats["unique_markets"] * 5)  # Max at 20 markets
    recency_score = 100 if hours_since_last_trade < 24 else 50

    total_score = (
        volume_score * 0.40 +
        consistency_score * 0.30 +
        diversity_score * 0.20 +
        recency_score * 0.10
    )

    return round(total_score, 2)
```

**Ventajas:**
- Datos disponibles vía API
- Proxy razonable de competencia
- Fácil de implementar

**Desventajas:**
- No garantiza rentabilidad
- Puede seguir whales en racha perdedora

---

### Método 2: Whale Consensus ⭐ (Secundario)
**Asunción:** Si 3+ whales compran el mismo market, probablemente hay información asimétrica

```python
def detect_whale_consensus(recent_trades, min_whales=3):
    """
    Groupby market + side
    Si >= 3 whales diferentes compran en últimas 2 horas → SIGNAL
    """
    market_activity = defaultdict(lambda: {"whales": set(), "volume": 0})

    for trade in recent_trades:
        if trade["usd_value"] >= 500:  # Whale threshold
            key = f"{trade['slug']}:{trade['side']}"
            market_activity[key]["whales"].add(trade["wallet"])
            market_activity[key]["volume"] += trade["usd_value"]

    signals = []
    for key, data in market_activity.items():
        if len(data["whales"]) >= min_whales:
            signals.append({
                "market": key.split(":")[0],
                "side": key.split(":")[1],
                "whale_count": len(data["whales"]),
                "confidence": min(100, len(data["whales"]) * 30)
            })

    return signals
```

**Ventajas:**
- Fuerte señal (sabiduría de la multitud)
- Reduce riesgo de seguir un solo whale malo

**Desventajas:**
- Menos señales (requiere consenso)
- Delay hasta que 3+ whales operen

---

### Método 3: Top Leaderboard (Polymarket Oficial) 🔮 (Futuro)
**Ideal:** Usar el leaderboard oficial de Polymarket si tiene API

**Investigar:**
```bash
# Posibles endpoints
GET https://polymarket.com/api/leaderboard
GET https://gamma-api.polymarket.com/leaderboard
```

Si existe → usar directamente, ya tiene win-rate calculado

---

## 🏗️ Arquitectura del Sistema

### Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                     WHALE COPY TRADING SYSTEM               │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        v                     v                     v
┌───────────────┐    ┌──────────────────┐   ┌─────────────────┐
│  Whale        │    │  Trade Monitor   │   │  Copy Engine    │
│  Profiler     │    │  (Real-time)     │   │  (Decision)     │
│               │    │                  │   │                 │
│ - Build       │    │ - Poll API       │   │ - Validate      │
│   leaderboard │    │   every 30s      │   │   signals       │
│ - Calculate   │    │ - Detect new     │   │ - Check risk    │
│   scores      │    │   whale trades   │   │ - Execute copy  │
│ - Update      │    │ - Match against  │   │ - Track copied  │
│   rankings    │    │   whitelist      │   │   positions     │
│               │    │ - Generate       │   │                 │
│ Runs: Every   │    │   signals        │   │ Runs: On        │
│ 15 minutes    │    │                  │   │ signal trigger  │
└───────────────┘    └──────────────────┘   └─────────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              v
                    ┌──────────────────┐
                    │  Main Bot Loop   │
                    │  (Orchestrator)  │
                    │                  │
                    │ Dual Strategy:   │
                    │ 1. Market scan   │
                    │ 2. Whale copy    │
                    └──────────────────┘
```

---

## 📁 Nuevos Archivos

### 1. `bot/whale_profiler.py` (NUEVO)
Gestión de rankings de whales

```python
class WhaleProfiler:
    """Build and maintain whale trader rankings."""

    def __init__(self, data_file="data/whale_profiles.json"):
        self.profiles = {}  # wallet -> profile
        self.data_file = data_file
        self.load()

    def update_profiles(self, trades: List[Dict]) -> Dict[str, Dict]:
        """Update whale profiles from recent trades."""
        # Calculate stats, scores, rankings
        pass

    def get_top_whales(self, limit=10) -> List[str]:
        """Get top N wallet addresses by score."""
        pass

    def get_profile(self, wallet: str) -> Optional[Dict]:
        """Get full profile for a wallet."""
        pass

    def is_whitelisted(self, wallet: str, min_score=60) -> bool:
        """Check if wallet meets copy trading criteria."""
        pass
```

### 2. `bot/whale_copy_engine.py` (NUEVO)
Lógica de decisión para copy trading

```python
class WhaleCopyEngine:
    """Decide which whale trades to copy."""

    def __init__(self, config, profiler, trader, position_manager):
        self.config = config
        self.profiler = profiler
        self.trader = trader
        self.pm = position_manager

    def evaluate_signal(self, trade_signal: Dict) -> Dict:
        """
        Evaluate if we should copy this trade.

        Checks:
        1. Is trader whitelisted?
        2. Does market pass filters?
        3. Do we have capital?
        4. Is risk acceptable?

        Returns: {should_copy: bool, reason: str, size: float}
        """
        pass

    def execute_copy(self, signal: Dict) -> Optional[Dict]:
        """Execute a copy trade."""
        pass

    def get_copy_statistics(self) -> Dict:
        """Stats on copied trades."""
        pass
```

### 3. `bot/whale_monitor.py` (NUEVO)
Real-time monitoring de trades de whales

```python
class WhaleMonitor:
    """Monitor whale trades in real-time."""

    def __init__(self, profiler, min_whale_size=500):
        self.tracker = WhaleTracker(min_whale_size)
        self.profiler = profiler
        self.seen_trades = set()

    def scan_for_signals(self) -> List[Dict]:
        """
        Poll API for new whale trades.

        Returns: List of signals: {
            wallet, side, market, slug, token_id,
            usd_value, confidence, timestamp
        }
        """
        pass

    def filter_whitelisted_only(self, trades: List[Dict]) -> List[Dict]:
        """Keep only trades from whitelisted whales."""
        pass
```

### 4. Integración en `main_bot.py` (MODIFICAR)

```python
# Nuevo modo dual
def run_loop_with_whale_copy(self):
    """Main loop con whale copy trading integrado."""

    whale_profiler = WhaleProfiler()
    whale_monitor = WhaleMonitor(whale_profiler)
    copy_engine = WhaleCopyEngine(config, whale_profiler, trader, pm)

    while True:
        # 1. Update whale profiles (cada 15 min)
        if time_to_update_profiles():
            whale_profiler.update_profiles(fetch_recent_trades())

        # 2. Scan for whale signals (cada 30s)
        signals = whale_monitor.scan_for_signals()

        # 3. Evaluate and copy
        for signal in signals:
            decision = copy_engine.evaluate_signal(signal)
            if decision["should_copy"]:
                copy_engine.execute_copy(signal)

        # 4. Original market scanning (cada 120s)
        if time_to_scan_markets():
            run_original_strategy()

        # 5. Monitor positions (ambas estrategias)
        monitor_all_positions()

        time.sleep(10)  # Main loop interval
```

---

## 📋 Config.json - Nuevos Parámetros

```json
{
  "whale_copy_trading": {
    "enabled": true,
    "mode": "hybrid",  // "hybrid", "whale_only", "original_only"

    "profiler": {
      "update_interval_seconds": 900,  // 15 min
      "min_whale_size": 500,
      "min_score_to_whitelist": 60,
      "max_whitelisted_whales": 20,
      "leaderboard_lookback_trades": 500
    },

    "monitor": {
      "poll_interval_seconds": 30,
      "max_trade_age_minutes": 10,  // Solo copiar trades <10 min
      "require_consensus": false,
      "min_consensus_whales": 3  // Si require_consensus=true
    },

    "copy_rules": {
      "enabled_sides": ["BUY"],  // Solo copiar compras (no ventas)
      "min_whale_trade_size": 500,
      "max_whale_trade_size": 50000,
      "copy_position_size": 0.50,  // $0.50 por copy trade
      "max_copies_per_day": 10,
      "apply_market_filters": true,  // Usar mismos filtros que strategy original
      "require_whale_score_above": 70,
      "blacklist_wallets": []
    },

    "risk_management": {
      "max_copy_allocation": 5.0,  // Max $5 en copy trades simultáneos
      "diversification_min_markets": 3,  // Min 3 markets diferentes
      "stop_if_daily_loss": 2.0,  // Detener copy si -$2 en un día
      "exit_strategy": "follow_whale"  // "follow_whale" o "own_tp_sl"
    },

    "alerts": {
      "telegram_on_whale_trade": true,
      "telegram_on_copy_executed": true,
      "log_level": "INFO"
    }
  }
}
```

---

## 🔄 Flujo de Ejecución

### Startup (Inicialización)
1. Load whale profiles from `data/whale_profiles.json`
2. Fetch recent 500 trades
3. Build initial leaderboard
4. Identify top 20 whales (score >60)
5. Start monitoring loop

### Continuous Loop (Cada 10s)
```python
# Every 10 seconds
while True:
    current_time = time.time()

    # A. Update whale profiles (every 15 min)
    if current_time - last_profile_update > 900:
        trades = fetch_recent_trades(limit=500)
        profiler.update_profiles(trades)
        last_profile_update = current_time

    # B. Scan for whale signals (every 30s)
    if current_time - last_whale_scan > 30:
        new_signals = whale_monitor.scan_for_signals()

        for signal in new_signals:
            # Validate against whitelist
            if not profiler.is_whitelisted(signal["wallet"]):
                continue

            # Evaluate copy decision
            decision = copy_engine.evaluate_signal(signal)

            if decision["should_copy"]:
                logger.info(f"COPY SIGNAL: {signal}")
                result = copy_engine.execute_copy(signal)

                if result["success"]:
                    send_telegram_alert(f"Copied whale trade: {result}")

        last_whale_scan = current_time

    # C. Original market scanning (every 120s)
    if current_time - last_market_scan > 120:
        run_original_market_strategy()
        last_market_scan = current_time

    # D. Monitor ALL positions (copy + original)
    monitor_positions()

    time.sleep(10)
```

---

## 🎯 Decisión de Copy Trading

### Checklist para Copiar un Trade

```python
def should_copy_trade(signal: Dict) -> Tuple[bool, str]:
    """
    Returns: (should_copy, reason)
    """

    # 1. Whale whitelist check
    if not profiler.is_whitelisted(signal["wallet"], min_score=70):
        return False, "Whale not whitelisted (score too low)"

    # 2. Trade age check
    age_minutes = (now - signal["timestamp"]).total_seconds() / 60
    if age_minutes > 10:
        return False, f"Trade too old ({age_minutes:.1f} min)"

    # 3. Side filter (solo BUY por default)
    if signal["side"] not in config["copy_rules"]["enabled_sides"]:
        return False, f"Side {signal['side']} not enabled"

    # 4. Trade size bounds
    if signal["usd_value"] < config["copy_rules"]["min_whale_trade_size"]:
        return False, "Whale trade size too small"
    if signal["usd_value"] > config["copy_rules"]["max_whale_trade_size"]:
        return False, "Whale trade size suspiciously large"

    # 5. Market filters (si apply_market_filters=true)
    if config["copy_rules"]["apply_market_filters"]:
        market_data = fetch_market_data(signal["token_id"])
        if not passes_market_filters(market_data):
            return False, "Market doesn't pass filters (spread/volume/odds)"

    # 6. Capital check
    if not has_available_capital(config["copy_rules"]["copy_position_size"]):
        return False, "Insufficient capital"

    # 7. Daily limits
    copies_today = count_copies_today()
    if copies_today >= config["copy_rules"]["max_copies_per_day"]:
        return False, "Daily copy limit reached"

    # 8. Risk allocation check
    current_copy_allocation = sum_copy_positions()
    if current_copy_allocation >= config["risk_management"]["max_copy_allocation"]:
        return False, "Max copy allocation reached"

    # 9. Diversification check
    unique_markets_held = len(set(p["market_slug"] for p in copy_positions))
    if unique_markets_held < config["risk_management"]["diversification_min_markets"]:
        if signal["market_slug"] in held_markets:
            return False, "Concentration risk (need more diversity)"

    # 10. Daily loss check
    copy_pnl_today = calculate_copy_pnl_today()
    if copy_pnl_today < -config["risk_management"]["stop_if_daily_loss"]:
        return False, f"Daily loss limit hit ({copy_pnl_today})"

    # All checks passed
    return True, "All validations passed"
```

---

## 📊 Data Structures

### Whale Profile (Persistente)
```json
{
  "wallet": "0xABC123...",
  "name": "Theo4",
  "stats": {
    "total_volume": 125000,
    "trade_count": 342,
    "unique_markets": 45,
    "buys": 180,
    "sells": 162,
    "avg_trade_size": 365.5,
    "last_seen": "2026-02-01T15:30:00Z",
    "first_seen": "2025-11-01T10:00:00Z"
  },
  "score": 85.5,
  "rank": 3,
  "whitelisted": true,
  "tags": ["high_volume", "consistent", "diverse"]
}
```

### Copy Trade Record
```json
{
  "copy_id": "copy_20260201_123456",
  "original_trade": {
    "whale_wallet": "0xABC...",
    "whale_name": "Theo4",
    "usd_value": 1500,
    "side": "BUY",
    "price": 0.55,
    "size": 2727
  },
  "our_trade": {
    "token_id": "21742633...",
    "side": "BUY",
    "size": 0.909,  // $0.50 worth
    "entry_price": 0.55,
    "filled_price": 0.551,
    "timestamp": "2026-02-01T12:35:22Z"
  },
  "exit": {
    "method": "follow_whale",  // or "tp_hit", "sl_hit"
    "exit_price": 0.72,
    "pnl": 0.15,
    "timestamp": "2026-02-01T18:22:11Z"
  },
  "status": "closed",  // "open", "closed"
  "pnl_usd": 0.15
}
```

---

## 🚀 Plan de Implementación (Fases)

### Fase 1: Core Infrastructure (2-3 días)
- [x] Diseñar arquitectura
- [ ] Implementar `bot/whale_profiler.py`
- [ ] Implementar `bot/whale_monitor.py`
- [ ] Implementar `bot/whale_copy_engine.py`
- [ ] Testing unitario de cada componente

### Fase 2: Integration (1-2 días)
- [ ] Integrar con `main_bot.py` (dual mode)
- [ ] Actualizar `config.json`
- [ ] Agregar Telegram alerts
- [ ] Testing end-to-end en dry-run

### Fase 3: Testing & Validation (3-5 días)
- [ ] Dry-run con 20+ whale signals
- [ ] Validar que solo copie whales whitelisted
- [ ] Verificar risk management (límites)
- [ ] Analizar performance vs strategy original

### Fase 4: Production (1 semana)
- [ ] Micro trading ($0.50 per copy)
- [ ] Monitor daily for 7 días
- [ ] Ajustar parámetros según datos
- [ ] Documentar resultados

---

## 🎲 Estrategia de Exit para Copy Trades

### Opción 1: Follow the Whale (Recomendado)
```python
# Continuar monitoreando el whale
# Cuando el whale venda, nosotros vendemos
while position_open:
    whale_trades = fetch_whale_recent_trades(whale_wallet)
    if whale_sold_our_market:
        execute_sell(match_whale_exit=True)
        break
```

**Pros:**
- Sigue la misma lógica del whale
- Captura timing superior si whale tiene alpha

**Cons:**
- Whale puede no vender nunca
- Dependencia de monitoreo continuo

---

### Opción 2: Own TP/SL (Alternativo)
```python
# Aplicar nuestros propios TP/SL dinámicos
# Igual que strategy original
tp_price = entry * 1.20  # +20%
sl_price = entry * 0.85  # -15%

if current_price >= tp_price:
    execute_sell(reason="take_profit")
elif current_price <= sl_price:
    execute_sell(reason="stop_loss")
```

**Pros:**
- Control total sobre risk
- No depende de whale

**Cons:**
- Puede salir antes que whale (dejar profit)
- No aprovecha información del whale

---

### Opción 3: Hybrid (Mejor de ambos)
```python
# Configurar TP/SL como backstop
# Pero dar preferencia a whale signals

if whale_sold:
    execute_sell(reason="follow_whale")
elif current_price >= tp_price:
    execute_sell(reason="tp_backstop")
elif current_price <= sl_price:
    execute_sell(reason="sl_protection")
elif days_held > 7 and whale_inactive:
    execute_sell(reason="timeout")
```

**Recomendación:** Usar Hybrid con config:
```json
{
  "exit_strategy": "hybrid",
  "follow_whale_priority": true,
  "tp_percent": 25,
  "sl_percent": 15,
  "max_hold_days": 7
}
```

---

## 📈 Métricas de Éxito

### KPIs a Trackear
1. **Copy Rate:** % de whale signals que copiamos (target: 60-80%)
2. **Win Rate:** % de copy trades ganadores (target: >50%)
3. **Avg P&L:** Promedio de ganancia por copy trade (target: +$0.10)
4. **Sharpe Ratio:** Risk-adjusted returns
5. **Max Drawdown:** Peor racha de pérdidas consecutivas
6. **Follow Efficiency:** ¿Cuántas veces el whale tuvo profit y nosotros también?

### Dashboard (tools/whale_copy_dashboard.py)
```
========================================
WHALE COPY TRADING STATS
========================================
Period: Last 7 days

Whitelisted Whales: 18
Signals Detected: 45
Signals Copied: 27 (60%)
Rejection Reasons:
  - Capital limit: 8
  - Market filters: 6
  - Daily limit: 4

Copy Trades:
  Total: 27
  Open: 3
  Closed: 24

  Win: 15 (62.5%)
  Loss: 9 (37.5%)

  Total P&L: +$2.85
  Avg P&L: +$0.12
  Best: +$0.45
  Worst: -$0.22

Original Strategy Comparison:
  Copy: +$2.85 (27 trades)
  Original: +$1.20 (15 trades)
  Combined: +$4.05 (42 trades)

Top Whales Copied:
  1. 0xABC... (Theo4) - 8 trades, +$1.50
  2. 0xDEF... (Fredi) - 6 trades, +$0.95
  3. 0xGHI... (Anon)  - 5 trades, +$0.40
```

---

## ⚠️ Riesgos y Mitigaciones

### Riesgo 1: Seguir whales en racha perdedora
**Mitigación:**
- Daily loss limit ($2.00)
- Stop copy si whale score cae <60
- Requiere score >70 para copiar

### Riesgo 2: Latency (nosotros compramos más caro)
**Mitigación:**
- Solo copiar trades <10 min
- VWAP order execution
- Slippage check (max 2%)

### Riesgo 3: Whale manipulation (pump & dump)
**Mitigación:**
- Min whale trade size: $500 (evita micro manipulación)
- Max whale trade size: $50k (evita whales sospechosos)
- Requiere volumen mínimo del market

### Riesgo 4: Over-allocation a copy strategy
**Mitigación:**
- Max $5 en copy trades simultáneos
- Max 10 copies/día
- Diversification: min 3 markets

### Riesgo 5: Whale nunca vende (capital atrapado)
**Mitigación:**
- Max hold: 7 días → auto-exit
- Hybrid exit strategy con TP/SL backstop

---

## 🎯 Conclusión

Sistema pragmático que funciona con datos disponibles:
- ✅ No requiere win-rate (usamos volume-weighted ranking)
- ✅ Risk management robusto
- ✅ Dual strategy (original + whale copy)
- ✅ Validación exhaustiva antes de copiar
- ✅ Telegram alerts para visibilidad

**Próximo paso:** Implementar Fase 1 (Core Infrastructure)
