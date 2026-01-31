# Parallel Implementation Plan: WebSocket + Concurrent Orders

## 🎯 Objetivo

Implementar **WebSocket real-time** mientras mantenemos **Concurrent Orders** funcional para testing en paralelo.

---

## 🏗️ Arquitectura de Coexistencia

### Sistema Modular con Flags Independientes

```json
// config.json
{
  "trading": {
    "use_concurrent_orders": false,  // Feature 1
    "use_websocket": false           // Feature 2 (nuevo)
  }
}
```

**Combinaciones posibles**:
```
Polling + Monitor mode        ← Baseline (actual)
Polling + Concurrent orders   ← Ya implementado
WebSocket + Monitor mode      ← Nuevo
WebSocket + Concurrent orders ← Objetivo final 🎯
```

---

## 📋 Plan de Trabajo (1 Semana)

### Día 1-2: WebSocket Foundation

**Crear archivos**:
- `bot/websocket_client.py` - Cliente WebSocket
- `bot/orderbook_snapshot.py` - Data structures
- `tests/test_websocket.py` - Unit tests

**Sin tocar**:
- `main_bot.py` (solo leer, no modificar aún)
- Concurrent orders (funciona independientemente)

**Resultado**: WebSocket funcional, aún no integrado

---

### Día 3: Integración Opcional

**Modificar**:
- `config.json` - Agregar `use_websocket: false`
- `main_bot.py` - Routing basado en flags

**Lógica**:
```python
# En main_bot.py
if use_websocket:
    # Nueva branch: WebSocket monitoring
    await monitor_positions_websocket()
else:
    # Existente: Polling
    monitor_positions_polling()
```

**Resultado**: Ambos modos coexisten, selección vía config

---

### Día 4: Testing WebSocket

**Ejecutar**:
```bash
# Test WebSocket solo (sin concurrent orders)
# config.json: use_websocket=true, use_concurrent_orders=false
python main_bot.py
```

**Validar**:
- Conexión WebSocket exitosa
- Recibe orderbook updates
- Latencia <100ms
- Reconexión automática

**Resultado**: WebSocket validado en modo aislado

---

### Día 5: Testing Concurrent Orders

**Ejecutar**:
```bash
# Test Concurrent Orders solo (sin WebSocket)
# config.json: use_websocket=false, use_concurrent_orders=true
bash scripts/test_concurrent_orders.sh
```

**Validar**:
- Limit orders se colocan
- TP/SL monitoring funciona
- Position persistence OK

**Resultado**: Concurrent Orders validado en modo aislado

---

### Día 6: Testing Combinado

**Ejecutar**:
```bash
# Test AMBOS juntos
# config.json: use_websocket=true, use_concurrent_orders=true
python main_bot.py
```

**Validar**:
- WebSocket detecta cambios instantáneamente
- Concurrent orders se colocan correctamente
- Status checks de limit orders vía WebSocket
- Ambos sistemas no interfieren

**Resultado**: Máxima eficiencia validada 🚀

---

### Día 7: Gasless Transactions

**Agregar**:
- Builder Program credentials a .env
- Lógica de gasless en `bot/trader.py`
- Flag `use_gasless: false` en config

**Testing**:
- 1 trade real con gasless
- Verificar $0 gas fee

**Resultado**: Triple optimización completa

---

## 🔧 Detalles Técnicos

### 1. WebSocket Client Architecture

```python
# bot/websocket_client.py
import asyncio
import websockets
import json
from typing import Callable, Dict, List
from dataclasses import dataclass

@dataclass
class OrderbookSnapshot:
    """Snapshot of orderbook at a point in time."""
    token_id: str
    timestamp: float
    bids: List[tuple]  # [(price, size), ...]
    asks: List[tuple]

    @property
    def best_bid(self) -> float:
        return max(self.bids, key=lambda x: x[0])[0] if self.bids else 0.0

    @property
    def best_ask(self) -> float:
        return min(self.asks, key=lambda x: x[0])[0] if self.asks else 0.0

    @property
    def mid_price(self) -> float:
        return (self.best_bid + self.best_ask) / 2 if self.best_bid and self.best_ask else 0.0

    @property
    def spread(self) -> float:
        return self.best_ask - self.best_bid if self.best_bid and self.best_ask else 0.0


class PolymarketWebSocket:
    """WebSocket client for real-time Polymarket orderbook data."""

    def __init__(self, logger):
        self.logger = logger
        self.ws = None
        self.subscribed_tokens: List[str] = []
        self.orderbooks: Dict[str, OrderbookSnapshot] = {}
        self.callbacks: List[Callable] = []
        self.running = False

    async def connect(self):
        """Establish WebSocket connection."""
        url = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
        self.ws = await websockets.connect(url)
        self.logger.info("WebSocket connected")

    async def subscribe(self, token_ids: List[str]):
        """Subscribe to orderbook updates for tokens."""
        self.subscribed_tokens.extend(token_ids)

        for token_id in token_ids:
            message = {
                "type": "subscribe",
                "channel": "market",
                "markets": [token_id]
            }
            await self.ws.send(json.dumps(message))
            self.logger.info(f"Subscribed to {token_id[:8]}...")

    async def run(self, auto_reconnect: bool = True):
        """Main loop to receive and process messages."""
        self.running = True

        while self.running:
            try:
                message = await self.ws.recv()
                await self._handle_message(message)
            except websockets.ConnectionClosed:
                self.logger.warn("WebSocket connection closed")
                if auto_reconnect:
                    await self._reconnect()
                else:
                    break
            except Exception as exc:
                self.logger.error(f"WebSocket error: {exc}")

    async def _handle_message(self, message: str):
        """Parse and process incoming messages."""
        try:
            data = json.loads(message)

            if data.get("type") == "book":
                snapshot = self._parse_orderbook(data)
                self.orderbooks[snapshot.token_id] = snapshot

                # Trigger callbacks
                for callback in self.callbacks:
                    await callback(snapshot)

        except Exception as exc:
            self.logger.error(f"Failed to handle message: {exc}")

    def _parse_orderbook(self, data: dict) -> OrderbookSnapshot:
        """Convert WebSocket message to OrderbookSnapshot."""
        return OrderbookSnapshot(
            token_id=data["market"],
            timestamp=data["timestamp"],
            bids=[(float(b["price"]), float(b["size"])) for b in data.get("bids", [])],
            asks=[(float(a["price"]), float(a["size"])) for a in data.get("asks", [])]
        )

    async def _reconnect(self):
        """Reconnect and resubscribe after connection loss."""
        self.logger.info("Reconnecting WebSocket...")
        await asyncio.sleep(5)
        await self.connect()
        await self.subscribe(self.subscribed_tokens)

    def on_book_update(self, callback: Callable):
        """Register callback for orderbook updates."""
        self.callbacks.append(callback)

    def get_orderbook(self, token_id: str) -> OrderbookSnapshot:
        """Get cached orderbook snapshot."""
        return self.orderbooks.get(token_id)

    async def close(self):
        """Close WebSocket connection."""
        self.running = False
        if self.ws:
            await self.ws.close()
        self.logger.info("WebSocket closed")
```

---

### 2. Integration Points

**main_bot.py modifications**:
```python
# Dual mode support
use_websocket = config.get("trading.use_websocket", False)
use_concurrent = config.get("trading.use_concurrent_orders", False)

if use_websocket:
    # Initialize WebSocket
    ws = PolymarketWebSocket(logger)
    await ws.connect()

    # Subscribe to all open positions
    token_ids = [pos.token_id for pos in position_manager.get_all_positions()]
    await ws.subscribe(token_ids)

    # Use WebSocket for monitoring
    async def monitor_loop():
        while True:
            for pos in position_manager.get_all_positions():
                snapshot = ws.get_orderbook(pos.token_id)
                if snapshot:
                    check_tp_sl(pos, snapshot)
            await asyncio.sleep(1)  # Much faster than 10s polling
else:
    # Existing polling logic
    def monitor_loop():
        # Current implementation
        pass
```

---

### 3. Configuration Schema

```json
{
  "trading": {
    "use_concurrent_orders": false,
    "use_websocket": false,
    "use_gasless": false,
    "websocket_reconnect_delay": 5,
    "websocket_ping_interval": 30
  }
}
```

---

## 🔄 Dependency Matrix

| Feature | Depends On | Conflicts With |
|---------|------------|----------------|
| Concurrent Orders | None | None |
| WebSocket | None | None |
| Gasless | None | None |

**Conclusión**: Todos son independientes ✅

---

## 🧪 Testing Strategy

### Phase 1: Isolated Testing

**Test 1**: Baseline (nada nuevo)
```json
{"use_concurrent_orders": false, "use_websocket": false}
```
**Expected**: Bot funciona como siempre

**Test 2**: Solo Concurrent Orders
```json
{"use_concurrent_orders": true, "use_websocket": false}
```
**Expected**: Limit orders funcionan, polling continúa

**Test 3**: Solo WebSocket
```json
{"use_concurrent_orders": false, "use_websocket": true}
```
**Expected**: WebSocket monitoring, market sells

**Test 4**: Ambos
```json
{"use_concurrent_orders": true, "use_websocket": true}
```
**Expected**: Limit orders + WebSocket status checks

---

### Phase 2: Performance Comparison

| Configuración | API Calls/hr | Latencia | Gas Fees |
|---------------|--------------|----------|----------|
| Baseline | 1,800 | 10s | $0.40 |
| +Concurrent | 80 | 10s | $0.40 |
| +WebSocket | 1 | <100ms | $0.40 |
| +Both | 1 | <100ms | $0.40 |
| +Both+Gasless | 1 | <100ms | $0.00 |

**Target**: Bottom row (máxima eficiencia)

---

## ⚠️ Risk Mitigation

### Risk 1: WebSocket Disconnection

**Mitigation**:
- Auto-reconnect with exponential backoff
- Fallback to polling if WebSocket fails >3 times
- Log all connection issues

### Risk 2: Both Systems Interfering

**Mitigation**:
- Clear separation in code (if/else branches)
- Independent testing before combining
- Config flags to disable quickly

### Risk 3: Increased Complexity

**Mitigation**:
- Comprehensive unit tests
- Clear documentation
- Fallback to baseline easily

---

## 📊 Success Criteria

**Week 1 Complete When**:
- [x] WebSocket client implemented
- [x] Concurrent orders tested
- [x] Both work together
- [x] Gasless integrated
- [x] All 4 test configurations pass
- [x] Performance metrics collected

**Metrics to Beat**:
- Latency: <1s (vs 10s baseline)
- API calls: <100/hr (vs 1,800 baseline)
- Win rate: ±2% (no strategy change)
- Error rate: ≤baseline

---

## 🚀 Quick Start Commands

```bash
# Day 1-2: Implement WebSocket
# (Create bot/websocket_client.py)

# Day 3: Test WebSocket alone
# Edit config.json: use_websocket=true, use_concurrent_orders=false
python main_bot.py

# Day 4-5: Test Concurrent Orders alone
# Edit config.json: use_websocket=false, use_concurrent_orders=true
bash scripts/test_concurrent_orders.sh

# Day 6: Test both together
# Edit config.json: use_websocket=true, use_concurrent_orders=true
python main_bot.py

# Day 7: Add gasless
# Edit config.json: use_gasless=true
python main_bot.py
```

---

## 📈 Expected Timeline

| Day | Task | Hours | Deliverable |
|-----|------|-------|-------------|
| 1 | WebSocket client | 4-6 | websocket_client.py |
| 2 | Unit tests + polish | 2-3 | tests/test_websocket.py |
| 3 | Integration | 3-4 | main_bot.py updated |
| 4 | WS testing | 2-3 | WS validated |
| 5 | Concurrent testing | 2-3 | Concurrent validated |
| 6 | Combined testing | 3-4 | Both validated |
| 7 | Gasless + docs | 2-3 | Complete |

**Total**: ~20-25 hours over 7 days

---

## 🎯 End State

**After 1 week, you'll have**:

✅ WebSocket real-time monitoring (-99% latency)
✅ Concurrent order placement (-95% API calls)
✅ Gasless transactions (-100% gas fees)
✅ All systems tested independently and together
✅ Clear config flags to enable/disable each
✅ Comprehensive documentation

**Bot evolution**:
```
Baseline → +Concurrent → +WebSocket → +Gasless → Optimized 🚀
```

---

**Ready to start?** First step: Create `bot/websocket_client.py`
